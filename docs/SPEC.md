# Vouch: Hold, Verify, Release
Build specification for the PayPal AI Hackathon. Prepared Nov 8, 2026. Submission closes Nov 12, 12:00 pm PT (Nov 13, 1:30 am IST). Built with Google Antigravity.

## 0. Read this first
About four days remain. Everything below is cut for one builder. Items marked Stretch are optional.
Sandbox only. Holding and paying out other people’s money is regulated. Vouch is an architecture a licensed platform could adopt, shown on PayPal sandbox with fictional people and institutions. Never use real donors, hospitals or schools.
PayPal’s built-in hold-and-release is probably not open to you. [Delayed disbursement](https://developer.paypal.com/platforms/checkout/delayed-disbursement) requires being an approved partner and onboarding sellers with the DELAY_FUNDS_DISBURSEMENT feature. The build therefore uses Mode A (platform ledger) in section 6, and delayed disbursement is documented as the production path. Test what your account allows on day 1.
Real versus simulated. Real: PayPal sandbox orders, captures, payouts and refunds, the AI audit, the audit log. Simulated: donors, payees, invoices, the price reference table and the legal structure of the platform.

## 1. The problem
Donors pay before they can know whether the money will reach the people it was promised to. Fraud is found afterward, if at all.
Problem statement. How can money be held, verified by AI against independent evidence, and released only to the verified payee for the verified purpose, with a public audit trail and automatic refunds if proof never arrives?

### Why it is real
- The BBB reports a surge in complaints about fake fundraisers, including on legitimate platforms, and says many victims never learn their donation did not reach the intended recipient.
- A U.S. Secret Service alert warns that donors should not assume money reaches the intended recipient on crowdfunding sites.
- The best-known protection today is claim-based and capped.

## 2. What already exists, and what is different
- **GoFundMe Giving Guarantee**: Refunds after misuse is confirmed, up to $1,000 per campaign. After the fact, claim-based, capped. Vouch verifies before release and refunds with no claim.
- **GoFundMe trust and safety**: Vets campaigns. Vouch audits each spend document at the moment of release.
- **Alice (alice.si)**: Pay-for-success with crypto escrow and human validators. Vouch uses ordinary PayPal rails and an AI evidence audit.
- **2026 research preprint**: Milestone-locked escrow smart contracts released on documentary evidence. Research prototype, on-chain, no payment-network integration.

### Honest positioning: Escrow-until-proof is not new. What Vouch adds:
1. Verification at release time, per spend document, not only at campaign creation.
2. Payee-first design: money goes to the hospital, school or vendor, never the organizer.
3. An explainable AI audit: deterministic checks plus a plain-language reason for every decision.
4. Cross-campaign reuse detection for invoices, photos and story text.
5. No-claim refunds: a deadline always resolves, and unproven money goes back automatically.
6. Mainstream rails (PayPal) with a documented production path, instead of crypto escrow.

## 3. Product definition
One line: Vouch holds donations, checks the proof of spending with AI and rules, pays only the verified payee, and refunds donors automatically when proof does not arrive.

### Roles
- **Donor**: Donate, view receipt and audit trail.
- **Organizer**: Create campaign, propose payee, upload evidence.
- **Payee**: Hospital, school, vendor (fictional). Receives money after verification.
- **Reviewer**: Human admin. Verify payees, decide flagged cases.
- **Vouch**: Platform and agents. Audit, release, refund, log.

### Principles
- Payee-first: the organizer never receives the money.
- Hold by default: nothing moves without a logged decision.
- The LLM extracts and explains; deterministic code decides money movement.
- Every decision comes with a reason a donor can read.
- Humans decide the edge cases.
- A deadline always resolves: release, or refund.

## 4. End-to-end flow
1. Organizer creates a campaign and registers a payee. Reviewer verifies payee. Campaign goes ACTIVE with proof deadline.
2. Donor pays via PayPal checkout. Funds captured into Vouch platform account. Ledger shows HELD.
3. Organizer uploads evidence (invoice/bill addressed to payee, plus optional photos).
4. Auditor extracts fields, runs checks, scores risk, writes explanation.
5. Decision engine chooses RELEASE, REQUEST_MORE, HUMAN_REVIEW, or REJECT.
6. RELEASE pays verified payee via Payouts for min(invoice total, held funds).
7. Deadline sweeper refunds all unreleased donations pro rata automatically.
8. Hash-chained audit log updated at every step, with public donor receipt.

## 5. Features (F1 - F12)
- **F1. Payee registry and verification**: Institutions allowed to receive money.
- **F2. Donation and hold**: PayPal Orders v2, captured into platform account, ledger entry HELD.
- **F3. Evidence intake**: PDF/JPG/PNG upload, SHA-256 and pHash computation.
- **F4. Evidence Auditor**: Vision LLM extracts fields; deterministic checks executed in code.
- **F5. Reuse detection**: Fingerprints of invoices, images (pHash), and stories (TF-IDF).
- **F6. Risk scoring and decision engine**: Combines hard checks and soft signals into 0-100 risk score.
- **F7. Release**: Payout to verified payee with batch ID = release ID.
- **F8. Deadline clock and automatic refund**: Sweeper refunds unproven donations pro rata.
- **F9. Public audit trail and donor receipt**: Append-only hash-chained log + public receipt.
- **F10. Reviewer queue**: AG Grid table of flagged cases with inline document viewer.
- **F11. Release Agent**: Autonomous agent managing case lifecycle with deterministic guardrails.
- **F12. Attack Lab**: Demo and test suite simulating scripted fraud patterns and injections.

## 6. PayPal integration (Mode A: platform ledger)
- Auth: `POST /v1/oauth2/token`
- Create donation: `POST /v2/checkout/orders` (intent CAPTURE)
- Capture: `POST /v2/checkout/orders/{id}/capture`
- Release: `POST /v1/payments/payouts`
- Refund: `POST /v2/payments/captures/{capture_id}/refund`
- Webhooks: verify signature with `/v1/notifications/verify-webhook-signature`

### Money Invariants
1. `held = donations - releases - refunds >= 0`
2. `release <= min(invoice_total, held)`
3. Donation refunded at most once
4. Every PayPal call is idempotent and logged
5. Ledger entry written in same DB transaction as intent to act
