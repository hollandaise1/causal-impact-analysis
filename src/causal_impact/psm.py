"""Baseline logistic propensity model and greedy 1:1 caliper matching."""
import warnings
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def match_units(units, features, caliper_sd=0.2, seed=42):
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=3000, random_state=seed))
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(units[features], units.treated)
    scored = units.copy()
    scored["propensity"] = model.predict_proba(units[features])[:, 1]
    logits = model.decision_function(units[features])
    scored["logit"] = logits
    caliper = float(caliper_sd * np.std(logits, ddof=1))
    treated = scored[scored.treated == 1]
    control = scored[scored.treated == 0]
    low = max(treated.propensity.min(), control.propensity.min())
    high = min(treated.propensity.max(), control.propensity.max())
    scored["in_support"] = scored.propensity.between(low, high)
    eligible_t = scored[(scored.treated == 1) & scored.in_support]
    eligible_c = scored[(scored.treated == 0) & scored.in_support]
    available = list(eligible_c.index)
    pairs = []
    rng = np.random.default_rng(seed)
    # Seeded order is reproducible; greedy matches do depend on this order.
    for position in rng.permutation(len(eligible_t)):
        tid = eligible_t.index[position]
        if not available:
            break
        distances = np.abs(scored.loc[available, "logit"].to_numpy() - scored.loc[tid, "logit"])
        best = int(np.argmin(distances))
        if distances[best] <= caliper + 1e-12:
            cid = available.pop(best)
            pairs.append({"pair_id": len(pairs), "treated_unit": tid, "control_unit": cid,
                          "logit_distance": float(distances[best])})
    if len(pairs) < 3:
        raise ValueError("Fewer than three matched pairs. Revisit overlap/design; do not tune for significance.")
    return scored, pd.DataFrame(pairs), {"support_lower": float(low), "support_upper": float(high),
        "logit_caliper": caliper, "n_treated": len(treated), "n_control": len(control),
        "n_pairs": len(pairs), "treated_retained_fraction": len(pairs) / len(treated),
        "n_outside_support": int((~scored.in_support).sum())}


def balance_table(scored, pairs, features):
    rows = []
    for feature in features:
        t = scored.loc[scored.treated == 1, feature]
        c = scored.loc[scored.treated == 0, feature]
        denom = np.sqrt((t.var(ddof=1) + c.var(ddof=1)) / 2)
        before = t.mean() - c.mean()
        after = scored.loc[pairs.treated_unit, feature].mean() - scored.loc[pairs.control_unit, feature].mean()
        def standardize(value):
            return float(value / denom) if denom > 0 else (0.0 if value == 0 else float("inf"))
        rows.append({"covariate": feature, "smd_before": standardize(before), "smd_after": standardize(after)})
    return pd.DataFrame(rows)
