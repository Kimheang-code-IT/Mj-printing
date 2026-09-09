from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProductCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sku: str = Field(min_length=1, max_length=100)
    barcode: str | None = Field(default=None, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    category_id: UUID | None = None
    brand_id: UUID | None = None
    cost_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    selling_price: Decimal = Field(
        gt=0,
        validation_alias=AliasChoices("selling_price", "salePrice"),
    )
    image_object_key: str | None = Field(default=None, max_length=500)
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|INACTIVE)$")
    note: str | None = None

    @field_validator("sku", "barcode", "name")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class ProductUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sku: str | None = Field(default=None, min_length=1, max_length=100)
    barcode: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: UUID | None = None
    brand_id: UUID | None = None
    cost_price: Decimal | None = Field(default=None, ge=0)
    # The UI sends salePrice; changing it adds + activates a new price version.
    selling_price: Decimal | None = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices("selling_price", "salePrice"),
    )
    image_object_key: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")
    note: str | None = None

    @field_validator("sku", "name")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sku: str
    barcode: str | None
    name: str
    category_id: UUID | None
    category_name: str | None = None
    brand_id: UUID | None = None
    brand_name: str | None = None
    cost_price: Decimal
    selling_price: Decimal
    profit_percent: Decimal
    image_object_key: str | None
    image_url: str | None = None
    status: str
    note: str | None
    quantity: Decimal = Decimal("0")
    current_stock: Decimal = Decimal("0")
    average_cost: Decimal = Decimal("0.00")
    # Derived from immutable stock_movements (never persisted on the product).
    stock_in_qty: Decimal = Decimal("0")
    stock_out_qty: Decimal = Decimal("0")
    damage_qty: Decimal = Decimal("0")
    created_at: datetime
    updated_at: datetime

# ---------------------------------------------------------------- stock operations


class StockInItem(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)
    height: Decimal | None = Field(default=None, ge=0)
    width: Decimal | None = Field(default=None, ge=0)
    calculation_mode: str = Field(default="NORMAL", pattern="^(NORMAL|DIMENSIONAL)$")
    note: str | None = None


class StockInRequest(BaseModel):
    supplier_id: UUID | None = None
    transaction_date: datetime | None = None
    reference_no: str | None = Field(default=None, max_length=100)
    note: str | None = None
    paid_amount: Decimal = Field(default=Decimal("0"), ge=0)
    items: list[StockInItem] = Field(min_length=1)


class AdjustmentItem(BaseModel):
    product_id: UUID
    system_quantity: Decimal | None = Field(default=None, ge=0)
    actual_quantity: Decimal = Field(ge=0)
    reason: str = Field(min_length=1, max_length=500)
    note: str | None = None


class StockAdjustmentRequest(BaseModel):
    transaction_date: datetime | None = None
    reference_no: str | None = Field(default=None, max_length=100)
    note: str | None = None
    items: list[AdjustmentItem] = Field(min_length=1)


class DamageItem(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)
    reason: str = Field(min_length=1, max_length=500)
    note: str | None = None


class StockDamageRequest(BaseModel):
    transaction_date: datetime | None = None
    reference_no: str | None = Field(default=None, max_length=100)
    note: str | None = None
    items: list[DamageItem] = Field(min_length=1)


class OperationItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    product_name: str | None = None
    sku: str | None = None
    quantity: Decimal
    unit_cost: Decimal
    system_quantity: Decimal | None
    actual_quantity: Decimal | None
    height: Decimal | None = None
    width: Decimal | None = None
    square_meter: Decimal | None = None
    calculation_mode: str = "NORMAL"
    reason: str | None
    line_total: Decimal


class StockOperationOut(BaseModel):
    id: UUID
    document_no: str
    transaction_type: str
    supplier_id: UUID | None
    transaction_date: datetime
    reference_no: str | None
    note: str | None
    status: str
    total_amount: Decimal
    paid_amount: Decimal
    debt_created: bool = False
    debt_id: UUID | None = None
    items: list[OperationItemOut]


class QuickStockOperationRequest(BaseModel):
    """Single-product quick operation from the Stock list
    (`type`: stock_in | adjustment | damage)."""

    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(default="stock_in", pattern="^(stock_in|adjustment|damage)$")
    product_id: UUID = Field(validation_alias=AliasChoices("product_id", "productId"))
    quantity: Decimal
    note: str | None = Field(default=None, max_length=1000)
    transaction_date: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("transaction_date", "transactionDate", "date"),
    )
    unit_cost: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("unit_cost", "unitCost"),
    )


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    product_name: str | None = None
    movement_type: str
    quantity_delta: Decimal
    occurred_at: datetime
    previous_qty: Decimal
    qty_in: Decimal
    qty_out: Decimal
    new_balance: Decimal
    unit_cost: Decimal
    reference_type: str
    reference_id: UUID
    document_no: str | None
    note: str | None
    created_at: datetime


class PurchaseItemRequest(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0)
    height: Decimal | None = Field(default=None, ge=0)
    width: Decimal | None = Field(default=None, ge=0)
    calculation_mode: str = Field(default="NORMAL", pattern="^(NORMAL|DIMENSIONAL)$")
    unit_price: Decimal = Field(ge=0)
    note: str | None = None

    @field_validator("calculation_mode")
    @classmethod
    def validate_dimensions(cls, value: str) -> str:
        return value.upper()


class PurchaseCreateRequest(BaseModel):
    supplier_id: UUID
    supplier_invoice_no: str | None = Field(default=None, max_length=100)
    purchase_date: datetime | None = None
    other_cost: Decimal = Field(default=Decimal("0"), ge=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0)
    paid_amount: Decimal = Field(default=Decimal("0"), ge=0)
    note: str | None = None
    items: list[PurchaseItemRequest] = Field(min_length=1)


class PurchaseReturnItemRequest(BaseModel):
    purchase_item_id: UUID
    quantity: Decimal = Field(gt=0)


class PurchaseReturnRequest(BaseModel):
    return_date: datetime | None = None
    reason: str = Field(min_length=1)
    items: list[PurchaseReturnItemRequest] = Field(min_length=1)


class ProductHistoryRow(BaseModel):
    """Compact row for the product stock-history dialogs (spec section 2.1.5)."""

    id: UUID
    date: datetime
    type: str
    kind: str
    qty: Decimal
    reference: str | None = None
    reference_type: str
    user: str | None = None
    note: str | None = None


# ---------------------------------------------------------------- sale prices


class SalePriceCreate(BaseModel):
    """Add Sale Price payload (snake_case and camelCase accepted)."""

    model_config = ConfigDict(populate_by_name=True)

    sale_price: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=2,
        validation_alias=AliasChoices("sale_price", "salePrice", "price"),
    )
    effective_date: date | None = Field(
        default=None,
        validation_alias=AliasChoices("effective_date", "effectiveDate", "date"),
    )
    product_id: UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("product_id", "productId"),
    )


class SalePriceUpdate(BaseModel):
    """PATCH payload: `{isActive: true}` runs the activate transaction."""

    model_config = ConfigDict(populate_by_name=True)

    is_active: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("is_active", "isActive"),
    )
