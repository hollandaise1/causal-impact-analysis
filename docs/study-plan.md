# Marketing-event revenue study plan

## Research question

What is the average effect of attending one marketing event on subsequent monthly customer revenue among comparable attendees?

## Decisions to lock before using real outcomes

1. Event ID/date, eligibility criteria, invitation and anticipation window, and confirmed attendance definition.
2. Customer identity, account hierarchy, and unit at which attendance selection/revenue shocks cluster.
3. Revenue definition/currency, refunds, exposure window, seasonality, and minimum reliable history.
4. Separate feature-building history, analysis preperiod, and postperiod; the demo uses eight historical months and four months on either side of the event.
5. Baseline revenue mean, slope, and residual volatility plus any necessary nonrevenue confounders (industry, tenure, account size, outreach, prior event attendance).
6. Primary estimand: monthly revenue effect among matched attendees; report the count and fraction retained.
7. Matching specification chosen from baseline overlap and balance only. Record exclusions and unresolved imbalance.
8. Diagnostics: trajectories, overlap, covariate balance, pre-event contrasts, and attendance-related attrition.
9. Prespecified robustness: alternate calipers/seeds/windows, baseline-outcome adjustment, negative-control outcomes/exposures where credible, and a sensitivity analysis for unmeasured confounding. These extensions are planning items, not implemented claims.

## Current implementation

Implemented: deterministic synthetic generator, strict panel validation, three baseline matching features, propensity estimation, support restriction, matching, balance checks, PSM/DiD/matched DiD, pointwise event studies, trajectory plots, JSON/CSV/Markdown export, input/config hashing, dependency capture, automated tests, and a GitHub Actions template (not activated).

Pending real-study work: ingestion from your revenue/event systems, business cohort rules, additional confounders, assignment-appropriate inference, sensitivity analyses, and an analyst-reviewed causal conclusion. Staggered events, cluster inference, missing panels, and production scheduling are not implemented.
