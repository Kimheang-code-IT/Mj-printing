"""Report JSON, PDF, and XLSX endpoints backed by shared query services."""

import csv
import io
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ListParams, envelope, get_db_session, list_params, require_permission
from app.modules.auth.models import User
from app.modules.reports.schemas import (
    CustomerDebtReportRow,
    ExpenseCreate,
    ExpenseOut,
    FinanceEntryRow,
    FinanceReportOut,
    PurchaseReportRow,
    SalesReportRow,
    SupplierDebtReportRow,
)
from app.modules.reports.service import ReportsService

router = APIRouter(prefix="/reports", tags=["reports"])


async def _company_settings(db: AsyncSession) -> dict:
    from app.modules.administration import get_setting_value

    return {
        "name": await get_setting_value(db, "shop", "shop_name", "MJ Printing"),
        "address": await get_setting_value(db, "shop", "address", ""),
        "phone": await get_setting_value(db, "shop", "phone", ""),
        "logo": await get_setting_value(db, "invoice", "logo", ""),
    }


def _export_response(content: bytes, *, filename: str, format: str) -> Response:
    media = "application/pdf" if format == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(content=content, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename}.{format}"'})


async def _render_report(db: AsyncSession, *, title: str, filename: str, format: str, data: dict, columns: list[str]):
    from app.modules.reports.exports import build_pdf, build_xlsx

    if format not in {"pdf", "xlsx"}:
        from app.core.exceptions import ValidationError

        raise ValidationError("format must be pdf or xlsx", field_errors={"format": "Unsupported format"})
    summary = data.get("summary") or {}
    renderer = build_pdf if format == "pdf" else build_xlsx
    content = renderer(
        title=title, company=await _company_settings(db), period=data.get("period") or {},
        columns=columns, rows=data.get("rows") or [], totals=summary,
    )
    return _export_response(content, filename=filename, format=format)


@router.get("/customer-statement")
async def customer_statement(
    customer_id: UUID,
    params: ListParams = Depends(list_params),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("customer_statements.view")),
) -> dict:
    data = await ReportsService(db).customer_statement(
        customer_id=customer_id, start=params.start_date, end=params.end_date,
        page=params.page, limit=params.limit,
    )
    total = data.pop("total")
    return envelope(data, {"page": params.page, "limit": params.limit, "total": total})


@router.get("/supplier-statement")
async def supplier_statement(
    supplier_id: UUID,
    params: ListParams = Depends(list_params),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("supplier_statements.view")),
) -> dict:
    data = await ReportsService(db).supplier_statement(
        supplier_id=supplier_id, start=params.start_date, end=params.end_date,
        page=params.page, limit=params.limit,
    )
    total = data.pop("total")
    return envelope(data, {"page": params.page, "limit": params.limit, "total": total})


@router.get("/customers")
async def customer_report(
    customer_id: UUID | None = None,
    start_date: date | None = Query(default=None, alias="startDate"),
    end_date: date | None = Query(default=None, alias="endDate"),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("customer_reports.view")),
) -> dict:
    return envelope(await ReportsService(db).party_report(party="customer", party_id=customer_id, start=start_date, end=end_date))


@router.get("/suppliers")
async def supplier_report(
    supplier_id: UUID | None = None,
    start_date: date | None = Query(default=None, alias="startDate"),
    end_date: date | None = Query(default=None, alias="endDate"),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("supplier_reports.view")),
) -> dict:
    return envelope(await ReportsService(db).party_report(party="supplier", party_id=supplier_id, start=start_date, end=end_date))


@router.get("/customer-statement/export")
async def customer_statement_export(
    customer_id: UUID, format: str = Query(pattern="^(pdf|xlsx)$"),
    start_date: date | None = Query(default=None, alias="startDate"), end_date: date | None = Query(default=None, alias="endDate"),
    db: AsyncSession = Depends(get_db_session), actor: User = Depends(require_permission("customer_statements.export")),
):
    data = await ReportsService(db).customer_statement(customer_id=customer_id, start=start_date, end=end_date, page=1, limit=100000)
    return await _render_report(db, title="Customer Statement", filename="customer-statement", format=format, data=data,
                                columns=["date", "reference_no", "transaction_type", "description", "debit", "credit", "running_balance"])


@router.get("/supplier-statement/export")
async def supplier_statement_export(
    supplier_id: UUID, format: str = Query(pattern="^(pdf|xlsx)$"),
    start_date: date | None = Query(default=None, alias="startDate"), end_date: date | None = Query(default=None, alias="endDate"),
    db: AsyncSession = Depends(get_db_session), actor: User = Depends(require_permission("supplier_statements.export")),
):
    data = await ReportsService(db).supplier_statement(supplier_id=supplier_id, start=start_date, end=end_date, page=1, limit=100000)
    return await _render_report(db, title="Supplier Statement", filename="supplier-statement", format=format, data=data,
                                columns=["date", "reference_no", "transaction_type", "description", "debit", "credit", "running_balance"])


