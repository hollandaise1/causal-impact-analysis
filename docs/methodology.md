# Estimands and assumptions

## Propensity score matching

Fit an L2-regularized logistic regression (`C=1`, standardized predictors) on one baseline record per customer. No post-event values enter matching. Restrict to the intersection of observed score ranges, then greedily match randomly ordered attendees (seeded) to the closest remaining non-attendee on logit propensity within the configured caliper. This is without replacement, and is not a globally optimal assignment. Ties are deterministic for the sorted input. Score overlap is a diagnostic, not proof of positivity.

The PSM contrast is the mean matched post-event revenue difference. Interpreting it as a treatment effect requires conditional exchangeability given included baseline features, positivity, consistency, and no interference. Revenue-only features may miss strong attendance confounders. The target is the retained attendee population; report retention and characteristics of unmatched attendees.

Standardized mean differences use the full unmatched pooled SD as a fixed denominator before and after matching. Absolute SMD below 0.1 is a heuristic rather than an identification test.

## Common-event DiD

For customer i compute change_i = mean(post revenue_i) - mean(pre revenue_i). Regress this change on an intercept and attendance membership. This equals the canonical difference in group changes with equal customer weights for the balanced common-event panel. HC3 standard errors are computed across customer changes, using a t reference distribution. Serial dependence within customers does not create pseudo-replication because each customer contributes one observation. Dependence across customers is not accounted for.

Matched DiD computes change_attendee - change_nonattendee within each selected pair, then averages these differences. Its 95% interval uses the pair-difference standard error and Student t with pairs minus one degrees of freedom. The PSM post-level contrast uses the same conditional paired inference. These intervals omit model fitting and match-selection uncertainty; they should be treated as exploratory conditional summaries, not full design-based inference. A naive ordinary bootstrap for nearest-neighbor matching is not implemented.

DiD identification requires parallel untreated revenue trends for the target population, no anticipation, no spillovers, and a stable outcome definition/composition. Matched DiD requires credible parallel trends after the matching design. PSM alone instead needs exchangeability of outcome levels given observed covariates. These are different assumptions.

## Dynamic diagnostics

For each month compute revenue minus the same customer's last pre-event revenue, then estimate the attendee/non-attendee contrast (or paired contrast). The reference month's contrast is zero by normalization. The other confidence intervals are pointwise; they are correlated across periods, and do not constitute a joint pretrend test or simultaneous confidence band. No automated pass/fail decision is made from pretrend p-values.

The provided design is not a staggered-adoption TWFE estimator. For different attendance dates or multiple events, use an appropriate cohort-time ATT design and revisit controls, anticipation, and aggregation before extending the code.

## References

- Rosenbaum and Rubin (1983), propensity scores: https://doi.org/10.1093/biomet/70.1.41
- Callaway and Sant'Anna (2021), multi-period and staggered DiD: https://doi.org/10.1016/j.jeconom.2020.12.001
- Statsmodels robust covariance implementation: https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_robustcov_results.html

## Next steps for a real study

Lock the analysis plan before examining post-event effects. Validate event eligibility, invitations, attendance timestamps, revenue measurement, concurrent campaigns, customer relationships, and attrition. Add relevant baseline business confounders and robustness designs based on causal reasoning. Consider overlap/balance across the full baseline distribution, sensitivity to unmeasured confounding, alternate prespecified windows, and inference suited to the sampling and treatment-assignment process.
