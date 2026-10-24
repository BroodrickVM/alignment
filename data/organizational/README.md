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

### Sprint 1 reporting safeguards

The analyzer and CSV entry point accept `minimum_responses=5`; the dashboard
provides a minimum-responses control and the report CLI accepts
`--minimum-responses`. Choose an organization-approved threshold. This default is
a prototype policy, not a claim of a universal privacy standard or anonymity.
Any supplied item below the threshold suppresses the entire team/period before
scores, rankings, prompts or exports are constructed. Suppressed reports retain
only team/period identifiers and policy messages; no exact counts or item values.
Item counts are not summed or assumed to represent unique team respondents.

Malformed inputs, duplicate team/item/period records, missing required values,
non-finite/out-of-range scores, invalid counts, invalid percentiles and unsupported
columns reject the full input. Missing item rows remain explicit gaps: no
imputation, available-item equal weighting, and a comparability caution. Varying
counts produce a data-quality note. No cross-team comparison is introduced.

The evidence matrix now separates `validation_status` from legacy provisional
support judgments and includes relationship, allowed/prohibited language,
external reference, reviewer and review date fields. Status vocabulary: `pending`,
`validated`, `partially_supported`, `indirect_support`, `insufficient_evidence`.
These are review outcomes, not confidence scores. All nine records remain
`pending`; no new external research was reviewed. Pending external support cannot
be promoted to a completed status. Completed statuses require recorded external
provenance, reviewer and date; those fields support audit, not automatic proof.
Reviewers must evaluate claim-specific support before changing a status. This
matrix never changes the analytical rankings or operational mappings.

Review outcome meanings: `validated` means reviewed sources directly support the
stated non-causal mapping; `partially_supported` means only part of the stated
claim is supported; `indirect_support` means support is contextual rather than
direct; `insufficient_evidence` means reviewed material is inadequate. `pending`
means review is incomplete, not that evidence is absent. No bundled record has
been assigned a completed outcome in Sprint 1.

### Sprint 2 preliminary review update

The Sprint 1 statement that all nine reviews were pending is historical.
Five targeted automated desk reviews are now recorded: Q07 is partially supported;
Q02/Q05/Q08/Q09 have indirect support. Four others remain pending. No mapping or
instrument is classified validated. See [review scope, sources and remaining
gaps](evidence_review_sprint2.md). Human review and the noted full-text appraisals
remain pending. Current `validation_status` and matching `recommended_status`
are review outcomes; historical provisional overall/Gallup support labels are
retained without changing operational mappings or analysis.

### Current follow-up

All nine preliminary reviews are now recorded: five partial and four indirect.
The earlier five-reviewed/four-pending statement describes the first pass.
`review_scope` distinguishes abstract-only from targeted full-text sections;
`full_text_status` separately preserves three unresolved access checks. None of
these outcomes validates AlignAgent. See [current review](evidence_review_followup.md)
for sources, inspected sections, access limits and remaining human review.

### Manager discussion workflow

Eligible team/period reports now include a signal selector, source-grounded guide,
separate employee observations and manager reflections, hypothesis assessment,
and a manager-selected next step (investigate, agree on action, or no action).
Responsible role and follow-up timing are optional. These entries never change
scores, evidence statuses, or analytical conclusions.

Notes require an explicit **Save notes in this session** action. Each team,
period and signal has separate saved notes. Unsaved form edits are excluded from
the discussion download. Notes live only in Streamlit session state, not a file
or database, and may be lost on disconnection, reload or restart. The user can
explicitly download a text guide/summary or clear that signal's saved notes.
Use non-identifying summaries. Increasing the reporting threshold removes saved
and widget notes for every newly suppressed team/period in that session; lowering
the threshold does not restore removed notes. Previously downloaded copies remain
under the user's control. Suppressed results and teams with no selected mapped
signals have no discussion form or discussion download.

Validation: `tests/test_workflow.py` checks export separation, blocked contexts,
signal/team/session isolation, period-specific removal, save/restore/clear and
privacy-threshold changes. Full suite after implementation: 271 passed.