@router.get("/customers/export")
async def customer_report_export(
    format: str = Query(pattern="^(pdf|xlsx)$"), customer_id: UUID | None = None,
    start_date: date | None = Query(default=None, alias="startDate"), end_date: date | None = Query(default=None, alias="endDate"),
    db: AsyncSession = Depends(get_db_session), actor: User = Depends(require_permission("customer_reports.export")),
):
    data = await ReportsService(db).party_report(party="customer", party_id=customer_id, start=start_date, end=end_date)
    return await _render_report(db, title="Customer Report", filename="customer-report", format=format, data=data,
                                columns=["code", "name", "phone", "transaction_count", "total_transactions", "total_paid", "total_returns", "outstanding_balance"])


@router.get("/suppliers/export")
async def supplier_report_export(
    format: str = Query(pattern="^(pdf|xlsx)$"), supplier_id: UUID | None = None,
    start_date: date | None = Query(default=None, alias="startDate"), end_date: date | None = Query(default=None, alias="endDate"),
    db: AsyncSession = Depends(get_db_session), actor: User = Depends(require_permission("supplier_reports.export")),
):
    data = await ReportsService(db).party_report(party="supplier", party_id=supplier_id, start=start_date, end=end_date)
    return await _render_report(db, title="Supplier Report", filename="supplier-report", format=format, data=data,
                                columns=["code", "name", "phone", "transaction_count", "total_transactions", "total_paid", "total_returns", "outstanding_balance"])


@router.get("/stock-movements/export")
async def stock_movements_export(
    format: str = Query(pattern="^(pdf|xlsx)$"),
    product_id: UUID | None = None,
    movement_type: str | None = None,
    params: ListParams = Depends(list_params),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("stock_movements.export")),
):
    from app.modules.stock.service import StockOperationService, movement_to_out

    movements, _ = await StockOperationService(db).list_movements(
        q=params.q, product_id=product_id, movement_type=movement_type,
        start=params.start_date, end=params.end_date, page=1, limit=100000,
    )
    rows = [movement_to_out(row).model_dump() for row in movements]
    data = {"period": {"from": params.start_date or "", "to": params.end_date or ""}, "rows": rows}
    return await _render_report(
        db, title="Stock Movements", filename="stock-movements", format=format, data=data,
        columns=["occurred_at", "document_no", "movement_type", "product_name", "previous_qty", "qty_in", "qty_out", "new_balance", "unit_cost"],
    )


@router.get("/stock")
async def stock_report(
    category_id: UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.stock")),
) -> dict:
    return envelope(await ReportsService(db).stock_report(category_id=category_id))


@router.get("/stock/export")
async def stock_report_export(
    format: str = Query(default="xlsx", pattern="^(pdf|xlsx)$"),
    category_id: UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.stock")),
):
    data = await ReportsService(db).stock_report(category_id=category_id)
    return await _render_report(
        db, title="Stock Report", filename="stock-report", format=format, data=data,
        columns=["product_code", "product", "current_stock", "average_cost", "stock_value", "status"],
    )


@router.get("/profit")
async def profit_report(
    start_date: date | None = Query(default=None, alias="startDate"),
    end_date: date | None = Query(default=None, alias="endDate"),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.finance")),
) -> dict:
    return envelope(await ReportsService(db).profit_report(start=start_date, end=end_date))


@router.get("/profit/export")
async def profit_report_export(
    format: str = Query(default="xlsx", pattern="^(pdf|xlsx)$"),
    start_date: date | None = Query(default=None, alias="startDate"),
    end_date: date | None = Query(default=None, alias="endDate"),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.finance")),
):
    data = await ReportsService(db).profit_report(start=start_date, end=end_date)
    return await _render_report(
        db, title="Profit Report", filename="profit-report", format=format, data=data,
        columns=["date", "invoice_no", "product_code", "product", "sales_amount", "cost_amount", "gross_profit"],
    )


