"""Run an auditable study from a JSON configuration and a panel CSV."""
import argparse
import hashlib
import json
from pathlib import Path
from importlib.metadata import version
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from .data import synthetic_panel, validate_panel, unit_summary
from .psm import match_units, balance_table
from .estimators import did, paired_effect, event_study


def run(input_path, config_path, output_path):
    cfg = json.loads(Path(config_path).read_text())
    panel, features = validate_panel(pd.read_csv(input_path), cfg)
    units = unit_summary(panel, cfg["treatment_period"], features)
    scored, pairs, matching = match_units(units, features, cfg["caliper_sd"], cfg["seed"])
    balance = balance_table(scored, pairs, features)
    balance["covariate"] = cfg["covariates"]
    estimates = {"did": did(units), "psm_post_att": paired_effect(units, pairs, "post"),
                 "matched_did": paired_effect(units, pairs, "change")}
    events = event_study(panel, cfg["treatment_period"])
    matched_events = event_study(panel, cfg["treatment_period"], pairs)
    warnings = ["Causal interpretation requires the documented identification assumptions.",
        "PSM and matched DiD target retained treated units, not necessarily all treated units.",
        "Matched confidence intervals condition on matches and omit propensity estimation uncertainty.",
        "Independent units are assumed. Cluster-assigned treatment requires cluster-level inference.",
        "Event-study intervals are pointwise. Insignificant pretrends do not establish parallel trends."]
    if matching["n_pairs"] < 30:
        warnings.append("Fewer than 30 matched pairs: small-sample inference may be unstable.")
    if (balance.smd_after.abs() > 0.1).any():
        warnings.append("Residual covariate imbalance: at least one absolute matched SMD exceeds 0.1.")
    if matching["treated_retained_fraction"] < 0.8:
        warnings.append("Less than 80% of treated units retained; examine changes in the target population.")
    if sum(panel.period.unique() < cfg["treatment_period"]) < 3:
        warnings.append("Fewer than three preperiods: limited evidence for pretreatment dynamics.")
    result = {"config": cfg, "sample": {"n_customers": len(units), "n_rows": len(panel),
              "pre_months": sorted(int(p) for p in panel.period.unique() if p < cfg["treatment_period"]),
              "post_months": sorted(int(p) for p in panel.period.unique() if p >= cfg["treatment_period"])},
              "matching": matching, "estimates": estimates, "warnings": warnings,
              "provenance": {"input_sha256": hashlib.sha256(Path(input_path).read_bytes()).hexdigest(),
              "config_sha256": hashlib.sha256(Path(config_path).read_bytes()).hexdigest(),
              "versions": {p: version(p) for p in ["causal-impact-analysis", "numpy", "pandas", "scipy", "scikit-learn", "statsmodels", "matplotlib"]}}}
    out = Path(output_path)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    scored.to_csv(out / "unit_scores.csv")
    pairs.to_csv(out / "matched_pairs.csv", index=False)
    balance.to_csv(out / "balance.csv", index=False)
    events.to_csv(out / "event_study.csv", index=False)
    matched_events.to_csv(out / "matched_event_study.csv", index=False)
    trajectory = panel.groupby(["period", "treated"]).outcome.agg(["mean", "count"]).reset_index()
    trajectory.to_csv(out / "revenue_trajectory.csv", index=False)
    matched_ids = list(pairs.treated_unit) + list(pairs.control_unit)
    matched_trajectory = panel[panel.unit.isin(matched_ids)].groupby(["period", "treated"]).outcome.mean().reset_index()
    matched_trajectory.to_csv(out / "matched_revenue_trajectory.csv", index=False)
    trajectory_fig, trajectory_axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, frame, title in [(trajectory_axes[0], trajectory.rename(columns={"mean": "outcome"}), "All customers"),
                              (trajectory_axes[1], matched_trajectory, "Matched customers")]:
        for group, label in [(0, "Non-attendees"), (1, "Attendees")]:
            subset = frame[frame.treated == group]
            ax.plot(subset.period, subset.outcome, marker="o", label=label)
        ax.axvline(cfg["treatment_period"] - .5, color="grey", linestyle="--", label="Event boundary")
        ax.set(xlabel="Month", ylabel="Mean customer revenue", title=title)
        ax.legend()
    trajectory_fig.tight_layout()
    trajectory_fig.savefig(out / "revenue_trajectory.png", dpi=160)
    plt.close(trajectory_fig)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for group, label in [(0, "Control"), (1, "Treated")]:
        axes[0].hist(scored.loc[scored.treated == group, "propensity"], bins=20, alpha=.55, label=label, density=True)
    axes[0].set(xlabel="Baseline propensity score", ylabel="Density", title="Overlap before matching")
    axes[0].legend()
    axes[1].scatter(balance.smd_before.abs(), balance.covariate, label="Before")
    axes[1].scatter(balance.smd_after.abs(), balance.covariate, label="After")
    axes[1].axvline(.1, color="grey", linestyle="--")
    axes[1].set(xlabel="Absolute standardized mean difference", title="Covariate balance")
    axes[1].legend()
    for ev, label, offset in [(events, "All units", -.04), (matched_events, "Matched", .04)]:
        axes[2].errorbar(ev.relative_period + offset, ev.estimate,
                        yerr=[ev.estimate - ev.ci_lower, ev.ci_upper - ev.estimate], fmt="o", label=label, capsize=2)
    axes[2].axhline(0, color="grey", linewidth=1)
    axes[2].axvline(0, color="grey", linestyle="--")
    axes[2].set(xlabel="Period relative to treatment", ylabel="Outcome contrast", title="Event study · pointwise 95% CI")
    axes[2].legend()
    fig.tight_layout()
    fig.savefig(out / "diagnostics.png", dpi=160)
    plt.close(fig)
    lines = ["# Marketing event attendance: customer revenue impact", "", "Outcome: customer revenue per period. Treatment: marketing-event attendance. Synthetic examples are demonstrations, not real findings.", "",
             "| Estimator | Estimate | 95% CI |", "|---|---:|---:|"]
    for label, e in estimates.items():
        lines.append(f"| {label} | {e['estimate']:.3f} | [{e['ci_lower']:.3f}, {e['ci_upper']:.3f}] |")
    lines += ["", f"Matched pairs: {matching['n_pairs']}; treated retention: {matching['treated_retained_fraction']:.1%}.",
              "", "![Revenue trajectories](revenue_trajectory.png)", "", "![Diagnostics](diagnostics.png)", "", "## Interpretation and limitations", ""]
    lines += [f"- {w}" for w in warnings]
    lines += ["", "## Covariate balance", "", "| Baseline feature | SMD before | SMD after |", "|---|---:|---:|"]
    lines += [f"| {row.covariate} | {row.smd_before:.3f} | {row.smd_after:.3f} |" for row in balance.itertuples()]
    lines += ["", "See docs/methodology.md for estimands, assumptions, and inference limits.", ""]
    (out / "report.md").write_text("\n".join(lines))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("generate", help="Write synthetic data with known monthly revenue effect +150")
    demo.add_argument("--output", default="data/synthetic.csv")
    demo.add_argument("--units", type=int, default=600)
    demo.add_argument("--seed", type=int, default=42)
    study = sub.add_parser("run", help="Run PSM, DiD, matched DiD, and diagnostics")
    study.add_argument("--input", required=True)
    study.add_argument("--config", default="configs/study.json")
    study.add_argument("--output", default="reports/study")
    args = parser.parse_args()
    if args.command == "generate":
        if args.units < 20:
            parser.error("Use at least 20 synthetic units.")
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        synthetic_panel(args.units, args.seed).to_csv(path, index=False)
        print(f"Wrote synthetic data to {path}; true monthly treatment effect = 150.0")
    else:
        result = run(args.input, args.config, args.output)
        print(json.dumps(result["estimates"], indent=2))
        print(f"Report: {Path(args.output) / 'report.md'}")


if __name__ == "__main__":
    main()
