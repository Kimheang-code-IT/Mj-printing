# Agent instructions — MJ Printing Stock & POS

This repository is an existing Stock & POS system. Implementation guidance lives in:

1. **Skill:** `.cursor/skills/stock-pos-build/SKILL.md` (auto-discovered)
2. **References:** `removed-features.md`, `field-contracts.md`, `frontend-map.md`, `acceptance.md` in that skill folder
3. **Rules:** `.cursor/rules/stock-pos-*.mdc`
4. **Full specification:** `docs/AGENT_STOCK_POS_FULL_IMPLEMENTATION.md`

Modify end-to-end (frontend + backend + PostgreSQL + Alembic + Redis + Docker + tests). Do not rebuild from scratch. Do not add Delivery Note, UOM management, minimum stock, expired stock, customer credit limit, or sale delivery fee.

**Current snapshot:** frontend allowlist pages + dimensional POS/purchase UI + removal of forbidden UI are largely done. Prefer backend Phase 4 cleanup, mock/i18n dead-code purge, and deepening reports/statements next — see skill “Remaining cleanup” and `acceptance.md`.
