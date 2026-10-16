# AlignAgent personal-use prototype

A local, rule-based minimum viable prototype for workplace communication review.
All six dimensions and scoring rules are **provisional, configurable, and not
scientifically validated**. There are no research citations, LLM calls, external
services, or organizational-agent features. Inputs are not saved by the program.

## Run

Use Python 3.9 or later. Open this standalone project folder:

```sh
cd /Users/velaphi/Documents/alignagent
python3 -m app.main
```

Enter a multiline message, finish with a blank line, then optionally supply the
audience and purpose. For a reproducible noninteractive example:

```sh
python3 -m app.main --text "Please review the proposal and send your feedback by Friday. Thanks." --audience "Project team" --purpose "Review the proposal"
```

The report includes each dimension, a 1–5 score, explanation, improvement
suggestion, overall summary, and a suggested revised communication template.
The revision preserves the original wording and adds editable placeholders; it
does not invent owners, deadlines, facts, or a semantic rewrite.

## Architecture

`main.py` collects input → `agents/personal_agent.py` orchestrates review →
`evaluation/rubric.py` runs configurable scoring functions →
`reports/report_generator.py` formats results and the revision template.

`rag/retriever.py` reserves a boundary for future retrieval-augmented generation
(RAG). Calling it currently raises `NotImplementedError`; it is not part of the
prototype execution path. `data/research/` is reserved for permitted, verified
research sources. No evidence has been loaded.

## Temporary rubric

| Dimension | Placeholder signals |
| --- | --- |
| Clarity | Sentence length, vague tokens, extremely short text. |
| Consistency | Selected opposing-term pairs; no logical reasoning. |
| Audience alignment | Neutral 3; audience suitability is not assessed. |
| Purpose alignment | Keyword overlap with author-provided purpose. |
| Actionability | Action terms, owner pronouns, timing terms. |
| Tone appropriateness | Courtesy words, flagged insults, uppercase emphasis. |

Missing context uses a neutral 3 and an explicit explanation. The overall score
is a weighted mean, not an empirical measure. Token rules can misread quotations,
negation, acronyms, context, and informational messages. A high score does not
establish quality or safety; author review remains necessary.

Configure dimensions in Python by passing `Dimension(name, scorer, weight)`
objects to `Rubric(dimensions=...)`, then pass the rubric to `PersonalAgent`.
Each scorer receives text and `CommunicationContext`, and returns an integer
score from 1 to 5, explanation, and suggestion. Weights must be finite and
positive. Dimensions can be replaced or removed without changing the agent or
report renderer. A future evidence matrix should determine the final rules.

## Tests

The runtime needs no third-party packages. Install pytest in a virtual
environment inside this folder if needed:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q -p no:cacheprovider
```

Or use an existing interpreter with pytest installed:

```sh
python3 -m pytest -q -p no:cacheprovider
```

## Next development steps

1. Curate verified sources and an evidence matrix linking dimensions to evidence.
2. Define scoring anchors, applicability rules, and explicit unknown scores.
3. Create consented examples and independent human labels; evaluate agreement
   and failure cases on held-out communications.
4. Replace placeholder rules with evidence-supported scoring and implement
   traceable retrieval only after source permissions and quality are reviewed.
5. Improve revisions while preserving author intent; evaluate before considering
   an LLM integration. Keep organizational-agent development outside this MVP.
