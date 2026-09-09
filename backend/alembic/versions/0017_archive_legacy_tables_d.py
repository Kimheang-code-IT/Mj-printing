"""phase D: remove obsolete runtime tables while preserving legacy rows

Revision ID: 0017_stock_pos_d
Revises: 0016_stock_pos_c

The obsolete tables are renamed into explicit archives instead of destroying
production history. They are not imported or queried by runtime code.
"""

from alembic import op

revision = "0017_stock_pos_d"
down_revision = "0016_stock_pos_c"
branch_labels = None
depends_on = None


RENAMES = (
    ("telegram_expiry_alert_state", "legacy_telegram_alert_archive"),
    ("delivery_note_items", "legacy_fulfillment_items_archive"),
    ("delivery_note_sales", "legacy_fulfillment_sales_archive"),
    ("delivery_notes", "legacy_fulfillment_archive"),
    ("units_of_measure", "legacy_units_archive"),
)


def upgrade() -> None:
    for old, archived in RENAMES:
        op.rename_table(old, archived)


def downgrade() -> None:
    for old, archived in reversed(RENAMES):
        op.rename_table(archived, old)
