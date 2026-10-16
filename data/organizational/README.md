# Tool 2 aggregate input

`sample_q12_results.csv` is entirely **SYNTHETIC**, with three fictional teams.
Scores were invented solely for software testing. There are no proprietary
Gallup benchmarks, questionnaire wording, or employee-level records.
`q12_schema.csv` documents the input columns; it is not survey input.

Run from the project root:

```sh
.venv/bin/python -m app.organizational.report data/organizational/sample_q12_results.csv
```

Python API: `analyze_csv(path)` returns a tuple of
`OrganizationDiagnosticReport` objects, each with `to_dict()`.
`analyze_results(records, mappings=...)` accepts validated `Q12Result` records
and a replacement sequence of `SignalMapping` objects. An empty mapping disables
communication hypotheses. Q03, Q10, and Q12 are unmapped by default.

Only the documented columns are accepted. Invalid headers, malformed records,
nonfinite/out-of-range scores, nonpositive/noninteger counts, invalid item IDs,
and duplicate team/item/period keys reject the input. Empty optional cells mean
not supplied. Missing Q12 items are reported; available items are averaged
without imputation. Blank lines are ignored by the CSV reader. Team and period
labels are trimmed; period labels are opaque and not interpreted as dates.
Each team/period is analyzed independently; periods are never pooled.

GrandMean is the unweighted mean of available item means. Hierarchy summaries
also use available items; a wholly missing hierarchy is unavailable. Top/bottom
three rankings use item IDs to break ties. Signals include mapped items at or
below the third-lowest score, including ties. With few items or identical scores,
strength and opportunity selections can overlap; they are relative descriptions.
Hierarchy strengths/opportunities include all groups tied for highest/lowest.

Percentiles are optional input metadata, never inferred or compared with a
benchmark. Mapping relationships are provisional associations, not measures of
causal influence. Team conversations and evidence review are required before
interpreting an opportunity as a communication issue. These aggregates cannot
establish individual experience, statistical uncertainty, or nonresponse bias.
Use anonymized team IDs and organization-approved minimum group sizes before
sharing; the tool validates aggregate structure but cannot certify anonymization
or suppress small groups. No LLM or RAG is involved. Tool 1 is independent.

## Local dashboard

Install the project dependencies and launch from the project root:

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/streamlit run app/organizational/dashboard.py --server.address 127.0.0.1
```

Open the local URL printed by Streamlit (normally http://localhost:8501).
Select a fictional team to update the complete dashboard. The dashboard reads
only the bundled synthetic CSV; it is a presentation layer over the existing
analyzer and report objects, with no uploads, external services, LLM, or RAG.
The hierarchy chart uses the full valid 1–5 response scale, with a labeled
baseline at 1. Missing hierarchy areas remain unavailable.

The existing privacy and methodology limitations apply. This demonstration
does not implement real-data access controls or a small-group suppression policy.
