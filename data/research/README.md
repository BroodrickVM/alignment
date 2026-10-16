# Communication Evidence Matrix

`evidence_matrix.csv` is a reviewable record of verified sources and their
relationship to communication dimensions. It currently contains headers only:
no research has been included or verified. The loader does not establish that
a source exists or that a finding is accurate.

The matrix will support future decisions about AlignAgent's construct
definitions, observable behaviors, measurement guidance, and scoring rules.
It is not connected to the current rule-based scoring engine. Existing scores
remain provisional; this infrastructure adds no research-backed claims, RAG,
or language model integration.

## Research workflow and source register

Candidate source → Source register → Source verification → Evidence extraction
→ Evidence matrix → Rubric mapping → RAG ingestion.

`source_register.csv` is a staging area for sources supplied for review. It
currently contains headers only because no source list has been provided.
Registering a source does not automatically add it to `evidence_matrix.csv`
or establish that its findings support a communication dimension.

1. **Candidate source:** Identify a source to consider. Populate this register
   only with sources explicitly provided by the user; do not add guessed
   citations or independently selected research.
2. **Source register:** Record the supplied `source_id`, `authors`, `year`,
   `title`, `publication`, `source_type`, and `doi_or_url`. Use the literal
   `needs verification` for any field that cannot be confirmed, including
   peer-review status. Do not infer missing bibliographic information.
   `candidate_dimensions` records proposed links, not established support;
   separate multiple supplied dimension names with semicolons. Track review
   progress in `review_status` and verification details or gaps in `notes`.
3. **Source verification:** Check bibliographic identity, access to the source,
   and peer-review status against authoritative records. Document the checks
   in `notes`; unresolved fields remain `needs verification`. Bibliographic
   verification alone does not mean findings have been reviewed.
4. **Evidence extraction:** Review the actual findings, construct definitions,
   measurement methods, contexts, and limitations. Distinguish what the source
   reports from reviewer interpretation and proposed applications.
5. **Evidence matrix:** Only after source verification and findings review,
   manually add supported source-to-dimension rows to `evidence_matrix.csv`.
   Retain the register's `source_id` for traceability. There is no automatic
   promotion from the register.
6. **Rubric mapping:** In a future, separately authorized step, assess whether
   reviewed evidence supports particular rules and scoring anchors. The
   current rubric remains unchanged.
7. **RAG ingestion:** A later, separately authorized stage may ingest approved
   evidence after access permissions and quality checks. No RAG ingestion or
   LLM integration is implemented here.

## Adding research

1. Verify each source before inclusion. Check its identity, authors, year,
   title, publication, and DOI or stable URL against the original publication
   or an authoritative record, and inspect the source supporting the claim.
2. Assign a stable `source_id`. Record bibliographic metadata in `authors`,
   `year`, `title`, `source_type`, `publication`, and `doi_or_url`.
3. Define the relevant construct in `construct_definition`. Describe only
   behaviors and findings actually supported by the source in
   `supported_behavior`, `undesirable_behavior`, and `evidence_summary`.
   Distinguish source findings from reviewer interpretations in `notes`.
4. Record measurement guidance, applicable populations and contexts, and
   limitations in their corresponding columns. Describe `evidence_strength`
   qualitatively with a rationale; do not invent ratings or numeric evidence.
   Leave unsupported or unavailable details blank and explain gaps in `notes`.
5. Document who verified the source, when, and how in `notes`. Review the row
   for faithful interpretation and context before adding it. Unverified
   candidates should be kept outside this matrix.

Do not invent citations, papers, authors, findings, or measurements. Access to
metadata alone does not justify a claim about a study's findings.

## Linking evidence to dimensions

Use one source-to-dimension mapping per row in `communication_dimension`.
The current provisional dimensions are Clarity, Consistency, Audience alignment,
Purpose alignment, Actionability, and Tone appropriateness. When a verified
source supports more than one dimension, use separate rows with the same
`source_id`, and explain each link independently. A keyword match or a source's
existence alone does not establish support for a dimension or scoring rule.

## Loading and validation

`app/evaluation/evidence.py` provides `load_evidence_matrix`,
`validate_required_columns`, `filter_evidence_by_dimension`, and
`get_evidence_for_dimension`. Loading defaults to this CSV regardless of the
working directory. A headers-only file returns an empty list.

Files must be UTF-8 CSV (an optional BOM is accepted) with every required column.
Column order may vary and extra named columns are allowed. Missing, empty, or
duplicate headers, invalid encoding or CSV syntax, NUL characters, and rows
with an incorrect cell count raise `EvidenceValidationError`. Blank lines are
ignored and blank cells are retained. File access errors propagate unchanged.
These are structural checks, not bibliographic or scientific validation.

Dimension filtering trims surrounding whitespace and ignores case. Unknown
dimensions return no rows; blank requests raise `ValueError`. The filter does
not infer relationships between constructs or assess evidence strength.
