"""Synthetic panel generation and strict study design validation."""
import numpy as np
import pandas as pd


def synthetic_panel(n_units=600, seed=42, effect=150.0):
    """Revenue history (-8..-1) precedes study periods (0..7), event at 4.

    Three matching features are measured from the separate history window.
    Attendance selection depends on these features. Revenue trends differ
    across customers, so the unadjusted DiD can be confounded.
    """
    rng = np.random.default_rng(seed)
    level = rng.lognormal(np.log(1000), 0.35, n_units)
    slope = rng.normal(10, 8, n_units)
    noise = rng.uniform(20, 70, n_units)
    times = np.arange(-8, 0)
    history = level[:, None] + slope[:, None] * times + rng.normal(size=(n_units, 8)) * noise[:, None]
    average = history.mean(axis=1)
    centered_time = times - times.mean()
    trend = history @ centered_time / (centered_time @ centered_time)
    residuals = history - average[:, None] - trend[:, None] * centered_time
    volatility = np.sqrt((residuals ** 2).sum(axis=1) / 6)
    z = lambda x: (x - x.mean()) / x.std()
    propensity = 1 / (1 + np.exp(-(-0.6 + 0.5 * z(average) + 0.6 * z(trend) - 0.3 * z(volatility))))
    attended = rng.binomial(1, propensity)
    frames = []
    for period in range(8):
        frames.append(pd.DataFrame({
            "customer_id": np.arange(n_units), "month": period, "attended": attended,
            "baseline_revenue": average, "revenue_trend": trend, "revenue_volatility": volatility,
            "revenue": level + slope * period + 20 * np.sin(period / 2)
                       + effect * attended * (period >= 4) + rng.normal(size=n_units) * noise,
        }))
    return pd.concat(frames, ignore_index=True)


def validate_panel(df, cfg):
    """Normalize names; fail on missingness, imbalance, or invalid assignment.

    treated is EVER-treated membership, not time-varying treatment exposure.
    Numeric covariates must be fixed, explicitly selected pretreatment features.
    """
    roles = [cfg[k] for k in ("unit", "period", "treated", "outcome")]
    covs = cfg["covariates"]
    if not covs or len(set(roles + covs)) != len(roles + covs):
        raise ValueError("Use distinct role columns and at least one distinct covariate.")
    required = roles + covs
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    panel = df[required].copy()
    if panel.empty or panel.isna().any().any():
        raise ValueError("Panel must be nonempty with no missing required values.")
    names = dict(zip(roles, ["unit", "period", "treated", "outcome"]))
    names.update({c: f"x{i}" for i, c in enumerate(covs)})
    panel = panel.rename(columns=names)
    features = [f"x{i}" for i in range(len(covs))]
    numeric = ["period", "treated", "outcome"] + features
    try:
        panel[numeric] = panel[numeric].apply(pd.to_numeric, errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError("Period, treatment, outcome, and covariates must be numeric.") from exc
    if not np.isfinite(panel[numeric].to_numpy(dtype=float)).all():
        raise ValueError("All numeric values must be finite.")
    if panel.duplicated(["unit", "period"]).any():
        raise ValueError("Duplicate unit-period rows.")
    if set(panel.treated.unique()) != {0, 1}:
        raise ValueError("treated must contain both 0 and 1 groups.")
    if (panel.groupby("unit")[["treated"] + features].nunique() != 1).any().any():
        raise ValueError("Treatment membership and baseline covariates must be fixed within unit.")
    periods = sorted(panel.period.unique())
    if (panel.groupby("unit").size() != len(periods)).any():
        raise ValueError("A balanced panel is required; every unit must have every period.")
    if any(p != int(p) for p in periods) or any(b - a != 1 for a, b in zip(periods, periods[1:])):
        raise ValueError("Use consecutive integer month indexes; convert calendar dates upstream.")
    start = cfg["treatment_period"]
    if not np.isfinite(start) or start not in periods or not any(p < start for p in periods) or not any(p >= start for p in periods):
        raise ValueError("Treatment date must leave both pre and post observations.")
    sizes = panel.drop_duplicates("unit").groupby("treated").size()
    if sizes.min() < 3:
        raise ValueError("At least three units per treatment group are required.")
    if not np.isfinite(cfg["caliper_sd"]) or cfg["caliper_sd"] <= 0:
        raise ValueError("caliper_sd must be finite and positive.")
    return panel.sort_values(["unit", "period"]).reset_index(drop=True), features


def unit_summary(panel, treatment_period, features):
    base = panel.drop_duplicates("unit").set_index("unit")[["treated"] + features]
    base["pre"] = panel.loc[panel.period < treatment_period].groupby("unit").outcome.mean()
    base["post"] = panel.loc[panel.period >= treatment_period].groupby("unit").outcome.mean()
    base["change"] = base.post - base.pre
    return base
