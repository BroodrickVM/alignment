"""Distinguish preliminary outcomes from unresolved access and validation."""
from collections import Counter
from dataclasses import replace
import pytest
from app.organizational.evidence_validation import load_evidence_validation_matrix


def test_all_reviews_have_scope_and_unresolved_access_is_explicit():
    matrix = load_evidence_validation_matrix()
    assert Counter(v.validation_status for v in matrix.validations) == {
        'partially_supported': 5, 'indirect_support': 4}
    assert {v.source_item for v in matrix.validations if v.full_text_status == 'access_pending'} == {'Q05', 'Q09', 'Q11'}
    assert len(matrix.awaiting_external_review()) == 0
    assert all('Human review pending' in v.review_notes for v in matrix.validations)
    assert all(v.recommended_status == v.validation_status for v in matrix.validations)


@pytest.mark.parametrize('scope,status', [
    ('full_review', 'targeted_sections_checked'),
    ('abstract_only', 'complete'),
    ('abstract_only', 'targeted_sections_checked'),
    ('targeted_full_text_sections', 'access_pending'),
])
def test_invalid_or_inconsistent_scope_is_rejected(scope, status):
    row = load_evidence_validation_matrix().validations[0]
    with pytest.raises(ValueError):
        replace(row, review_scope=scope, full_text_status=status)


def test_new_claims_remain_limited_to_discussion():
    matrix = load_evidence_validation_matrix()
    for item in ('Q01', 'Q04', 'Q06', 'Q11'):
        row = matrix.get_by_source_item(item)
        assert row.validation_status == 'partially_supported'
        assert row.allowed_language.startswith('Ask')
        assert 'AlignAgent is independently validated' in row.prohibited_language
