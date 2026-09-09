"""phase C: remove UOM, minimum, expiry and legacy sale fields

Revision ID: 0016_stock_pos_c
Revises: 0015_stock_pos_b
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0016_stock_pos_c"
down_revision = "0015_stock_pos_b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM role_permissions rp USING permissions p WHERE rp.permission_id=p.id AND (p.module IN ('uom','delivery') OR p.code IN ('stock.expire'))")
    op.execute("DELETE FROM permissions WHERE module IN ('uom','delivery') OR code='stock.expire'")
    op.execute("DELETE FROM document_sequences WHERE document_type IN ('STOCK_EXPIRE','DELIVERY_NOTE')")
    op.execute("DELETE FROM system_settings WHERE key ILIKE '%expiry%' OR key ILIKE '%expired%' OR key ILIKE '%minimum_stock%' OR key ILIKE '%credit_limit%'")

    op.drop_index("ix_products_uom_id", table_name="products")
    op.drop_constraint("fk_products_uom_id", "products", type_="foreignkey")
    for column in ("uom_id", "uom_conversions", "minimum_stock", "expiry_tracking"):
        op.drop_column("products", column)
    op.execute("ALTER TABLE customers DROP COLUMN IF EXISTS credit_limit")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS min_stock")

    for column in ("uom_id", "uom_code", "uom_symbol", "factor_to_base"):
        op.drop_column("sale_items", column)
    for column in ("batch_no", "expiry_date"):
        op.drop_column("stock_transaction_items", column)
        op.drop_column("stock_movements", column)
    op.drop_column("sales", "delivery_price")


def downgrade() -> None:
    op.add_column("sales", sa.Column("delivery_price", sa.Numeric(18, 2), nullable=False, server_default="0"))
    op.add_column("stock_movements", sa.Column("expiry_date", sa.Date(), nullable=True))
    op.add_column("stock_movements", sa.Column("batch_no", sa.String(100), nullable=True))
    op.add_column("stock_transaction_items", sa.Column("expiry_date", sa.Date(), nullable=True))
    op.add_column("stock_transaction_items", sa.Column("batch_no", sa.String(100), nullable=True))
    op.add_column("sale_items", sa.Column("factor_to_base", sa.Numeric(18, 6), nullable=False, server_default="1"))
    op.add_column("sale_items", sa.Column("uom_symbol", sa.String(20), nullable=True))
    op.add_column("sale_items", sa.Column("uom_code", sa.String(50), nullable=True))
    op.add_column("sale_items", sa.Column("uom_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("products", sa.Column("expiry_tracking", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("products", sa.Column("minimum_stock", sa.Numeric(18, 4), nullable=False, server_default="0"))
    op.add_column("products", sa.Column("uom_conversions", postgresql.JSONB(), nullable=True))
    op.add_column("products", sa.Column("uom_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE products SET uom_id=(SELECT id FROM units_of_measure ORDER BY code LIMIT 1)")
    op.alter_column("products", "uom_id", nullable=False)
    op.create_foreign_key("fk_products_uom_id", "products", "units_of_measure", ["uom_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_products_uom_id", "products", ["uom_id"])
