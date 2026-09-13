import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from causal_impact.data import synthetic_panel, validate_panel, unit_summary
from causal_impact.psm import match_units, balance_table
from causal_impact.estimators import did, paired_effect, event_study
from causal_impact.cli import run

CFG = {"unit": "customer_id", "period": "month", "treated": "attended", "outcome": "revenue",
       "covariates": ["baseline_revenue", "revenue_trend", "revenue_volatility"],
       "treatment_period": 4, "caliper_sd": .2, "seed": 42}


def study(effect=150):
    p, f = validate_panel(synthetic_panel(effect=effect), CFG)
    u = unit_summary(p, 4, f)
    s, pairs, meta = match_units(u, f)
    return p, f, u, s, pairs, meta


def test_synthetic_effect_is_exact_and_features_do_not_leak():
    null = synthetic_panel(effect=0)
    treated = synthetic_panel(effect=150)
    pd.testing.assert_frame_equal(null.drop(columns="revenue"), treated.drop(columns="revenue"))
    expected = 150 * treated.attended * (treated.month >= 4)
    np.testing.assert_allclose(treated.revenue - null.revenue, expected, atol=1e-10)


def test_matching_constraints_and_balance():
    _, features, units, scored, pairs, meta = study()
    assert pairs.control_unit.is_unique and pairs.treated_unit.is_unique
    assert (scored.loc[pairs.treated_unit, "treated"] == 1).all()
    assert (scored.loc[pairs.control_unit, "treated"] == 0).all()
    assert scored.loc[list(pairs.treated_unit) + list(pairs.control_unit), "in_support"].all()
    assert pairs.logit_distance.max() <= meta["logit_caliper"] + 1e-12
    table = balance_table(scored, pairs, features)
    assert table.smd_after.abs().mean() < table.smd_before.abs().mean()
    _, again, _ = match_units(units, features)
    pd.testing.assert_frame_equal(pairs, again)


def test_post_outcome_changes_cannot_change_matches():
    panel, features, units, _, pairs, _ = study()
    panel.loc[panel.period >= 4, "outcome"] += panel.loc[panel.period >= 4, "unit"] * 100
    changed = unit_summary(panel, 4, features)
    _, again, _ = match_units(changed, features)
    pd.testing.assert_frame_equal(pairs, again)


def test_did_matches_hand_calculation():
    units = pd.DataFrame({"treated": [0, 0, 0, 1, 1, 1], "change": [1., 2., 3., 5., 6., 7.]})
    result = did(units)
    assert result["estimate"] == pytest.approx(4)
    assert result["std_error"] > 0
    assert result["ci_lower"] < 4 < result["ci_upper"]


def test_paired_did_matches_hand_calculation():
    units = pd.DataFrame({"change": [1., 2., 3., 5., 7., 9.]})
    pairs = pd.DataFrame({"treated_unit": [3, 4, 5], "control_unit": [0, 1, 2]})
    result = paired_effect(units, pairs, "change")
    assert result["estimate"] == pytest.approx(5)
    assert result["std_error"] == pytest.approx(1 / np.sqrt(3))


def test_matched_did_recovers_simulated_lift_and_null():
    # This is a deterministic smoke check, not a coverage claim over DGPs.
    for effect in (0, 150):
        _, _, units, _, pairs, _ = study(effect)
        assert abs(paired_effect(units, pairs, "change")["estimate"] - effect) < 25


def test_event_study_reference_and_shift():
    panel, _, _, _, pairs, _ = study()
    ev = event_study(panel, 4, pairs)
    reference = ev[ev.reference].iloc[0]
    assert reference.period == 3 and reference.estimate == 0
    assert ev.loc[ev.period >= 4, "estimate"].mean() > 100


@pytest.mark.parametrize("problem", ["duplicate", "missing", "infinite", "unbalanced", "time_varying_treatment", "time_varying_feature", "one_group", "non_numeric"])
def test_invalid_panels_are_rejected(problem):
    df = synthetic_panel()
    if problem == "duplicate":
        df = pd.concat([df, df.iloc[:1]])
    elif problem == "missing":
        df.loc[0, "revenue"] = np.nan
    elif problem == "infinite":
        df.loc[0, "revenue"] = np.inf
    elif problem == "unbalanced":
        df = df.iloc[1:]
    elif problem == "time_varying_treatment":
        df.loc[0, "attended"] = 1 - df.loc[0, "attended"]
    elif problem == "time_varying_feature":
        df.loc[0, "baseline_revenue"] += 1
    elif problem == "one_group":
        df.attended = 1
    elif problem == "non_numeric":
        df["revenue"] = "invalid"
    with pytest.raises(ValueError):
        validate_panel(df, CFG)


@pytest.mark.parametrize("updates", [{"treatment_period": -1}, {"treatment_period": 99}, {"caliper_sd": 0}, {"covariates": ["revenue"]}])
def test_invalid_config_rejected(updates):
    with pytest.raises(ValueError):
        validate_panel(synthetic_panel(), dict(CFG, **updates))


def test_no_overlap_is_rejected():
    units = pd.DataFrame({"treated": [0]*5 + [1]*5, "x": [-10]*5 + [10]*5})
    with pytest.raises(ValueError, match="matched pairs"):
        match_units(units, ["x"])


def test_end_to_end(tmp_path):
    csv, config, output = tmp_path / "data.csv", tmp_path / "config.json", tmp_path / "report"
    synthetic_panel().to_csv(csv, index=False)
    config.write_text(json.dumps(CFG))
    result = run(csv, config, output)
    expected = {"results.json", "report.md", "unit_scores.csv", "matched_pairs.csv", "balance.csv",
                "event_study.csv", "matched_event_study.csv", "diagnostics.png", "revenue_trajectory.png",
                "revenue_trajectory.csv", "matched_revenue_trajectory.csv"}
    assert expected == {p.name for p in output.iterdir()}
    assert json.loads((output / "results.json").read_text()) == result
    assert len(result["provenance"]["input_sha256"]) == 64
    assert (output / "diagnostics.png").stat().st_size > 10000
