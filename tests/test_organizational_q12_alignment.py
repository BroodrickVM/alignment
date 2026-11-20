"""Documentation and presentation retain the authoritative mapping boundaries."""
from copy import deepcopy
from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.organizational.action_plans import action_plans_for_report, load_action_plans
from app.organizational.analyzer import analyze_csv
from app.organizational.dashboard import SAMPLE_PATH, diagnostic_summary_text
from app.organizational.evidence_validation import load_evidence_validation_matrix
from app.organizational.mappings import DEFAULT_MAPPINGS
from app.organizational.rubric import load_rubric

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / 'docs/TOOL2_Q12_ALIGNMENT.md'
MAPPED = {'Q01', 'Q02', 'Q04', 'Q05', 'Q06', 'Q07', 'Q08', 'Q09', 'Q11'}


def test_alignment_table_matches_rubric_evidence_and_engine():
    text = DOCUMENT.read_text()
    rows = [line.split(' | ') for line in text.splitlines() if line.startswith('| Q') and line.split(' | ')[0].removeprefix('| ') in MAPPED]
    assert len(rows) == 9
    assert {row[0].removeprefix('| ') for row in rows} == MAPPED
    rubric = load_rubric()
    matrix = load_evidence_validation_matrix()
    assert {m.item_id for m in DEFAULT_MAPPINGS} == MAPPED
    for row in rows:
        item = row[0].removeprefix('| ')
        dimension = rubric.get_by_item(item)
        evidence = matrix.get_by_source_item(item)
        assert row[1] == dimension.dimension_name == evidence.dimension_name
        assert row[2] == dimension.relationship_type == evidence.relationship_type
        assert evidence.validation_status.replace('_', ' ') in row[6]
        assert evidence.source_reference in text
        assert evidence.external_source_reference in text
        assert evidence.allowed_language in text
        assert f'### {item} → {dimension.dimension_name}' in text
    assert rubric.unmapped_items() == ('Q03', 'Q10', 'Q12')
    assert 'Why Q03, Q10, and Q12 are not currently mapped' in text
    assert 'not a claim that these topics have no relationship with communication in reality' in text


def test_document_explains_noncausal_labels_and_research_limits():
    text = DOCUMENT.read_text()
    for phrase in (
        'not statistical confidence', 'not a validated causal effect',
        'does **not** mean direct empirical validation',
        'No causal inference is performed.',
        'They do not establish causes.',
        'Q07 does not directly measure voice behavior, psychological safety, or actual follow-through',
        'Coworker commitment to quality is not itself a measure of coordination or handoff quality',
        'not the full mapping', 'related construct, not the Q12 item itself',
        'Human review pending', 'six selected Q12 questions',
    ):
        assert phrase in text
    for claim in ('will increase engagement', 'expected score increase', 'scientifically proven to improve'):
        assert claim not in text.lower()


def test_dashboard_explains_alignment_without_changing_selected_reports():
    reports = analyze_csv(SAMPLE_PATH)
    before = deepcopy([report.to_dict() for report in reports])
    library = load_action_plans()
    actions = [action_plans_for_report(r, library) for r in reports]
    app = AppTest.from_file(str(ROOT / 'app/organizational/dashboard.py')).run(timeout=30)
    assert not app.exception
    explanation = next(e for e in app.expander if e.label == 'Why these Q12-style items?')
    text = '\n'.join(m.value for m in explanation.markdown)
    assert 'Only nine selected Q12-style items' in text
    assert 'investigation hypotheses, not causal diagnoses' in text
    assert 'conceptual relationship, not statistical confidence scores' in text
    assert 'Q03, Q10, and Q12 remain intentionally unmapped' in text
    assert 'does not mean direct empirical validation' in text
    assert 'docs/TOOL2_Q12_ALIGNMENT.md' in '\n'.join(c.value for c in explanation.caption)
    evidence = next(e for e in app.expander if e.label == 'Evidence validation status')
    evidence_text = '\n'.join(m.value for m in evidence.markdown)
    assert 'part of the discussion framing, not the full mapping' in evidence_text
    assert 'related construct, not the Q12 item itself' in evidence_text
    for report in reports:
        diagnostic_summary_text(report)
    assert [r.to_dict() for r in reports] == before
    assert [action_plans_for_report(r, library) for r in reports] == actions
