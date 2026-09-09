import uuid
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.modules.customers.models import Customer, CustomerLedgerEntry
from app.modules.stock.models import Purchase, StockBalance, StockMovement
from app.modules.suppliers.models import Supplier, SupplierLedgerEntry
from tests.utils import admin_headers


async def _master_data(client, headers):
    tag = uuid.uuid4().hex[:8]
    category = (await client.post(
        "/api/v1/categories", json={"code": f"PL-{tag}", "name": f"Ledger {tag}"}, headers=headers
    )).json()["data"]
    product = (await client.post(
        "/api/v1/products",
        json={
            "sku": f"PL-{tag}", "barcode": f"885{tag}", "name": f"Sheet {tag}",
            "category_id": category["id"], "cost_price": "2.00", "selling_price": "10.00",
        },
        headers=headers,
    )).json()["data"]
    supplier = (await client.post(
        "/api/v1/suppliers", json={"code": f"SUP-{tag}", "name": f"Supplier {tag}"}, headers=headers
    )).json()["data"]
    customer = (await client.post(
        "/api/v1/customers", json={"code": f"CUS-{tag}", "name": f"Customer {tag}"}, headers=headers
    )).json()["data"]
    return product, supplier, customer


@pytest.mark.asyncio
async def test_dimensional_purchase_recalculates_and_reconciles(client, db_session):
    headers = await admin_headers(client)
    product, supplier, _ = await _master_data(client, headers)
    response = await client.post(
        "/api/v1/purchases",
        json={
            "supplier_id": supplier["id"], "other_cost": "5.00", "discount": "2.00",
            "paid_amount": "10.00",
            "items": [{
                "product_id": product["id"], "quantity": "2", "height": "3", "width": "4",
                "calculation_mode": "DIMENSIONAL", "unit_price": "2.50",
            }],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    purchase = response.json()["data"]
    assert Decimal(purchase["items"][0]["square_meter"]) == Decimal("24")
    assert Decimal(purchase["subtotal"]) == Decimal("60.00")
    assert Decimal(purchase["grand_total"]) == Decimal("63.00")
    assert Decimal(purchase["balance_amount"]) == Decimal("53.00")

    balance = await db_session.scalar(select(StockBalance).where(StockBalance.product_id == uuid.UUID(product["id"])))
    supplier_row = await db_session.get(Supplier, uuid.UUID(supplier["id"]))
    ledger_balance = await db_session.scalar(select(func.sum(SupplierLedgerEntry.debit - SupplierLedgerEntry.credit)).where(
        SupplierLedgerEntry.supplier_id == supplier_row.id
    ))
    assert Decimal(balance.quantity) == Decimal("2.0000")
    assert Decimal(supplier_row.current_debt) == Decimal("53.00") == Decimal(ledger_balance)

    returned = await client.post(
        f"/api/v1/purchases/{purchase['id']}/returns",
        json={
            "reason": "supplier return",
            "items": [{"purchase_item_id": purchase["items"][0]["id"], "quantity": "1"}],
        },
        headers=headers,
    )
    assert returned.status_code == 201, returned.text
    assert Decimal(returned.json()["data"]["total_amount"]) == Decimal("30.00")
    statement = await client.get(
        "/api/v1/reports/supplier-statement", params={"supplier_id": supplier["id"]}, headers=headers
    )
    assert statement.status_code == 200, statement.text
    summary = statement.json()["data"]["summary"]
    assert Decimal(summary["total_purchases"]) == Decimal("63.00")
    assert Decimal(summary["total_payments"]) == Decimal("10.00")
    assert Decimal(summary["total_returns"]) == Decimal("30.00")
    assert Decimal(summary["closing_balance"]) == Decimal("23.00")
    exported = await client.get(
        "/api/v1/reports/supplier-statement/export",
        params={"supplier_id": supplier["id"], "format": "xlsx"}, headers=headers,
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@pytest.mark.asyncio
async def test_purchase_rolls_back_when_total_is_invalid(client, db_session):
    headers = await admin_headers(client)
    product, supplier, _ = await _master_data(client, headers)
    before = await db_session.scalar(select(func.count()).select_from(Purchase))
    response = await client.post(
        "/api/v1/purchases",
        json={
            "supplier_id": supplier["id"], "discount": "100.00", "paid_amount": "0",
            "items": [{"product_id": product["id"], "quantity": "3", "unit_price": "1.00"}],
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert await db_session.scalar(select(func.count()).select_from(Purchase)) == before
    balance = await db_session.scalar(select(StockBalance.quantity).where(StockBalance.product_id == uuid.UUID(product["id"])))
    assert Decimal(balance) == Decimal("0")


@pytest.mark.asyncio
async def test_sale_ledgers_statements_exports_and_reconciliation(client, db_session):
    headers = await admin_headers(client)
    product, supplier, customer = await _master_data(client, headers)
    purchase = await client.post(
        "/api/v1/purchases",
        json={
            "supplier_id": supplier["id"], "paid_amount": "10.00",
            "items": [{"product_id": product["id"], "quantity": "10", "unit_price": "2.00"}],
        }, headers=headers,
    )
    assert purchase.status_code == 201, purchase.text
    sale = await client.post(
        "/api/v1/pos/sales",
        json={
            "customer_id": customer["id"], "payment_method": "CUSTOMER_DEBT", "paid_amount": "5.00",
            "items": [{
                "product_id": product["id"], "quantity": "2", "height": "2", "width": "3",
                "calculation_mode": "DIMENSIONAL", "unit_price": "10.00",
            }],
        }, headers=headers,
    )
    assert sale.status_code == 201, sale.text
    payload = sale.json()["data"]
    assert Decimal(payload["items"][0]["square_meter"]) == Decimal("12")
    assert Decimal(payload["grand_total"]) == Decimal("120.00")
    assert Decimal(payload["balance_amount"]) == Decimal("115.00")

    statement = await client.get(
        "/api/v1/reports/customer-statement", params={"customer_id": customer["id"]}, headers=headers
    )
    assert statement.status_code == 200, statement.text
    summary = statement.json()["data"]["summary"]
    assert Decimal(summary["total_sales"]) == Decimal("120.00")
    assert Decimal(summary["total_payments"]) == Decimal("5.00")
    assert Decimal(summary["closing_balance"]) == Decimal("115.00")

    for fmt, content_type in (
        ("pdf", "application/pdf"),
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ):
        exported = await client.get(
            "/api/v1/reports/customer-statement/export",
            params={"customer_id": customer["id"], "format": fmt}, headers=headers,
        )
        assert exported.status_code == 200, exported.text
        assert exported.headers["content-type"].startswith(content_type)
        assert f"customer-statement.{fmt}" in exported.headers["content-disposition"]

    product_id = uuid.UUID(product["id"])
    customer_id = uuid.UUID(customer["id"])
    stock = await db_session.scalar(select(StockBalance.quantity).where(StockBalance.product_id == product_id))
    movement = await db_session.scalar(select(StockMovement.new_balance).where(
        StockMovement.product_id == product_id
    ).order_by(StockMovement.occurred_at.desc(), StockMovement.created_at.desc()).limit(1))
    customer_row = await db_session.get(Customer, customer_id)
    customer_ledger = await db_session.scalar(select(func.sum(CustomerLedgerEntry.debit - CustomerLedgerEntry.credit)).where(
        CustomerLedgerEntry.customer_id == customer_id
    ))
    assert Decimal(stock) == Decimal(movement) == Decimal("8")
    assert Decimal(customer_row.current_debt) == Decimal(customer_ledger) == Decimal("115.00")
