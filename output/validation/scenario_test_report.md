# Tool 2 scenario test report

Run: 23 October 2026. **11 scenario cases passed; full suite: 268 passed.**

Scope: fixture CSVs through the real analyzer, actual Streamlit page exercised
with Streamlit AppTest, team/period and threshold interactions, and summary export
content. Fixtures are substituted in isolated test scripts; the bundled sample
file is unchanged. This is automated dashboard verification, not a visual review
of every scenario in a browser. Tests do not validate communication constructs,
real-world usefulness, or protection from every form of re-identification.

| Synthetic scenario | Expected behavior | Observed result | Final |
|---|---|---|---|
| Equal scores: 3.0 | All hierarchy areas tied; no unique item priority | Mean 3.0, four tied hierarchy areas, nine mapped cutoff-tied signals; explicit item tie notice in page and export | PASS |
| One low item: Q07=2, others=4 | Q07 first lower item; Teamwork lower hierarchy; preserve cutoff ties | Mean 46/12, Teamwork 3.5; Q07 first; nine mapped signals due to third-position ties | PASS |
| Missing Q01/Q11/Q12 | No imputation; Growth unavailable | Mean 3.0, Basic Needs 3.0, Growth unavailable; missing-item warnings and export caution | PASS |
| One count=4 | At default 5, suppress entire team; threshold 4 permits reporting | No diagnostic mean/item payload or page download; changing threshold to 4 shows report | PASS |
| All high: 4.5 | Relative interpretation without absolute classification | Mean 4.5, all hierarchy areas tied; item tie notice and non-causal export | PASS |
| All low: 1.5 | Relative interpretation without absolute classification | Mean 1.5, all hierarchy areas tied; item tie notice and non-causal export | PASS |
| Multiple teams/periods | Independent privacy and correct selected group | Mixed/P1 suppressed; Mixed/P2 mean 4; Other/P1 mean 2; selections and exports isolated | PASS |
| Score=6 | Reject full input | Validation error shown; no diagnostic/download | PASS |
| Count=0 | Reject full input | Validation error shown; no diagnostic/download | PASS |
| Required score blank | Reject full input | Row-level validation error shown; no diagnostic/download | PASS |
| Duplicate team/item/period | Reject full input | Duplicate error shown; no diagnostic/download | PASS |

## Finding and fix

The initial scenario run passed eight cases and failed three uniform-profile
cases against the expected clarity requirement. Hierarchy ties were already
explained, but item cards lacked a prominent warning that their top/bottom lists
can contain arbitrary representatives of tied scores. Added a shared item-tie
notice to the dashboard and text report. It explains item-ID ordering, the
three-card limit, and tie-inclusive communication selection. No analytical
ranking, score, mapping, evidence status, or privacy rule changed.

A subsequent test assertion was corrected to inspect the Streamlit information
panel containing the notice rather than only ordinary Markdown. The final run
passed all 268 tests; the machine-readable results are in
`scenario_test_results.xml` beside this report.

## Remaining product limitation

When most items tie at the third-lowest cutoff, the current analytical rule can
select all nine communication mappings, even when one item is distinctly lower.
The tests preserve and disclose this behavior. A future prioritization change
would require an explicit design decision; this test sprint does not change it.

## Reproduce

From the repository root:

```sh
.venv/bin/python -m pytest tests/test_scenarios.py -q
.venv/bin/python -m pytest -q --junitxml=output/validation/scenario_test_results.xml
```

Relevant files: `tests/test_scenarios.py`, `tests/fixtures/scenarios/*.csv`,
`app/organizational/report.py`, and `app/organizational/dashboard.py`.
