"""Seed entrypoint (`python -m app.seed`), run by the api container on start.

- syncs the permission catalog and the Administrator system role
- bootstraps the initial administrator from SEED_ADMIN_* when no user exists

Local Docker convenience only; production must supply strong SEED_ADMIN_*
values (validated against the same rules as the API config).
"""

import asyncio

from app.core.config import settings


async def seed() -> None:
    from app.core.database import SessionFactory
    from app.core.permissions import SUPER_ADMIN_PERMISSION, build_all_permissions
    from app.core.security import hash_password

    # Import every model module before any ORM work so SQLAlchemy can
    # configure all mappers (relationships resolve by class name).
    import app.modules.administration.models  # noqa: F401
    import app.modules.auth.models  # noqa: F401
    import app.modules.brands.models  # noqa: F401
    import app.modules.categories.models  # noqa: F401
    import app.modules.customers.models  # noqa: F401
    import app.modules.pos.models  # noqa: F401
    import app.modules.stock.models  # noqa: F401
    import app.modules.suppliers.models  # noqa: F401
    import app.shared.audit.models  # noqa: F401
    import app.shared.documents.models  # noqa: F401

    from app.modules.auth.models import User
    from app.modules.auth.repository import RoleRepository, UserRepository
    from app.modules.customers.models import Customer
    from app.shared.documents import allocate_document_number, ensure_default_sequences

    async with SessionFactory() as session:
        roles = RoleRepository(session)
        users = UserRepository(session)

        await roles.sync_permission_catalog(build_all_permissions())
        admin_role = await roles.get_by_name("Administrator")
        if admin_role is None:
            admin_role = await roles.create_system_role(
                "Administrator", "Full system access", [SUPER_ADMIN_PERMISSION]
            )

        if not await users.any_user_exists():
            session.add(
                User(
                    full_name=settings.seed_admin_name,
                    email=settings.seed_admin_email.lower(),
                    password_hash=hash_password(settings.seed_admin_password),
                    telegram_chat_id=None,
                    telegram_verified=False,
                    role_id=admin_role.id,
                    status="ACTIVE",
                )
            )
            await session.flush()

        # Default document sequences are inserted idempotently.
        await ensure_default_sequences(session)

        if not settings.is_production:
            await _seed_sample_master_data(session)

        # System walk-in customer for POS sales (spec section 2.1.6).
        from sqlalchemy import select

        walk_in = await session.scalar(select(Customer).where(Customer.is_walk_in.is_(True)))
        if walk_in is None:
            session.add(
                Customer(
                    code=await allocate_document_number(session, "CUSTOMER"),
                    name="Walk-in Customer",
                    status="ACTIVE",
                    is_walk_in=True,
                )
            )
            await session.flush()

        await session.commit()


async def _seed_sample_master_data(session) -> None:
    """Local-Docker convenience sample brands. Production seeds no demo data."""
    from sqlalchemy import select

    from app.modules.brands.models import Brand

    for code, name in (("GEN", "Generic"), ("PREM", "Premium")):
        exists = await session.scalar(select(Brand).where(Brand.code == code))
        if exists is None:
            session.add(Brand(code=code, name=name, status="ACTIVE"))
    await session.flush()


def main() -> None:
    if settings.is_production:
        weak = (
            not settings.seed_admin_password
            or len(settings.seed_admin_password) < 12
            or settings.seed_admin_password == "123456"
        )
        if weak:
            raise RuntimeError("SEED_ADMIN_PASSWORD is too weak for production seeding")
    asyncio.run(seed())


if __name__ == "__main__":
    main()
