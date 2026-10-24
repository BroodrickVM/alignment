# Tool 2 handoff

## Run locally

Python 3.9 or later. From the alignment repository:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app/organizational/dashboard.py --server.address 127.0.0.1 --server.port 8502
```

Open http://127.0.0.1:8502/. Restart the server after changes to imported modules
if an existing session retains old code. Local URLs work only on that computer.
No production hosting or Tool 1 integration is included in this handoff.

## Current capabilities

- Strict aggregate CSV validation and independent team/period analysis.
- Available-item equal-weight means, relative rankings and transparent ties.
- Configurable minimum-response threshold, default 5, applied to each supplied
  item; a failing item suppresses the whole team/period.
- Nine preliminary evidence-review records with sources, scope and limits.
  Five partial support, four indirect support; no validated mapping.
- Session-only manager notes separated by team/period/signal, explicit save,
  clear and text export. Suppression removes affected session notes.

## Key files

- `app/organizational/dashboard.py`: presentation and controls.
- `analyzer.py`, `models.py`, `report.py` in the same directory: inputs, analysis
  and report formatting; `workflow.py`: manager discussion workflow.
- `data/organizational/sample_q12_results.csv`: fictional demonstration inputs.
- `data/organizational/communication_rubric.csv`: operational mapping rubric.
- `data/organizational/evidence_validation_matrix.csv`: separate research review.
- `evidence_review_followup.md` in that data directory: current research limits.
- `tests/fixtures/scenarios/`: eleven deliberately designed test datasets;
  some contain invalid inputs intentionally and must be rejected.
- `output/validation/scenario_test_report.md`: scenario results at that sprint.

## Verify

```sh
.venv/bin/python -m pytest -q
```

Tests cover calculations, missing/invalid data, privacy, ties, evidence schema,
scenario dashboards, session isolation, note clearing and export boundaries.
The scenario report records its historical 268-test run; later workflow/polish
checks expand the suite. Consult the latest run rather than treating that number
as a current count.

## Limitations and next work

No psychometric validation of communication mappings or real-data field trial.
Human evidence review is outstanding; full-text access is unresolved for Q05,
Q09 and Q11. Cutoff ties can select all nine mapped signals. Session notes can be
lost; no database, authentication, organizational authorization or audit log is
implemented. Minimum size alone does not guarantee privacy; user-downloaded notes
are outside the session's deletion controls. Avoid personal data in notes.

A future Tool 1 handoff should pass only an explicitly selected context through
an agreed interface after its code and input/output contract are available.
This handoff accompanies the Tool 2 update prepared for the GitHub repository.
The local dashboard is not a public deployment. Review future changes before
publishing or deploying.
