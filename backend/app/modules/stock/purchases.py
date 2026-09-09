"""Transactional purchases and purchase returns."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.auth.models import User
from app.modules.pos.models import Payment
from app.modules.stock.models import Purchase, PurchaseItem, PurchaseReturn, PurchaseReturnItem
from app.modules.stock.repository import ProductRepository
from app.modules.stock.service import apply_stock_movement
from app.modules.suppliers.models import Supplier, SupplierLedgerEntry
from app.shared.audit.service import record_audit
from app.shared.documents import allocate_document_number

Q2 = Decimal("0.01")
Q4 = Decimal("0.0001")


def q2(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Q2, rounding=ROUND_HALF_UP)


def q4(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Q4, rounding=ROUND_HALF_UP)


def purchase_out(row: Purchase) -> dict:
    return {
        "id": row.id,
        "purchase_no": row.purchase_no,
        "supplier_invoice_no": row.supplier_invoice_no,
        "purchase_date": row.purchase_date,
        "supplier_id": row.supplier_id,
        "note": row.note,
        "subtotal": row.subtotal,
        "other_cost": row.other_cost,
        "discount": row.discount,
        "grand_total": row.grand_total,
        "paid_amount": row.paid_amount,
        "balance_amount": row.balance_amount,
        "status": row.status,
        "created_by": row.created_by,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_code_snapshot": item.product_code_snapshot,
                "product_name_snapshot": item.product_name_snapshot,
                "height": item.height,
                "width": item.width,
                "square_meter": item.square_meter,
                "quantity": item.quantity,
                "calculation_mode": item.calculation_mode,
                "unit_price": item.unit_price,
                "amount": item.amount,
                "returned_quantity": item.returned_quantity,
                "note": item.note,
            }
            for item in row.items
        ],
    }


class PurchaseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.products = ProductRepository(session)

    async def create(self, payload, *, actor: User) -> dict:
        supplier = await self.session.scalar(
            select(Supplier).where(Supplier.id == payload.supplier_id).with_for_update()
        )
        if supplier is None:
            raise NotFoundError("Supplier not found")
        if supplier.status != "ACTIVE":
            raise ValidationError("Inactive suppliers cannot be used")

        products = {}
        for item in payload.items:
            if item.product_id in products:
                raise ValidationError("Duplicate product in purchase", field_errors={"items": "Duplicate product"})
            product = await self.products.get(item.product_id)
            if product is None:
                raise NotFoundError("Product not found")
            products[item.product_id] = product

        purchase_no = await allocate_document_number(self.session, "PURCHASE")
        occurred_at = payload.purchase_date or datetime.now(timezone.utc)
        purchase = Purchase(
            purchase_no=purchase_no,
            supplier_invoice_no=payload.supplier_invoice_no,
            purchase_date=occurred_at,
            supplier_id=supplier.id,
            note=payload.note,
            subtotal=Decimal("0"),
            other_cost=q2(payload.other_cost),
            discount=q2(payload.discount),
            grand_total=Decimal("0"),
            paid_amount=q2(payload.paid_amount),
            balance_amount=Decimal("0"),
            created_by=actor.id,
        )
        self.session.add(purchase)
        await self.session.flush()

        subtotal = Decimal("0")
        for item in payload.items:
            product = products[item.product_id]
            quantity = q4(item.quantity)
            square_meter = None
            billed_quantity = quantity
            if item.calculation_mode == "DIMENSIONAL":
                if item.height is None or item.width is None:
                    raise ValidationError(
                        "Dimensional items require height and width",
                        field_errors={"items": "Missing dimensions"},
                    )
                square_meter = q4(item.height * item.width * quantity)
                billed_quantity = square_meter
            amount = q2(billed_quantity * item.unit_price)
            self.session.add(
                PurchaseItem(
                    purchase_id=purchase.id,
                    product_id=product.id,
                    product_code_snapshot=product.sku,
                    product_name_snapshot=product.name,
                    height=item.height,
                    width=item.width,
                    square_meter=square_meter,
                    quantity=quantity,
                    calculation_mode=item.calculation_mode,
                    unit_price=q2(item.unit_price),
                    amount=amount,
                    note=item.note,
                )
            )
            await apply_stock_movement(
                self.session,
                product_id=product.id,
                movement_type="PURCHASE",
                quantity_delta=quantity,
                unit_cost=item.unit_price,
                reference_type="purchase",
                reference_id=purchase.id,
                created_by=actor.id,
                document_no=purchase_no,
                note=item.note,
                occurred_at=occurred_at,
            )
            subtotal += amount

        purchase.subtotal = q2(subtotal)
        purchase.grand_total = q2(purchase.subtotal + purchase.other_cost - purchase.discount)
        if purchase.grand_total < 0:
            raise ValidationError("Discount cannot make the purchase total negative")
        if purchase.paid_amount > purchase.grand_total:
            raise ValidationError("Paid amount cannot exceed the purchase total")
        purchase.balance_amount = q2(purchase.grand_total - purchase.paid_amount)

        self.session.add(SupplierLedgerEntry(
            supplier_id=supplier.id, occurred_at=occurred_at, entry_type="PURCHASE",
            reference_type="purchase", reference_id=purchase.id, reference_no=purchase_no,
            description=f"Purchase {purchase_no}", debit=purchase.grand_total, credit=Decimal("0"),
            created_by=actor.id,
        ))
        if purchase.paid_amount > 0:
            payment = Payment(
                payment_no=await allocate_document_number(self.session, "SUPPLIER_PAYMENT"),
                supplier_id=supplier.id,
                payment_type="PURCHASE_PAYMENT",
                payment_method="CASH",
                amount=purchase.paid_amount,
                reference_no=purchase_no,
                payment_date=occurred_at,
                created_by=actor.id,
            )
            self.session.add(payment)
            await self.session.flush()
            self.session.add(SupplierLedgerEntry(
                supplier_id=supplier.id, occurred_at=occurred_at, entry_type="PAYMENT",
                reference_type="payment", reference_id=payment.id, reference_no=payment.payment_no,
                description=f"Payment for {purchase_no}", debit=Decimal("0"), credit=purchase.paid_amount,
                created_by=actor.id,
            ))
        supplier.current_debt = q2(supplier.current_debt + purchase.balance_amount)
        await record_audit(
            self.session, action="purchase", module="stock", user_id=actor.id,
            entity_type="purchase", entity_id=purchase.id,
            new_values={"purchase_no": purchase_no, "grand_total": str(purchase.grand_total)},
        )
        await self.session.commit()
        await self.session.refresh(purchase)
        await self.session.refresh(purchase, attribute_names=["items"])
        return purchase_out(purchase)

    async def get(self, purchase_id: UUID) -> Purchase:
        row = await self.session.get(Purchase, purchase_id)
        if row is None:
            raise NotFoundError("Purchase not found")
        return row

    async def list(self, *, q, supplier_id, start_at, end_at, page, limit):
        conditions = []
        if q:
            conditions.append(Purchase.purchase_no.ilike(f"%{q.strip()}%"))
        if supplier_id:
            conditions.append(Purchase.supplier_id == supplier_id)
        if start_at:
            conditions.append(Purchase.purchase_date >= start_at)
        if end_at:
            conditions.append(Purchase.purchase_date <= end_at)
        total = await self.session.scalar(select(func.count()).select_from(Purchase).where(*conditions))
        rows = await self.session.scalars(
            select(Purchase).where(*conditions).order_by(Purchase.purchase_date.desc())
            .offset((page - 1) * limit).limit(limit)
        )
        return [purchase_out(row) for row in rows.all()], int(total or 0)

    async def create_return(self, purchase_id: UUID, payload, *, actor: User) -> dict:
        purchase = await self.session.scalar(
            select(Purchase).where(Purchase.id == purchase_id).with_for_update()
        )
        if purchase is None:
            raise NotFoundError("Purchase not found")
        supplier = await self.session.scalar(
            select(Supplier).where(Supplier.id == purchase.supplier_id).with_for_update()
        )
        items = {item.id: item for item in purchase.items}
        occurred_at = payload.return_date or datetime.now(timezone.utc)
        row = PurchaseReturn(
            return_no=await allocate_document_number(self.session, "PURCHASE_RETURN"),
            purchase_id=purchase.id, return_date=occurred_at, total_amount=Decimal("0"),
            reason=payload.reason, created_by=actor.id,
        )
        self.session.add(row)
        await self.session.flush()
        total = Decimal("0")
        for requested in payload.items:
            source = items.get(requested.purchase_item_id)
            if source is None:
                raise NotFoundError("Purchase item not found")
            if requested.quantity > source.quantity - source.returned_quantity:
                raise ValidationError("Return quantity exceeds the remaining purchased quantity")
            amount = q2(source.amount * requested.quantity / source.quantity)
            source.returned_quantity = q4(source.returned_quantity + requested.quantity)
            self.session.add(PurchaseReturnItem(
                purchase_return_id=row.id, purchase_item_id=source.id, product_id=source.product_id,
                quantity=q4(requested.quantity), amount=amount,
            ))
            await apply_stock_movement(
                self.session, product_id=source.product_id, movement_type="PURCHASE_RETURN",
                quantity_delta=-requested.quantity, unit_cost=source.unit_price,
                reference_type="purchase_return", reference_id=row.id, created_by=actor.id,
                document_no=row.return_no, note=payload.reason, occurred_at=occurred_at,
            )
            total += amount
        row.total_amount = q2(total)
        self.session.add(SupplierLedgerEntry(
            supplier_id=purchase.supplier_id, occurred_at=occurred_at, entry_type="PURCHASE_RETURN",
            reference_type="purchase_return", reference_id=row.id, reference_no=row.return_no,
            description=f"Return for {purchase.purchase_no}", debit=Decimal("0"), credit=row.total_amount,
            created_by=actor.id,
        ))
        supplier.current_debt = q2(supplier.current_debt - row.total_amount)
        await record_audit(
            self.session, action="purchase_return", module="stock", user_id=actor.id,
            entity_type="purchase_return", entity_id=row.id,
            new_values={"return_no": row.return_no, "amount": str(row.total_amount)},
        )
        await self.session.commit()
        return {"id": row.id, "return_no": row.return_no, "purchase_id": purchase.id, "total_amount": row.total_amount}
