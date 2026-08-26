# Kopilotti Sales - product overview

Kopilotti Sales digitizes used-vehicle price negotiation. Natural-language interaction and the commercial decision are separated: an LLM may support the conversation, while a deterministic server-side policy engine makes the commercial decision within boundaries defined by the dealer.

## 1. Product purpose

Vehicle information and other purchasing steps can be online while price negotiation still requires a manual exchange. Kopilotti Sales turns that step into a controlled digital flow without transferring commercial authority away from the dealer.

The dealer defines the policy. The system applies it consistently. Cases outside the automated boundary are escalated for human review.

## 2. Customer journey

1. The customer opens a vehicle-specific negotiation flow.
2. The customer submits an offer.
3. The server loads the vehicle and the applicable commercial policy.
4. The policy engine returns `ACCEPT`, `COUNTER`, `REJECT`, or `ESCALATE`.
5. An accepted outcome may reserve the vehicle in the same database transaction as the decision, session transition, and audit event.
6. The customer continues in the dealer's own completion process, or a person handles an escalated case.

Kopilotti Sales limits its role to digital price negotiation and a controlled continuation path. The dealer remains responsible for its own transaction, payment, and handover processes.

## 3. Commercial boundaries

The dealer defines the commercial policy, including the price floor, target price, list price, round limits, and escalation rules. Kopilotti Sales applies the policy; it does not invent a pricing strategy.

A stale policy, missing vehicle, mismatch between the vehicle and policy, or policy conflict leads to escalation instead of a guessed decision. A person retains authority over exceptional cases.

## 4. Deterministic policy engine

The policy engine returns one of four states: accept, counter, reject, or escalate. The price floor bounds acceptance and counteroffers. The same validated input and policy produce the same commercial decision.

The commercial decision is made by a server-side policy engine isolated from the LLM. This boundary reduces the impact of LLM manipulation but is not presented as complete protection against every attack.

## 5. Reservation and double-booking prevention

The PostgreSQL model permits only one active reservation for the same dealer and vehicle through a database-enforced unique index. The accepted decision, reservation, session transition, and audit event share a transaction. If one step fails, the unit of work is rolled back.

Reservation mechanisms are implemented and tested but have not been production-verified in this review.

## 6. Persistence and application audit history

The published demo's production backend stores negotiation sessions durably in PostgreSQL. Session access is tenant-scoped at the application boundary, and tenant-relationship integrity is enforced by database constraints.

Persistence paths for purchase sessions, idempotency records, decisions, and audit events, together with the application audit history and append-only application path, are implemented and tested but remain outside this limited production-verification scope.

This describes application and database behavior in the repository. It does not claim an immutable external ledger, event-sourced architecture, or production verification.

## 7. DDN and verifiability

DDN (Deterministic Decision Network) preparation includes deterministic canonicalization, domain-separated hashes, a bounded submission adapter, and a safe local boundary for constructing and displaying a receipt link for a locally verified result.

A hash supports integrity checking, but a hash alone does not authenticate the receipt issuer.

Live DDN verification, signer authentication, quorum and trust profiles, public anchoring, and an independent offline verifier are roadmap items. The current implementation does not present them as complete production capabilities.

## 8. Security boundaries

- The LLM may support conversation but does not decide the price or commercial outcome.
- LLM isolation reduces the impact of manipulation but is not a promise of complete prompt-injection protection.
- A hash shows integrity-related consistency, not issuer identity or a trust chain.
- Roadmap capabilities are not prerequisites for the current decision flow.
- This overview does not authorize deployment, migrations, or access to production services.

## 9. Production-readiness status

Status: **limited production verification completed on 26 August 2026**.

The published demo's production backend was verified for durable PostgreSQL storage of negotiation sessions, tenant-scoped session access, and database-enforced integrity for tenant relationships. A fresh backup-and-restore test and the schema and readiness gates passed before release.

This is a limited production verification, not a general production-ready claim for the entire product. Reservation and audit mechanisms, the payment-capable transaction path, live DDN verification, and a production VIS connection retain the boundaries described below.

