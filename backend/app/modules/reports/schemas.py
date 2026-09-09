"""Report row schemas — spec section 2.1.10."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, computed_field


class SalesReportRow(BaseModel):
    sale_id: UUID
    sale_date: datetime
    invoice_no: str
    customer_name: str | None
    customer_phone: str | None = None
    customer_address: str | None = None
    item_count: int = 0
    subtotal: Decimal
    discount_amount: Decimal
    other_charge: Decimal = Decimal("0.00")
    grand_total: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    payment_status: str
    cashier_name: str | None
    payment_method: str


class PurchaseReportRow(BaseModel):
    transaction_id: UUID
    document_no: str
    transaction_date: datetime
    supplier_name: str | None
    supplier_phone: str | None = None
    supplier_address: str | None = None
    item_count: int = 0
    subtotal: Decimal
    other_cost: Decimal = Decimal("0.00")
    discount: Decimal = Decimal("0.00")
    grand_total: Decimal
    paid_amount: Decimal
    remaining_debt: Decimal
    status: str
    note: str | None = None

class CustomerDebtReportRow(BaseModel):
    debt_id: UUID
    customer_id: UUID
    customer_name: str
    customer_code: str
    date: datetime
    invoice_no: str
    invoice_total: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    due_date: date | None
    status: str
    created_at: datetime


class SupplierDebtReportRow(BaseModel):
    debt_id: UUID
    supplier_id: UUID
    supplier_name: str
    supplier_code: str
    date: datetime
    document_no: str
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    due_date: date | None
    status: str
    created_at: datetime


class FinanceReportOut(BaseModel):
    """Finance summary cards (spec 2.1.10). Net Result includes operating
    expenses recorded via Add Expense on the Finance Report.

    `income/expense/net/outstanding` are aliases the frontend financeSummary
    mapper reads; they match the canonical cards exactly.
    """

    period_start: date
    period_end: date
    total_sales: Decimal
    total_expense: Decimal
    total_purchase_cost: Decimal
    total_customer_debt: Decimal
    total_supplier_debt: Decimal
    cost_of_goods_sold: Decimal
    stock_damage_loss: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    net_result: Decimal

    @computed_field
    @property
    def income(self) -> Decimal:
        return self.total_sales

    @computed_field
    @property
    def expense(self) -> Decimal:
        return self.operating_expenses

    @computed_field
    @property
    def net(self) -> Decimal:
        return self.net_result

    @computed_field
    @property
    def outstanding(self) -> Decimal:
        return self.total_customer_debt + self.total_supplier_debt


class ExpenseCreate(BaseModel):
    """Add Expense payload — allowed on the Finance Report only."""

    date: date
    category: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    reference: str | None = Field(default=None, max_length=100)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    payment_method: Literal["CASH", "BANK_QR", "CARD", "OTHER"] | None = Field(
        default=None,
        validation_alias=AliasChoices("payment_method", "paymentMethod"),
    )


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    expense_date: date
    category: str
    description: str | None
    amount: Decimal
    payment_method: str | None
    created_by: UUID | None = None
    created_by_name: str | None = None
    created_at: datetime


class FinanceEntryRow(BaseModel):
    """One combined income/expense ledger row of the Finance table.

    `type` is lowercase income/expense for the HTTP mapper; `category`,
    `paymentMethod` and `user` are the camelCase keys the mapper reads.
    """

    id: UUID
    date: datetime
    type: Literal["income", "expense"]
    reference: str
    category: str | None = None
    description: str | None
    amount: Decimal
    payment_method: str | None = None
    paymentMethod: str | None = None
    created_by_name: str | None = None
    user: str | None = None
    created_at: datetime
