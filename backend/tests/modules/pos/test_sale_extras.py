"""POS complete-sale extras: camelCase input, charges,
included debts, active sale price, and the print-ready receipt payload."""

import uuid
from decimal import Decimal

import pytest

from tests.modules.pos.helpers import balance_of, make_customer, make_stocked_product
from tests.utils import admin_headers


@pytest.mark.asyncio
async def test_complete_sale_alias_and_camel_case_payload(client):
    headers = await admin_headers(client)
    tag = uuid.uuid4().hex[:6]
    product = await make_stocked_product(client, headers, sku=f"POSX-{tag}", name=f"POSX Widget {tag}")

    response = await client.post(
        "/api/v1/pos/sales/complete",
        json={
            "paymentMethod": "CASH",
            "paidAmount": "21.00",
            "items": [{"productId": product["id"], "quantity": 2}],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    sale = response.json()["data"]
    assert Decimal(sale["grand_total"]) == Decimal("20.00")
    assert Decimal(sale["change_amount"]) == Decimal("1.00")


@pytest.mark.asyncio
async def test_default_unit_price_is_active_sale_price_version(client):
    headers = await admin_headers(client)
    tag = uuid.uuid4().hex[:6]
    product = await make_stocked_product(client, headers, sku=f"POSP-{tag}", name=f"POSP Widget {tag}")

    # Add a new POS-active price version; POS must follow it.
    created = await client.post(
        "/api/v1/products/sale-prices",
        json={"productId": product["id"], "salePrice": "15.00"},
        headers=headers,
    )
    assert created.status_code == 201, created.text

    response = await client.post(
        "/api/v1/pos/sales",
        json={"payment_method": "CASH", "amount_received": "100.00", "items": [{"product_id": product["id"], "quantity": "2"}]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    sale = response.json()["data"]
    assert Decimal(sale["grand_total"]) == Decimal("30.00")
    assert Decimal(sale["items"][0]["unit_price"]) == Decimal("15.00")


@pytest.mark.asyncio
async def test_other_charge_added_to_grand_total(client):
    headers = await admin_headers(client)
    tag = uuid.uuid4().hex[:6]
    product = await make_stocked_product(client, headers, sku=f"POSD-{tag}", name=f"POSD Widget {tag}")

    response = await client.post(
        "/api/v1/pos/sales",
        json={
            "payment_method": "CASH",
            "paidAmount": "25.00",
            "otherCharge": "5.00",
            "items": [{"productId": product["id"], "quantity": 2}],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    sale = response.json()["data"]
    assert Decimal(sale["grand_total"]) == Decimal("25.00")
    assert Decimal(sale["other_charge"]) == Decimal("5.00")

    # Receipt payload carries the other charge.
    receipt = await client.get(f"/api/v1/pos/sales/{sale['id']}/receipt", headers=headers)
    assert receipt.status_code == 200, receipt.text
    data = receipt.json()["data"]
    assert Decimal(data["other_charge"]) == Decimal("5.00")


@pytest.mark.asyncio
async def test_included_debts_settled_from_paid_amount(client):
    headers = await admin_headers(client)
    tag = uuid.uuid4().hex[:6]
    product = await make_stocked_product(client, headers, sku=f"POSB-{tag}", name=f"POSB Widget {tag}")
    customer = await make_customer(client, headers, code=f"POSB-C-{tag}", name="POSB Customer")

    # First sale creates a 10.00 debt.
    first = await client.post(
        "/api/v1/pos/sales",
        json={
            "payment_method": "CUSTOMER_DEBT",
            "customer_id": customer["id"],
            "items": [{"product_id": product["id"], "quantity": "1"}],
        },
        headers=headers,
    )
    assert first.status_code == 201, first.text

    debts = (await client.get(f"/api/v1/customers/{customer['id']}/debts", headers=headers)).json()["data"]
    open_debt = next(row for row in debts if Decimal(row["remaining_amount"]) > 0)
    assert open_debt["invoice_no"]
    assert open_debt["date"] is not None

    # Second sale includes the open debt and settles it from the paid amount:
    # 10 (new items) + 5 (part of the old debt) = 15.00 received now.
    second = await client.post(
        "/api/v1/pos/sales/complete",
        json={
            "customerId": customer["id"],
            "paymentMethod": "CASH",
            "paidAmount": "15.00",
            "includedDebtIds": [open_debt["id"]],
            "items": [{"productId": product["id"], "quantity": "1"}],
        },
        headers=headers,
    )
    assert second.status_code == 201, second.text
    sale = second.json()["data"]
    assert Decimal(sale["grand_total"]) == Decimal("10.00")
    # The paid amount settles included debts first; the remainder goes to the
    # new sale (10 debt + 5 sale covered, 5 still owed on the new invoice).
    assert Decimal(sale["paid_amount"]) == Decimal("5.00")
    assert Decimal(sale["debt_amount"]) == Decimal("5.00")
    assert sale["payment_status"] == "PARTIAL"

    debts_after = (await client.get(f"/api/v1/customers/{customer['id']}/debts", headers=headers)).json()["data"]
    settled = next(row for row in debts_after if row["id"] == open_debt["id"])
    assert Decimal(settled["remaining_amount"]) == Decimal("0.00")
    assert settled["status"] == "PAID"

    # The second sale left a 5.00 debt of its own; include it next and settle
    # exactly its remaining 5.00 (never more — no overpayment).
    open_after = next(row for row in debts_after if Decimal(row["remaining_amount"]) == Decimal("5.00"))
    third = await client.post(
        "/api/v1/pos/sales/complete",
        json={
            "customerId": customer["id"],
            "paymentMethod": "CASH",
            "paidAmount": "20.00",
            "includedDebtIds": [open_after["id"]],
            "items": [{"productId": product["id"], "quantity": "1"}],
        },
        headers=headers,
    )
    assert third.status_code == 201, third.text
    data = third.json()["data"]
    # 20 received - 5 debt settlement - 10 sale = 5 change.
    assert Decimal(data["change_amount"]) == Decimal("5.00")
    assert data["payment_status"] == "PAID"


@pytest.mark.asyncio
async def test_receipt_payload_is_print_ready(client):
    headers = await admin_headers(client)
    tag = uuid.uuid4().hex[:6]
    product = await make_stocked_product(client, headers, sku=f"POSR-{tag}", name=f"POSR Widget {tag}")

    sale = (
        await client.post(
            "/api/v1/pos/sales",
            json={
                "payment_method": "CASH",
                "amount_received": "30.00",
                "otherCharge": "2.00",
                "items": [{"productId": product["id"], "quantity": 2, "discountPercent": 10}],
            },
            headers=headers,
        )
    ).json()["data"]

    receipt = await client.get(f"/api/v1/pos/sales/{sale['id']}/receipt", headers=headers)
    assert receipt.status_code == 200, receipt.text
    data = receipt.json()["data"]
    assert data["shop"]["name"]
    assert data["invoice_no"] == sale["invoice_no"]
    assert data["sale_date"]
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["name"] == product["name"]
    assert item["sku"]
    assert Decimal(item["line_total"]) == Decimal("18.00")  # 2 × 10 − 10%
    assert Decimal(data["subtotal"]) == Decimal("20.00")
    assert Decimal(data["discount"]) == Decimal("2.00")
    assert Decimal(data["other_charge"]) == Decimal("2.00")
    assert Decimal(data["grand_total"]) == Decimal("20.00")
    assert Decimal(data["paid"]) == Decimal("20.00")
