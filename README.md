# Causal impact analysis

Estimate how attendance at a marketing event changes customer revenue trajectories using propensity score matching (PSM), difference-in-differences (DiD), and matched DiD.

**Status:** executable research starter with synthetic customer data, validation, diagnostics, and tests. No actual customer data or causal findings are included. The first version assumes a single event date, a balanced customer panel, and independently sampled customers.

## Run locally

Python 3.9–3.12 supported. From this repository:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
causal-study generate --output data/synthetic.csv
causal-study run --input data/synthetic.csv --config configs/study.json --output reports/demo
python -m pytest -q
```

After installation the study runs offline. GitHub operations and dependency installation need internet. The numerical stack currently uses NumPy 1.x for compatibility with the validated macOS/Python 3.9 environment. Dependencies from the validated Python 3.9 environment are pinned in `requirements-lock.txt`; use `pip install -r requirements-lock.txt` then `pip install --no-deps -e .` to reproduce that environment.

## Study design

- Treatment: customer attended the marketing event (`attended=1`). Comparison: eligible non-attendees (`attended=0`). Membership stays fixed across rows, including pre-event rows.
- Outcome: revenue for each customer-month, measured consistently for both groups.
- Matching features: historical average revenue, revenue trend, and residual revenue volatility. Use only information known **before the event or its anticipation window**.
- PSM: baseline logistic propensity scores, common support restriction, seeded greedy nearest-neighbor 1:1 matching without replacement within 0.2 SD of the logit score.
- PSM estimate: average post-event revenue difference among matched attendee/non-attendee pairs.
- DiD estimate: difference between groups in each customer's average post-event minus average pre-event revenue.
- Matched DiD: average within-pair difference in revenue changes; primary design candidate when selection into attendance relates to prior revenue patterns.
- Event study: month-specific DiD contrasts relative to the last pre-event month, for all customers and matched customers. Intervals are pointwise.

The simulated effect is **+150 revenue units per attendee per post-event month**. Three baseline revenue features are computed from eight historical months separate from the eight analysis months; the event starts in analysis month 4. Attendance selection and underlying trends are related, so unmatched DiD need not recover the true effect. Matching on observed features does not guarantee removal of all bias.

## Use your data

Prepare one row per customer-month and edit `configs/study.json` to map your column names. See [the data contract](docs/data-contract.md) and [study plan](docs/study-plan.md). Periods must be consecutive integer month indexes; customers must have every period. Missingness and duplicates fail validation rather than being silently dropped.

```sh
causal-study run --input data/customer_panel.csv --config configs/study.json --output reports/customer-study
```

The output folder contains `report.md`, `results.json` with hashes/configuration/package versions, customer scores, matched pairs, covariate balance, full and matched event-study CSVs, revenue-trajectory CSVs, and diagnostic PNGs. `examples/demo/` contains committed results generated only from synthetic data. Raw customer data and local reports are git-ignored.

## Read before interpreting

[Methodology](docs/methodology.md) covers identification, estimands, and inference limitations. Attendance is self-selected: matching cannot adjust for unmeasured purchase intent, account-manager outreach, or concurrent campaigns. PSM and matched DiD target retained attendees; matching attrition changes the population. Matched intervals are conditional on the selected pairs and do not include propensity/matching uncertainty. Clustered accounts or cluster-assigned attendance require a different inference design. Staggered events require a cohort-aware estimator and are outside this version.

A nonsignificant pretrend is not proof of parallel trends. Do not choose covariates, calipers, or analysis windows based on which produces a significant revenue lift.

## Optional continuous integration

A workflow template lives in `docs/ci/test.yml`. It is not active. To enable GitHub Actions, move it to `.github/workflows/test.yml` using a GitHub credential with workflow-write permission. The current connection has repository access but no workflow scope; all validation in this initial delivery is local.