@router.get("/sales")
async def sales_report(
    params: ListParams = Depends(list_params),
    customer_id: UUID | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    cashier_id: UUID | None = Query(default=None),
    payment_method: str | None = Query(default=None, pattern="^(CASH|BANK_QR|CUSTOMER_DEBT)$"),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.sales")),
) -> dict:
    service = ReportsService(db)
    rows, total = await service.sales_report(
        q=params.q,
        customer_id=customer_id,
        product_id=product_id,
        category_id=category_id,
        cashier_id=cashier_id,
        payment_method=payment_method,
        start=params.start_date,
        end=params.end_date,
        page=params.page,
        limit=params.limit,
    )
    return envelope(
        [SalesReportRow.model_validate(row) for row in rows],
        {"page": params.page, "limit": params.limit, "total": total},
    )


# `/purchase` and `/purchases` serve the same Purchase Report (frontend uses
# the plural path; spec section 7 documents the singular one).
@router.get("/purchase")
@router.get("/purchases")
async def purchase_report(
    params: ListParams = Depends(list_params),
    supplier_id: UUID | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.purchase")),
) -> dict:
    service = ReportsService(db)
    rows, total = await service.purchase_report(
        q=params.q,
        supplier_id=supplier_id,
        product_id=product_id,
        status=status,
        start=params.start_date,
        end=params.end_date,
        page=params.page,
        limit=params.limit,
    )
    return envelope(
        [PurchaseReportRow.model_validate(row) for row in rows],
        {"page": params.page, "limit": params.limit, "total": total},
    )


@router.get("/customer-debts")
async def customer_debt_report(
    params: ListParams = Depends(list_params),
    customer_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None, pattern="^(UNPAID|PARTIAL|PAID)$"),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.customer_debt")),
) -> dict:
    service = ReportsService(db)
    rows, total = await service.customer_debt_report(
        q=params.q,
        customer_id=customer_id,
        status=status,
        start=params.start_date,
        end=params.end_date,
        page=params.page,
        limit=params.limit,
    )
    return envelope(
        [CustomerDebtReportRow.model_validate(row) for row in rows],
        {"page": params.page, "limit": params.limit, "total": total},
    )


@router.get("/supplier-debts")
async def supplier_debt_report(
    params: ListParams = Depends(list_params),
    supplier_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None, pattern="^(UNPAID|PARTIAL|PAID)$"),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.supplier_debt")),
) -> dict:
    service = ReportsService(db)
    rows, total = await service.supplier_debt_report(
        q=params.q,
        supplier_id=supplier_id,
        status=status,
        start=params.start_date,
        end=params.end_date,
        page=params.page,
        limit=params.limit,
    )
    return envelope(
        [SupplierDebtReportRow.model_validate(row) for row in rows],
        {"page": params.page, "limit": params.limit, "total": total},
    )


@router.get("/finance")
async def finance_report(
    start_date: date | None = Query(default=None, alias="startDate"),
    end_date: date | None = Query(default=None, alias="endDate"),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.finance")),
) -> dict:
    """Finance summary cards (Income, Expense, Net Result, debts, losses)."""
    service = ReportsService(db)
    data = await service.finance_report(start=start_date, end=end_date)
    return envelope(FinanceReportOut.model_validate(data))


@router.get("/finance/summary")
async def finance_summary(
    start_date: date | None = Query(default=None, alias="startDate"),
    end_date: date | None = Query(default=None, alias="endDate"),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.finance")),
) -> dict:
    """Alias of GET /reports/finance — the endpoint the frontend calls."""
    return await finance_report(
        start_date=start_date,
        end_date=end_date,
        db=db,
        actor=actor,
    )


@router.get("/finance/entries")
async def finance_entries(
    params: ListParams = Depends(list_params),
    type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.finance")),
) -> dict:
    """Combined income/expense ledger table (income derived from POS sales)."""
    normalized_type = (type or "").strip().upper() or None
    if normalized_type not in (None, "INCOME", "EXPENSE"):
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="type must be INCOME or EXPENSE")
    service = ReportsService(db)
    rows, total = await service.finance_entries(
        q=params.q,
        entry_type=normalized_type,
        start=params.start_date,
        end=params.end_date,
        page=params.page,
        limit=params.limit,
    )
    return envelope(
        [FinanceEntryRow.model_validate(row) for row in rows],
        {"page": params.page, "limit": params.limit, "total": total},
    )


@router.post("/finance/expenses", status_code=201)
async def create_expense(
    payload: ExpenseCreate,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_permission("report.finance")),
    actor: User = Depends(require_permission("expense.create")),
) -> dict:
    """Record an operating expense (Finance Report only — no Expense page)."""
    service = ReportsService(db)
    expense = await service.create_expense(payload=payload, actor=actor)
    return envelope(ExpenseOut.model_validate(expense))


# ------------------------------------------------------------------- exports


