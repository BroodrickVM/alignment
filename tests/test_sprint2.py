"""Evidence updates must preserve provenance and analytical independence."""
from dataclasses import replace
import hashlib
from pathlib import Path
import pytest
from app.organizational.analyzer import analyze_csv
from app.organizational.evidence_validation import load_evidence_validation_matrix


def test_priority_reviews_are_limited_and_traceable():
    matrix = load_evidence_validation_matrix()
    expected = {'Q02': 'indirect_support', 'Q05': 'indirect_support',
                'Q07': 'partially_supported', 'Q08': 'indirect_support', 'Q09': 'indirect_support'}
    for item, status in expected.items():
        row = matrix.get_by_source_item(item)
        assert row.validation_status == row.recommended_status == status
        assert row.external_source_reference.startswith('https://')
        assert row.reviewed_on == '2026-10-23'
        assert 'automated' in row.reviewer and 'human review pending' in row.reviewer
        assert 'pending' in row.review_notes
        assert 'not instrument validation' in row.review_notes
    assert len(matrix.awaiting_external_review()) == 0
    assert not any(v.validation_status == 'validated' for v in matrix.validations)


def test_review_outcomes_must_agree():
    row = load_evidence_validation_matrix().get_by_source_item('Q07')
    with pytest.raises(ValueError, match='must match'):
        replace(row, recommended_status='validated')


def test_loading_reviews_does_not_change_analysis_or_rubric():
    path = Path('data/organizational/sample_q12_results.csv')
    rubric = Path('data/organizational/communication_rubric.csv')
    digest = hashlib.sha256(rubric.read_bytes()).digest()
    before = analyze_csv(path)
    load_evidence_validation_matrix()
    assert analyze_csv(path) == before
    assert hashlib.sha256(rubric.read_bytes()).digest() == digest


def test_dashboard_shows_current_scope_sources_and_limits():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file('app/organizational/dashboard.py').run(timeout=30)
    assert not app.exception
    text = '\n'.join(v.value for v in app.markdown)
    assert 'Initial research reviews recorded: 9 of 9. Initial reviews not yet recorded: 0.' in text
    assert 'All bundled external evidence remains pending' not in text
    assert 'https://pubmed.ncbi.nlm.nih.gov/21073566/' in text
    assert any('full-text checks remain pending' in v.value for v in app.caption)
