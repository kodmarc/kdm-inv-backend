# Double-Entry Accounting

Every invoice and return in the system automatically creates journal entries when saved. No manual journaling is required. This happens inside the serializer's `create()` and `update()` methods, wrapped in a single database transaction.

---

## Purchase Invoice Entries

When a purchase invoice is created with status `pending`, two journal items are posted:

A debit to the `account` (the purchase expense account) for `net_amount` — recording that money was spent or is owed from that account.

A credit to the `supplier` (party's payable ledger) for `net_amount` — recording that we owe the supplier.

When a purchase invoice is created with status `paid`, a second journal entry is also created alongside the above:

A debit to the `supplier` (party's payable ledger) for `net_amount` — settling the payable.

A credit to the `account` (cash/bank) for `net_amount` — recording the cash paid out.

This means a paid purchase invoice always produces two JournalEntry records with two JournalItems each, totaling four postings. A pending invoice produces one JournalEntry with two postings.

In addition to the journal entries, the supplier's `balance_amount` is incremented by `net_amount` when status is `pending` (we owe them more), and the account's `balance` is incremented by `net_amount` (our ledger account reflects the purchase value).

---

## Sales Invoice Entries

When a sales invoice is created with status `pending`:

A debit to the `party` (customer's receivable ledger) for `net_amount` — they owe us.

A credit to the `account` (the revenue/income account) for `net_amount` — recording revenue earned.

When created with status `paid`, an additional settlement entry is added:

A debit to the `account` (cash/bank) for `net_amount` — recording the cash received.

A credit to the `party` (receivable ledger) for `net_amount` — clearing the receivable.

The party's `balance_amount` is incremented when pending (they owe us more), and the account's `balance` is incremented (reflecting cash or revenue).

---

## Update Behavior

When an invoice is edited, the serializer's `update()` method:

1. Deletes all existing JournalEntry records linked to the invoice
2. Reverses the old stock movements (subtracts the old line item quantities)
3. Reverses the old party balance and account balance changes
4. Applies the new line items, party balance, and account balance
5. Creates fresh journal entries based on the new data

This delete-and-recreate approach keeps the code simple and ensures the ledger is always consistent with the current invoice state. There is no partial-update path.

---

## Return Entries

Purchase returns and damage returns each create their own JournalEntry that reverses the original posting direction: the supplier's balance is reduced (we are returning goods so we owe less), and the account's balance is adjusted accordingly.

Damage receiving creates entries in the opposite direction — recording the cost of damage received from customers.

---

## Reading the Ledger

JournalEntry records are read-only through the API (`/api/journal-entries/`). They are never created or modified directly. The full audit trail of every financial event is available through this endpoint, filterable by branch and date range.
