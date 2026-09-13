"""Unit-level changes preserve within-unit dependence across periods."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


def did(units):
    # Collapsing to one change per unit avoids treating repeated rows as independent.
    design = sm.add_constant(units[["treated"]], has_constant="add")
    fit = sm.OLS(units.change, design).fit(cov_type="HC3", use_t=True)
    ci = fit.conf_int().loc["treated"]
    return {"estimate": float(fit.params["treated"]), "std_error": float(fit.bse["treated"]),
            "ci_lower": float(ci.iloc[0]), "ci_upper": float(ci.iloc[1]),
            "p_value": float(fit.pvalues["treated"]), "n_units": len(units),
            "inference": "HC3 on one pre/post change per independent unit; t reference"}


def paired_effect(units, pairs, column):
    differences = (units.loc[pairs.treated_unit, column].to_numpy()
                   - units.loc[pairs.control_unit, column].to_numpy())
    n = len(differences)
    estimate = float(differences.mean())
    se = float(differences.std(ddof=1) / np.sqrt(n))
    critical = stats.t.ppf(0.975, n - 1)
    p = float(2 * stats.t.sf(abs(estimate / se), n - 1)) if se > 0 else (1.0 if estimate == 0 else 0.0)
    return {"estimate": estimate, "std_error": se, "ci_lower": float(estimate - critical * se),
            "ci_upper": float(estimate + critical * se), "p_value": p, "n_pairs": n,
            "inference": "Paired t interval conditional on selected matches; excludes propensity/match uncertainty"}


def event_study(panel, treatment_period, pairs=None):
    """Period-specific DiD relative to last preperiod; pointwise 95% intervals.

    Each regression has one observation per unit (or paired contrast per pair).
    These intervals are not simultaneous; no joint pretrend test is implied.
    """
    wide = panel.pivot(index="unit", columns="period", values="outcome")
    membership = panel.drop_duplicates("unit").set_index("unit").treated
    baseline = max(p for p in wide.columns if p < treatment_period)
    rows = []
    for period in sorted(wide.columns):
        if period == baseline:
            result = {"estimate": 0.0, "std_error": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "p_value": None}
        else:
            changes = pd.DataFrame({"treated": membership, "change": wide[period] - wide[baseline]})
            result = did(changes) if pairs is None else paired_effect(changes, pairs, "change")
        rows.append({"period": period, "relative_period": period - treatment_period,
                     "reference": period == baseline, **result})
    return pd.DataFrame(rows)
