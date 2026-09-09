from __future__ import annotations

from collections.abc import Iterable

from argon2 import PasswordHasher

SUPER_ADMIN_ROLE = "Administrator"
SUPER_ADMIN_PERMISSION = "ALL_PAGES"

# Stock & POS permission catalog (spec section 2.1.8).
PERMISSION_CATALOG: dict[str, tuple[str, ...]] = {
    "dashboard": ("view", "view_profit"),
    "category": ("view", "create", "update", "delete"),
    "brand": ("view", "create", "update", "delete"),
    "stock": ("view", "in", "adjust", "damage"),
    "stock_movements": ("view", "export"),
    "purchase": ("view", "create", "return"),
    "product": ("create", "update", "delete"),
    "supplier": ("view", "create", "update", "delete", "debt.pay"),
    "pos": ("access", "discount", "debt_sale", "print"),
    "customer": ("view", "create", "update", "delete", "debt.pay"),
    "report": ("sales", "purchase", "stock", "customer_debt", "supplier_debt", "finance"),
    "customer_reports": ("view", "export"),
    "customer_statements": ("view", "export"),
    "supplier_reports": ("view", "export"),
    "supplier_statements": ("view", "export"),
    "customer_payments": ("create",),
    "supplier_payments": ("create",),
    "expense": ("create",),  # Add Expense on Finance Report only (no Expense page)
    "user": ("manage",),
    "role": ("manage",),
    "sequence": ("manage",),
    "audit": ("view",),
    "settings": ("manage",),
}

SERVICE_PERMISSIONS = frozenset({"telegram.reset.send"})
ASSIGNABLE_PERMISSIONS = frozenset(
    f"{module}.{action}"
    for module, actions in PERMISSION_CATALOG.items()
    for action in actions
)


def permission_catalog() -> list[dict[str, object]]:
    return [
        {
            "module": module,
            "actions": list(actions),
            "permissions": [f"{module}.{action}" for action in actions],
        }
        for module, actions in PERMISSION_CATALOG.items()
    ]


def build_all_permissions() -> list[str]:
    codes = [key for group in permission_catalog() for key in group["permissions"]] + sorted(SERVICE_PERMISSIONS)
    codes.append(SUPER_ADMIN_PERMISSION)
    return codes


def normalize_role_permissions(values: Iterable[str] | None, *, allow_wildcard: bool = False) -> list[str]:
    normalized = list(dict.fromkeys(str(value).strip() for value in (values or []) if str(value).strip()))
    allowed = set(ASSIGNABLE_PERMISSIONS)
    if allow_wildcard:
        allowed.add(SUPER_ADMIN_PERMISSION)
    unknown = sorted(set(normalized) - allowed)
    if unknown:
        raise ValueError(f"Unknown permissions: {', '.join(unknown)}")
    granted = set(normalized)
    for permission in normalized:
        if permission.count(".") < 1:
            continue
        module, action = permission.rsplit(".", 1)
        view_permission = f"{module}.view"
        if action != "view" and view_permission in ASSIGNABLE_PERMISSIONS:
            granted.add(view_permission)
    ordered = [permission for permission in build_all_permissions() if permission in granted]
    if SUPER_ADMIN_PERMISSION in granted and SUPER_ADMIN_PERMISSION not in ordered:
        ordered.append(SUPER_ADMIN_PERMISSION)
    return ordered


def cashier_permissions() -> list[str]:
    return [
        "dashboard.view",
        "stock.view",
        "pos.access",
        "pos.print",
        "customer.view",
        "customer.create",
        "report.sales",
    ]


def stock_staff_permissions() -> list[str]:
    return [
        "dashboard.view",
        "category.view",
        "brand.view",
        "stock.view",
        "stock.in",
        "stock.adjust",
        "stock.damage",
        "product.create",
        "product.update",
        "supplier.view",
        "supplier.create",
    ]


def permissions_hasher() -> PasswordHasher:
    return PasswordHasher()


def effective_permissions(user: object) -> list[str]:
    """Resolve access exclusively from the authoritative related role."""
    role = getattr(user, "role_ref", None)
    if role is None:
        return []
    values = list(getattr(role, "permissions", None) or [])
    if getattr(role, "name", None) == SUPER_ADMIN_ROLE and SUPER_ADMIN_PERMISSION in values:
        return [SUPER_ADMIN_PERMISSION]
    return [value for value in values if value in ASSIGNABLE_PERMISSIONS]


def is_super_admin_user(user: object) -> bool:
    role = getattr(user, "role_ref", None)
    return bool(
        role
        and getattr(role, "name", None) == SUPER_ADMIN_ROLE
        and SUPER_ADMIN_PERMISSION in (getattr(role, "permissions", None) or [])
    )


def user_has_permission(user: object, required: str) -> bool:
    values = effective_permissions(user)
    return SUPER_ADMIN_PERMISSION in values or required in values


def is_super_admin(role: str | None, permissions: list[str] | None) -> bool:
    return role == SUPER_ADMIN_ROLE or bool(permissions and SUPER_ADMIN_PERMISSION in permissions)


def has_permission(role: str | None, permissions: list[str] | None, required: str) -> bool:
    return is_super_admin(role, permissions) or bool(permissions and required in permissions)
