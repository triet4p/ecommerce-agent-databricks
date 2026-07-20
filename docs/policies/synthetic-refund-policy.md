# Synthetic Ecommerce Refund Policy

> Training/demo policy only. This is not an Olist policy, legal advice, or a
> statement of any real merchant's obligations.

## Policy metadata

- Policy ID: `SYNTH-REFUND-2026-01`
- Version: `1.0.0`
- Effective date: `2026-07-17`
- Time basis: calendar days
- Scope: synthetic transactions used by the `ecommerce_agent` learning project
- Decision states: `eligible`, `ineligible`, `manual_review`

The explicit `claim_date` is the policy reference date. The explicit
`evaluation_date` represents the date on which the decision is evaluated; the
function must not read the system clock. This keeps historical evaluation and
tests deterministic.

## Policy matrix

| Claim type | Required order state | Reference date | Window or wait | Evidence | Additional conditions |
|---|---|---|---:|---|---|
| `damaged` | `delivered` | `delivered_date` | 30 days, inclusive | Required | Final-sale and opened-item flags do not remove seller-fault protection. |
| `wrong_item` | `delivered` | `delivered_date` | 30 days, inclusive | Required | Final-sale and opened-item flags do not remove seller-fault protection. |
| `missing_item` | `delivered` | `delivered_date` | 14 days, inclusive | Required | Applies when part of a delivered order is missing. |
| `remorse` | `delivered` | `delivered_date` | 7 days, inclusive | Not required | Item must be unopened and must not be marked final sale. |
| `not_delivered` | `approved`, `processing`, `invoiced`, or `shipped` | `estimated_delivery_date` | Eligible beginning 7 days after the estimate | Not required | A delivered or canceled state conflicts with this claim type. |
| `seller_canceled` | `canceled` | `claim_date` | Immediate | Not required | The canceled state is required. |

Day zero is the reference date. Therefore a delivery on `2026-07-01` remains
inside a 7-day inclusive window through `2026-07-08`. A `not_delivered` claim
with an estimate of `2026-07-01` becomes eligible on `2026-07-08`.

## Validation and ambiguity rules

Return `manual_review` rather than `ineligible` when the function cannot make a
policy-backed decision, including:

- unknown claim type or order state;
- missing reference date required by the selected claim type;
- missing evidence/opened/final-sale discriminator values;
- `claim_date` after `evaluation_date`;
- `claim_date` before this policy's effective date;
- a delivered date after the claim date;
- a delivered date after `evaluation_date` (a future estimated delivery date is
  valid and means that the delivery deadline has not yet been reached);
- an order state that conflicts with the selected claim type.

Return `ineligible` only when valid, sufficient inputs are present and a stated
policy condition fails, such as an expired window, missing required evidence,
an opened remorse return, a final-sale remorse return, or an active delivery
grace period.

## Output contract

The governed function returns `MAP<STRING, STRING>` with these stable keys:

- `decision`
- `decision_code`
- `policy_id`
- `policy_version`
- `claim_type`
- `explanation`
- `reference_date`
- `deadline_date`
- `days_from_reference`

Consumers must branch on `decision`, not parse `explanation`. The explanation is
for auditing and customer-support context; it is not a substitute for the
stable decision code.

## Change control

Changing a window, wait period, supported claim type, required input, or outcome
semantics requires a new policy version and corresponding boundary tests. Do
not silently edit this document to mimic a real marketplace policy.
