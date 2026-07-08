# Auto-Code Sequences

Every invoice, account, company, and item in the system gets an auto-generated human-readable code (e.g. PUR-0001, SAL-0002, ACC-0003). These are scoped per organization-branch-type combination so each branch has its own independent counter starting from 0001.

---

## BranchSequence Model

`BranchSequence` stores the next available integer for each combination of organization, branch, and sequence type. A unique constraint ensures only one row exists per (org or branch) + type.

When a new invoice is saved, the model's `save()` override calls `get_next_sequence_value(organization, branch, prefix)` and formats the result into the code field before persisting.

---

## get_next_sequence_value

This function lives in `organizations/models.py` and is imported by any model that needs auto-sequencing.

The function must be called inside an active database transaction (which it always is, since model saves in invoice serializers happen inside `with transaction.atomic()`). It works as follows:

It tries to fetch and lock the existing BranchSequence row using `select_for_update()`. This is a `filter().first()` call rather than `get()`. Using `filter().first()` is deliberate — if no row exists it returns `None` without raising an exception, which matters because raising `DoesNotExist` inside a nested savepoint sets Django's `needs_rollback` flag on the connection and breaks the outer transaction.

If the row does not exist, the function creates it with `next_val=1` wrapped in its own `with transaction.atomic()` savepoint. If two concurrent requests both try to create the row at the same time, one will hit an `IntegrityError`. `IntegrityError` is a real database exception, so the savepoint rollback cleans it up without setting `needs_rollback`, and the losing request simply falls through to fetch the row created by the winner.

After obtaining the row (either existing or newly created), the function reads `next_val`, increments it, saves with `update_fields=['next_val']`, and returns the original value.

The caller formats the returned integer into the final code:

```python
self.purchase_code = f"PUR-{next_val:04d}"   # → PUR-0001
```

---

## Supported Sequence Types

- `PUR` — Purchase Invoices
- `SAL` — Sales Invoices
- `RET` — Purchase Returns
- `DMR` — Damage Returns
- `DMR-REC` — Damage Receiving
- `ACC` — Account Opening codes
- `COM` — Company codes
- `ITM` — Item codes
- `CAT` — Item Category codes

---

## Why Not Use Database Sequences

PostgreSQL native sequences would be simpler, but the system needs per-branch counters with a human-readable format, and it needs them to work across multiple Django apps without coupling to PostgreSQL-specific syntax. The BranchSequence table approach keeps this portable and explicit.

The `select_for_update()` lock ensures two simultaneous invoice creations from the same branch never get the same number, even under concurrent load.
