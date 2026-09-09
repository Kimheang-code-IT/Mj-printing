"""phase B: historical ledger and stock reconciliation backfill

Revision ID: 0015_stock_pos_b
Revises: 0014_stock_pos_a
"""

from alembic import op

revision = "0015_stock_pos_b"
down_revision = "0014_stock_pos_a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE payments SET payment_date = created_at")
    op.execute("UPDATE sales SET other_charge = COALESCE(delivery_price, 0)")
    op.execute("UPDATE sale_items SET cost_amount = ROUND(quantity * unit_cost, 2), gross_profit = ROUND(line_total - quantity * unit_cost, 2)")
    op.execute("UPDATE customers c SET current_debt = COALESCE((SELECT SUM(d.remaining_amount) FROM customer_debts d WHERE d.customer_id=c.id), 0)")
    op.execute("UPDATE suppliers s SET current_debt = COALESCE((SELECT SUM(d.remaining_amount) FROM supplier_debts d WHERE d.supplier_id=s.id), 0)")

    op.execute("""
        INSERT INTO customer_ledger_entries
            (id, customer_id, occurred_at, entry_type, reference_type, reference_id, reference_no, description, debit, credit, created_by)
        SELECT gen_random_uuid(), s.customer_id, s.sale_date, 'SALE', 'sale', s.id, s.invoice_no,
               'Historical sale ' || s.invoice_no, s.grand_total, 0, s.cashier_id
        FROM sales s JOIN customers c ON c.id=s.customer_id
        WHERE NOT c.is_walk_in
    """)
    op.execute("""
        INSERT INTO customer_ledger_entries
            (id, customer_id, occurred_at, entry_type, reference_type, reference_id, reference_no, description, debit, credit, created_by)
        SELECT gen_random_uuid(), p.customer_id, p.payment_date, 'PAYMENT', 'payment', p.id, p.payment_no,
               'Historical payment ' || p.payment_no, 0, p.amount, p.created_by
        FROM payments p JOIN customers c ON c.id=p.customer_id
        WHERE p.customer_id IS NOT NULL AND NOT c.is_walk_in
    """)
    op.execute("""
        INSERT INTO customer_ledger_entries
            (id, customer_id, occurred_at, entry_type, reference_type, reference_id, reference_no, description, debit, credit, created_by)
        SELECT gen_random_uuid(), s.customer_id, r.return_date, 'SALE_RETURN', 'sale_return', r.id, r.return_no,
               'Historical return ' || r.return_no, 0, r.refund_amount, r.created_by
        FROM sale_returns r JOIN sales s ON s.id=r.sale_id JOIN customers c ON c.id=s.customer_id
        WHERE NOT c.is_walk_in
    """)
    op.execute("""
        WITH balances AS (
            SELECT c.id, c.current_debt,
                   COALESCE(SUM(l.debit-l.credit), 0) AS reconstructed
            FROM customers c LEFT JOIN customer_ledger_entries l ON l.customer_id=c.id
            WHERE NOT c.is_walk_in GROUP BY c.id
        )
        INSERT INTO customer_ledger_entries
            (id, customer_id, occurred_at, entry_type, reference_type, reference_id, reference_no, description, debit, credit, created_by)
        SELECT gen_random_uuid(), id, TIMESTAMPTZ '1900-01-01 00:00:00+00', 'OPENING_BALANCE',
               'migration_reconciliation', id, 'MIGRATION', 'Opening balance reconciliation',
               GREATEST(current_debt-reconstructed, 0), GREATEST(reconstructed-current_debt, 0), NULL
        FROM balances WHERE current_debt <> reconstructed
    """)

    op.execute("""
        INSERT INTO supplier_ledger_entries
            (id, supplier_id, occurred_at, entry_type, reference_type, reference_id, reference_no, description, debit, credit, created_by)
        SELECT gen_random_uuid(), t.supplier_id, t.transaction_date, 'PURCHASE', 'legacy_stock_transaction', t.id, t.document_no,
               'Historical purchase ' || t.document_no, SUM(i.line_total), 0, t.created_by
        FROM stock_transactions t JOIN stock_transaction_items i ON i.stock_transaction_id=t.id
        WHERE t.transaction_type='STOCK_IN' AND t.supplier_id IS NOT NULL
        GROUP BY t.id
    """)
    op.execute("""
        INSERT INTO supplier_ledger_entries
            (id, supplier_id, occurred_at, entry_type, reference_type, reference_id, reference_no, description, debit, credit, created_by)
        SELECT gen_random_uuid(), p.supplier_id, p.payment_date, 'PAYMENT', 'payment', p.id, p.payment_no,
               'Historical payment ' || p.payment_no, 0, p.amount, p.created_by
        FROM payments p WHERE p.supplier_id IS NOT NULL
    """)
    op.execute("""
        WITH balances AS (
            SELECT s.id, s.current_debt,
                   COALESCE(SUM(l.debit-l.credit), 0) AS reconstructed
            FROM suppliers s LEFT JOIN supplier_ledger_entries l ON l.supplier_id=s.id GROUP BY s.id
        )
        INSERT INTO supplier_ledger_entries
            (id, supplier_id, occurred_at, entry_type, reference_type, reference_id, reference_no, description, debit, credit, created_by)
        SELECT gen_random_uuid(), id, TIMESTAMPTZ '1900-01-01 00:00:00+00', 'OPENING_BALANCE',
               'migration_reconciliation', id, 'MIGRATION', 'Opening balance reconciliation',
               GREATEST(current_debt-reconstructed, 0), GREATEST(reconstructed-current_debt, 0), NULL
        FROM balances WHERE current_debt <> reconstructed
    """)

    op.execute("""
        WITH ordered AS (
            SELECT id, quantity_delta, created_at,
                   SUM(quantity_delta) OVER (PARTITION BY product_id ORDER BY created_at, id) AS running
            FROM stock_movements
        )
        UPDATE stock_movements m
        SET occurred_at=o.created_at,
            qty_in=GREATEST(o.quantity_delta, 0),
            qty_out=GREATEST(-o.quantity_delta, 0),
            previous_qty=o.running-o.quantity_delta,
            new_balance=o.running
        FROM ordered o WHERE o.id=m.id
    """)
    op.execute("UPDATE stock_movements SET movement_type='PURCHASE' WHERE movement_type='STOCK_IN'")
    op.execute("UPDATE stock_movements SET movement_type='DAMAGED' WHERE movement_type IN ('DAMAGE', 'EXPIRE')")


def downgrade() -> None:
    op.execute("DELETE FROM supplier_ledger_entries")
    op.execute("DELETE FROM customer_ledger_entries")
    op.execute("UPDATE stock_movements SET movement_type='STOCK_IN' WHERE movement_type='PURCHASE'")
    op.execute("UPDATE stock_movements SET movement_type='DAMAGE' WHERE movement_type='DAMAGED'")