def _csv_response(filename: str, header: list[str], rows: list[list]) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sales/export")
async def sales_report_export(
    format: str = Query(default="xlsx", pattern="^(pdf|xlsx)$"),
    params: ListParams = Depends(list_params),
    customer_id: UUID | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    cashier_id: UUID | None = Query(default=None),
    payment_method: str | None = Query(default=None, pattern="^(CASH|BANK_QR|CUSTOMER_DEBT)$"),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.sales")),
):
    service = ReportsService(db)
    rows = await service.sales_report_export(
        q=params.q,
        customer_id=customer_id,
        product_id=product_id,
        category_id=category_id,
        cashier_id=cashier_id,
        payment_method=payment_method,
        start=params.start_date,
        end=params.end_date,
    )
    data = {
        "period": {"from": params.start_date or "", "to": params.end_date or ""},
        "summary": {
            "grand_total": sum((row["grand_total"] for row in rows), Decimal("0")),
            "paid_amount": sum((row["paid_amount"] for row in rows), Decimal("0")),
            "remaining_amount": sum((row["remaining_amount"] for row in rows), Decimal("0")),
        },
        "rows": rows,
    }
    return await _render_report(
        db, title="Sales Report", filename="sales-report", format=format, data=data,
        columns=[
            "sale_date", "invoice_no", "customer_name", "item_count", "subtotal",
            "discount_amount", "other_charge", "grand_total", "paid_amount",
            "remaining_amount", "payment_method", "payment_status", "cashier_name",
        ],
    )


@router.get("/purchase/export")
@router.get("/purchases/export")
async def purchase_report_export(
    format: str = Query(default="xlsx", pattern="^(pdf|xlsx)$"),
    params: ListParams = Depends(list_params),
    supplier_id: UUID | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.purchase")),
):
    service = ReportsService(db)
    rows, _ = await service.purchase_report(
        q=params.q,
        supplier_id=supplier_id,
        product_id=product_id,
        status=status,
        start=params.start_date,
        end=params.end_date,
        page=1,
        limit=100000,
    )
    data = {
        "period": {"from": params.start_date or "", "to": params.end_date or ""},
        "summary": {
            "grand_total": sum((row["grand_total"] for row in rows), Decimal("0")),
            "paid_amount": sum((row["paid_amount"] for row in rows), Decimal("0")),
            "remaining_debt": sum((row["remaining_debt"] for row in rows), Decimal("0")),
        },
        "rows": rows,
    }
    return await _render_report(
        db, title="Purchase Report", filename="purchase-report", format=format, data=data,
        columns=[
            "document_no", "transaction_date", "supplier_name", "item_count", "subtotal",
            "other_cost", "discount", "grand_total", "paid_amount", "remaining_debt", "status", "note",
        ],
    )


@router.get("/customer-debts/export")
async def customer_debt_report_export(
    params: ListParams = Depends(list_params),
    customer_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None, pattern="^(UNPAID|PARTIAL|PAID)$"),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.customer_debt")),
):
    service = ReportsService(db)
    rows, _ = await service.customer_debt_report(
        q=params.q,
        customer_id=customer_id,
        status=status,
        start=params.start_date,
        end=params.end_date,
        page=1,
        limit=100000,
    )
    return _csv_response(
        "customer-debt-report.csv",
        [
            "Date", "Customer", "Invoice No.", "Invoice Total", "Paid Amount",
            "Remaining Amount", "Due Date", "Status",
        ],
        [
            [
                str(row["date"]), row["customer_name"], row["invoice_no"], str(row["invoice_total"]),
                str(row["paid_amount"]), str(row["remaining_amount"]),
                str(row["due_date"] or ""), row["status"],
            ]
            for row in rows
        ],
    )


@router.get("/supplier-debts/export")
async def supplier_debt_report_export(
    params: ListParams = Depends(list_params),
    supplier_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None, pattern="^(UNPAID|PARTIAL|PAID)$"),
    db: AsyncSession = Depends(get_db_session),
    actor: User = Depends(require_permission("report.supplier_debt")),
):
    service = ReportsService(db)
    rows, _ = await service.supplier_debt_report(
        q=params.q,
        supplier_id=supplier_id,
        status=status,
        start=params.start_date,
        end=params.end_date,
        page=1,
        limit=100000,
    )
    return _csv_response(
        "supplier-debt-report.csv",
        [
            "Date", "Supplier", "Stock In / Purchase No.", "Total Amount", "Paid Amount",
            "Remaining Amount", "Due Date", "Status",
        ],
        [
            [
                str(row["date"]), row["supplier_name"], row["document_no"], str(row["total_amount"]),
                str(row["paid_amount"]), str(row["remaining_amount"]),
                str(row["due_date"] or ""), row["status"],
            ]
            for row in rows
        ],
    )