The publicly documented current scope and production boundaries are available in the [Kopilotti Sales public README](https://github.com/mikko-lab/kopilotti-sales-demo#current-scope).

## 10. Production-verified scope - 26 August 2026

<!-- sales-claim id="postgres-session-persistence" status="production-verified-scope" -->
- durable PostgreSQL storage of negotiation sessions in production
<!-- sales-claim id="tenant-scoped-negotiation-session-access" status="production-verified-scope" -->
- tenant-scoped negotiation-session access
<!-- sales-claim id="database-enforced-tenant-relationship-integrity" status="production-verified-scope" -->
- database-enforced integrity for tenant relationships
<!-- sales-claim id="readiness-schema-verification-gates" status="production-verified-scope" -->
- production schema and readiness gates
<!-- sales-claim id="verified-backup-restore" status="production-verified-scope" -->
- backup-and-restore test passed before release

The verification applies only to the limited production scope listed above.

## 11. Implemented and tested

<!-- sales-claim id="digital-price-negotiation" status="implemented-tested" -->
- digital price negotiation
<!-- sales-claim id="llm-isolated-commercial-decision" status="implemented-tested" -->
- a server-side commercial decision isolated from the LLM
<!-- sales-claim id="deterministic-decision-engine" status="implemented-tested" -->
- deterministic `ACCEPT`, `COUNTER`, `REJECT`, and `ESCALATE` logic
<!-- sales-claim id="dealer-commercial-boundaries-price-floor" status="implemented-tested" -->
- dealer-defined commercial boundaries and price-floor enforcement
<!-- sales-claim id="deterministic-canonicalization-hashes" status="implemented-tested" -->
- deterministic canonicalization and hash generation
<!-- sales-claim id="safe-local-receipt-link-boundary" status="implemented-tested" -->
- a safe local boundary for constructing and displaying a receipt link

## 12. Not production-verified

<!-- sales-claim id="atomic-vehicle-reservation" status="implemented-not-production-verified" -->
- atomic vehicle reservation
<!-- sales-claim id="database-enforced-double-booking-prevention" status="implemented-not-production-verified" -->
- database-enforced prevention of concurrent active reservations
<!-- sales-claim id="application-audit-history-hash-chain" status="implemented-not-production-verified" -->
- application audit history and hash chain
<!-- sales-claim id="append-only-audit-application-path" status="implemented-not-production-verified" -->
- append-only application path for audit events

Reservation and audit mechanisms are implemented and tested but have not been production-verified in this review.

## 13. Roadmap and research directions

<!-- sales-claim id="live-ddn-verification" status="roadmap-research" -->
- live DDN verification
<!-- sales-claim id="signer-authentication-trust-profiles" status="roadmap-research" -->
- signer authentication and pinned trust profiles
<!-- sales-claim id="quorum-public-anchoring" status="roadmap-research" -->
- quorum verification and public anchoring
<!-- sales-claim id="independent-offline-verifier" status="roadmap-research" -->
- an independent offline verifier
<!-- sales-claim id="byte-exact-runtime-replay" status="roadmap-research" -->
- byte-exact runtime replay
<!-- sales-claim id="signed-committed-decision-artifact" status="roadmap-research" -->
- a signed committed decision artifact
<!-- sales-claim id="proof-gated-execution" status="roadmap-research" -->
- proof-gated execution
<!-- sales-claim id="zero-knowledge-proofs" status="roadmap-research" -->
- zero-knowledge proofs
<!-- sales-claim id="approved-rto-rpo-targets" status="roadmap-research" -->
- approved RTO/RPO targets
<!-- sales-claim id="named-operational-owners-response-times" status="roadmap-research" -->
- named operational owners and response times

These are target or research directions, not current capabilities.

## 14. Demo and further information

- [Open the demo](https://app.kopilotti.online)
- [Suomenkielinen tuote-esittely](kopilotti-sales-overview-fi.md)
- [Suomenkielinen A4-PDF](kopilotti-sales-overview-fi.pdf)
- [Repository README](../README.md)
- [License](../LICENSE)

The demo illustrates the product flow. It does not prove production verification for capabilities marked as not production-verified.
