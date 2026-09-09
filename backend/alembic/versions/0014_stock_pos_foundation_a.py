"""phase A: ledger, purchase, dimensional and movement foundation

Revision ID: 0014_stock_pos_a
Revises: 0013_delivery_multi_invoice
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014_stock_pos_a"
down_revision = "0013_delivery_multi_invoice"
branch_labels = None
depends_on = None


def _ledger(name: str, owner: str) -> None:
    op.create_table(
        name,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(f"{owner}_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{owner}s.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_type", sa.String(30), nullable=False),
        sa.Column("reference_type", sa.String(30), nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_no", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("debit", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("debit >= 0", name=f"ck_{owner}_ledger_debit_nonnegative"),
        sa.CheckConstraint("credit >= 0", name=f"ck_{owner}_ledger_credit_nonnegative"),
        sa.CheckConstraint("NOT (debit > 0 AND credit > 0)", name=f"ck_{owner}_ledger_one_sided"),
    )
    op.create_index(f"ix_{owner}_ledger_{owner}_occurred_id", name, [f"{owner}_id", "occurred_at", "id"])
    op.create_index(f"ix_{owner}_ledger_reference", name, ["reference_type", "reference_id"])


def upgrade() -> None:
    op.add_column("customers", sa.Column("current_debt", sa.Numeric(18, 2), nullable=False, server_default="0"))
    op.add_column("suppliers", sa.Column("current_debt", sa.Numeric(18, 2), nullable=False, server_default="0"))
    _ledger("customer_ledger_entries", "customer")
    _ledger("supplier_ledger_entries", "supplier")

    op.create_table(
        "purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("purchase_no", sa.String(50), nullable=False, unique=True),
        sa.Column("supplier_invoice_no", sa.String(100), nullable=True),
        sa.Column("purchase_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("other_cost", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("discount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("grand_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("balance_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="CONFIRMED"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("subtotal >= 0", name="ck_purchases_subtotal_nonnegative"),
        sa.CheckConstraint("other_cost >= 0", name="ck_purchases_other_cost_nonnegative"),
        sa.CheckConstraint("discount >= 0", name="ck_purchases_discount_nonnegative"),
        sa.CheckConstraint("grand_total >= 0", name="ck_purchases_total_nonnegative"),
        sa.CheckConstraint("paid_amount >= 0", name="ck_purchases_paid_nonnegative"),
        sa.CheckConstraint("balance_amount >= 0", name="ck_purchases_balance_nonnegative"),
    )
    op.create_index("ix_purchases_supplier_date", "purchases", ["supplier_id", "purchase_date"])
    op.create_index("ix_purchases_date", "purchases", ["purchase_date"])
    op.create_table(
        "purchase_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_code_snapshot", sa.String(100), nullable=False),
        sa.Column("product_name_snapshot", sa.String(200), nullable=False),
        sa.Column("height", sa.Numeric(18, 4), nullable=True),
        sa.Column("width", sa.Numeric(18, 4), nullable=True),
        sa.Column("square_meter", sa.Numeric(18, 4), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("calculation_mode", sa.String(20), nullable=False, server_default="NORMAL"),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("returned_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("quantity > 0", name="ck_purchase_items_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_purchase_items_price_nonnegative"),
    )
    op.create_index("ix_purchase_items_product_id", "purchase_items", ["product_id"])
    op.create_table(
        "purchase_returns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("return_no", sa.String(50), nullable=False, unique=True),
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("return_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "purchase_return_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("purchase_return_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_returns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purchase_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("purchase_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("quantity > 0", name="ck_purchase_return_items_quantity_positive"),
    )

    for table in ("sale_items", "stock_transaction_items"):
        op.add_column(table, sa.Column("height", sa.Numeric(18, 4), nullable=True))
        op.add_column(table, sa.Column("width", sa.Numeric(18, 4), nullable=True))
        op.add_column(table, sa.Column("square_meter", sa.Numeric(18, 4), nullable=True))
        op.add_column(table, sa.Column("calculation_mode", sa.String(20), nullable=False, server_default="NORMAL"))
    op.add_column("sale_items", sa.Column("cost_amount", sa.Numeric(18, 2), nullable=False, server_default="0"))
    op.add_column("sale_items", sa.Column("gross_profit", sa.Numeric(18, 2), nullable=False, server_default="0"))
    op.create_index("ix_sale_items_product_id", "sale_items", ["product_id"])
    op.add_column("sales", sa.Column("other_charge", sa.Numeric(18, 2), nullable=False, server_default="0"))
    op.add_column("sales", sa.Column("payment_method", sa.String(30), nullable=False, server_default="CASH"))
    op.add_column("sales", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_sales_customer_date", "sales", ["customer_id", "sale_date"])
    op.add_column("payments", sa.Column("payment_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    op.add_column("stock_movements", sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column("stock_movements", sa.Column("previous_qty", sa.Numeric(18, 4), nullable=False, server_default="0"))
    op.add_column("stock_movements", sa.Column("qty_in", sa.Numeric(18, 4), nullable=False, server_default="0"))
    op.add_column("stock_movements", sa.Column("qty_out", sa.Numeric(18, 4), nullable=False, server_default="0"))
    op.add_column("stock_movements", sa.Column("new_balance", sa.Numeric(18, 4), nullable=False, server_default="0"))
    op.create_check_constraint("ck_stock_movements_qty_in_nonnegative", "stock_movements", "qty_in >= 0")
    op.create_check_constraint("ck_stock_movements_qty_out_nonnegative", "stock_movements", "qty_out >= 0")
    op.create_check_constraint("ck_stock_movements_one_sided", "stock_movements", "NOT (qty_in > 0 AND qty_out > 0)")
    op.create_index("ix_stock_movements_product_occurred", "stock_movements", ["product_id", "occurred_at"])
    op.create_index("ix_stock_movements_type_occurred", "stock_movements", ["movement_type", "occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_stock_movements_type_occurred", table_name="stock_movements")
    op.drop_index("ix_stock_movements_product_occurred", table_name="stock_movements")
    for constraint in ("ck_stock_movements_one_sided", "ck_stock_movements_qty_out_nonnegative", "ck_stock_movements_qty_in_nonnegative"):
        op.drop_constraint(constraint, "stock_movements", type_="check")
    for column in ("new_balance", "qty_out", "qty_in", "previous_qty", "occurred_at"):
        op.drop_column("stock_movements", column)
    op.drop_column("payments", "payment_date")
    op.drop_index("ix_sales_customer_date", table_name="sales")
    for column in ("updated_at", "payment_method", "other_charge"):
        op.drop_column("sales", column)
    op.drop_index("ix_sale_items_product_id", table_name="sale_items")
    for column in ("gross_profit", "cost_amount", "calculation_mode", "square_meter", "width", "height"):
        op.drop_column("sale_items", column)
    for column in ("calculation_mode", "square_meter", "width", "height"):
        op.drop_column("stock_transaction_items", column)
    op.drop_table("purchase_return_items")
    op.drop_table("purchase_returns")
    op.drop_index("ix_purchase_items_product_id", table_name="purchase_items")
    op.drop_table("purchase_items")
    op.drop_index("ix_purchases_date", table_name="purchases")
    op.drop_index("ix_purchases_supplier_date", table_name="purchases")
    op.drop_table("purchases")
    op.drop_table("supplier_ledger_entries")
    op.drop_table("customer_ledger_entries")
    op.drop_column("suppliers", "current_debt")
    op.drop_column("customers", "current_debt")
