# Money Rules & Invariants

All transactions and fund movements in Vouch MUST strictly satisfy the following invariants and concurrency controls:

1. **Non-Negative Held Balance:**
   `held = total_donations - total_releases - total_refunds >= 0`
   The held balance can never drop below zero under any condition.

2. **Capped Release Amount:**
   `release_amount <= min(invoice_total, campaign_held_funds)`
   A release payout can never exceed the verified invoice amount or available held balance.

3. **Single Refund Guarantee:**
   `refund_count_per_donation <= 1`
   A donation capture can be refunded at most once. Enforce at the database level with `UNIQUE (donation_id)` on `refunds`.

4. **Guaranteed Idempotency:**
   Every outgoing external PayPal call must supply a deterministic idempotency key:
   - Orders/Captures/Refunds: `PayPal-Request-Id`
   - Payouts: `sender_batch_id` = `release_id` (enforced with `UNIQUE (release_id)` on `releases`).

5. **PostgreSQL Concurrency Controls:**
   - Always lock the campaign row (`SELECT ... FOR UPDATE`) before checking held balance or executing a money decision.
   - Prevent hash chain forks by acquiring `SELECT pg_advisory_xact_lock(1)` prior to appending any audit-log record.
   - Hash canonical JSON: `json.dumps(payload, sort_keys=True, separators=(',', ':'))`.

6. **Atomic State Mutation:**
   State mutation (ledger entry, donation status, release status) must be recorded in the same database transaction as the corresponding hash-chained audit log record.
