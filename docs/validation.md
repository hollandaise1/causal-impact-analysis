# Initial validation

Validated on macOS arm64 / Python 3.9.6 with the versions in `requirements-lock.txt`.

- `python -m pytest -q`: **21 passed**. Runtime numerical warnings are configured as test failures. Matplotlib's dependency emits 14 deprecation warnings; they do not affect numerical calculations.
- Generated 600 synthetic customers across eight analysis months, with three baseline revenue features computed from a separate historical window.
- End-to-end CLI produced JSON, CSV, Markdown, and PNG outputs. Diagnostic charts were visually inspected.
- True simulated monthly attendance effect: +150. Matched DiD: +146.194 (conditional paired 95% interval: 137.804 to 154.584); 177 pairs.
- PSM post-level contrast: +150.353. Unmatched DiD: +158.327. These are simulation results, not findings about real customers.
- Regression tests cover exact arithmetic, fixed matching under post-outcome changes, no reused controls, caliper/support enforcement, deterministic matching, balance improvement, null/effect simulation smoke checks, event-study normalization, invalid panels/configurations, insufficient overlap, and report artifacts.

NumPy is constrained to 1.x for the validated local environment after the initially resolved NumPy 2.0.2 build emitted matrix multiplication RuntimeWarnings. The final run has no numerical RuntimeWarnings.

The GitHub Actions template is provided under `docs/ci/`; it is not activated. Python 3.12 is a target in that template but was not run locally in this validation. The single seeded simulation is not a Monte Carlo coverage study.
