"""Separate evidence-review matrix validation and query behavior."""
import csv
from dataclasses import asdict, replace
import io

import pytest

from app.organizational.evidence_validation import (
    DEFAULT_MATRIX_PATH, REQUIRED_COLUMNS, EvidenceValidation, EvidenceValidationMatrix,
    counts_by_recommended_status, dimensions_awaiting_external_review,
    dimensions_with_limited_support, get_validation_by_dimension_id,
    get_validation_by_source_item, load_evidence_validation_matrix,
    validate_required_columns, validate_support_level,
)
from app.organizational.rubric import DEFAULT_RUBRIC_PATH, load_rubric


def stream_for(rows, columns=REQUIRED_COLUMNS):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    stream.seek(0)
    return stream


@pytest.fixture
def row():
    return asdict(load_evidence_validation_matrix().validations[0])


def test_all_nine_dimensions_and_exact_initial_judgments():
    matrix = load_evidence_validation_matrix()
    expected = (
        ('expectations_and_direction', 'Q01', 'strong', 'gallup_supported_external_review_pending'),
        ('information_and_resource_access', 'Q02', 'moderate', 'partial_support_external_review_pending'),
        ('recognition_communication', 'Q04', 'strong', 'gallup_supported_external_review_pending'),
        ('relational_support', 'Q05', 'moderate', 'indirect_support_external_review_pending'),
        ('developmental_communication', 'Q06', 'strong', 'gallup_supported_external_review_pending'),
        ('employee_voice', 'Q07', 'moderate', 'partial_support_external_review_pending'),
        ('purpose_alignment', 'Q08', 'moderate', 'partial_support_external_review_pending'),
        ('team_norms_and_coordination', 'Q09', 'limited', 'limited_support_external_review_required'),
        ('progress_feedback', 'Q11', 'strong', 'gallup_supported_external_review_pending'),
    )
    assert len(matrix.validations) == 9
    assert [(v.dimension_id, v.source_item, v.gallup_support_level, v.recommended_status) for v in matrix.validations] == list(expected)
    for record, dimension in zip(matrix.validations, load_rubric().dimensions):
        assert record.dimension_name == dimension.dimension_name
        assert record.external_research_support == 'not_yet_reviewed'
        assert record.external_support_level == 'pending'
        assert record.overall_support_level == record.gallup_support_level + '_provisional'
        assert record.source_reference == 'Full Day_Creating an Engaging Workplace for Managers_PPT'
        assert 'not been independently verified' in record.review_notes
        assert record.claim_being_made.startswith('Lower relative results may warrant investigating')
        assert get_validation_by_dimension_id(matrix, record.dimension_id) is record
        assert get_validation_by_source_item(matrix, record.source_item) is record
    assert matrix.get_by_dimension_id('missing') is None
    assert matrix.get_by_source_item('Q03') is None
    assert matrix.get_by_source_item('Q13') is None


def test_review_queries_and_status_counts():
    matrix = load_evidence_validation_matrix()
    assert dimensions_awaiting_external_review(matrix) == matrix.validations
    assert [v.dimension_id for v in dimensions_with_limited_support(matrix)] == ['team_norms_and_coordination']
    assert counts_by_recommended_status(matrix) == {
        'gallup_supported_external_review_pending': 4,
        'partial_support_external_review_pending': 3,
        'indirect_support_external_review_pending': 1,
        'limited_support_external_review_required': 1,
    }
    reviewed = replace(matrix.validations[0], external_support_level='limited', external_research_support='Example review note')
    subset = EvidenceValidationMatrix((reviewed,))
    assert subset.awaiting_external_review() == ()
    assert subset.limited_support() == (reviewed,)


@pytest.mark.parametrize('key', ['dimension_id', 'source_item'])
def test_duplicate_rejection(row, key):
    other = dict(row, dimension_id='other', source_item='Q02')
    other[key] = row[key]
    with pytest.raises(ValueError, match='Duplicate evidence matrix ' + key):
        load_evidence_validation_matrix(stream_for([row, other]))


@pytest.mark.parametrize('column', REQUIRED_COLUMNS)
def test_required_columns_and_nonempty_cells(row, column):
    with pytest.raises(ValueError, match='missing'):
        validate_required_columns([c for c in REQUIRED_COLUMNS if c != column])
    row[column] = ' '
    with pytest.raises(ValueError, match='line 2'):
        load_evidence_validation_matrix(stream_for([row]))


@pytest.mark.parametrize('columns', [(), REQUIRED_COLUMNS + ('extra',), REQUIRED_COLUMNS + ('source_item',)])
def test_invalid_headers(columns):
    with pytest.raises(ValueError):
        validate_required_columns(columns)


@pytest.mark.parametrize('support_type', ['gallup', 'external'])
@pytest.mark.parametrize('level', ['strong', 'moderate', 'limited', 'none'])
def test_allowed_support_levels(support_type, level):
    assert validate_support_level(level, support_type) == level


def test_pending_only_allowed_for_external():
    assert validate_support_level('pending', 'external') == 'pending'
    with pytest.raises(ValueError):
        validate_support_level('pending', 'gallup')
    with pytest.raises(ValueError):
        validate_support_level('strong', 'unknown')


@pytest.mark.parametrize('column,value', [
    ('gallup_support_level', 'pending'), ('gallup_support_level', 'high'),
    ('external_support_level', 'unreviewed'), ('external_support_level', '0.9'),
    ('overall_support_level', 'validated'), ('recommended_status', 'approved'),
    ('source_item', 'Q03'), ('source_item', 'Q10'), ('source_item', 'Q12'), ('source_item', 'Q13'),
])
def test_invalid_categorical_values(row, column, value):
    row[column] = value
    with pytest.raises(ValueError):
        load_evidence_validation_matrix(stream_for([row]))


def test_malformed_csv_empty_rows_and_paths(row, tmp_path):
    header = ','.join(REQUIRED_COLUMNS)
    for text in ('', header + '\n', header + '\n"unterminated', header + '\nshort,row\n'):
        with pytest.raises(ValueError):
            load_evidence_validation_matrix(io.StringIO(text))
    good = stream_for([row]).getvalue()
    with pytest.raises(ValueError):
        load_evidence_validation_matrix(io.StringIO(good.rstrip() + ',extra\n'))
    path = tmp_path / 'matrix.csv'
    path.write_text('\ufeff' + stream_for([{k: ' ' + v + ' ' for k, v in row.items()}], tuple(reversed(REQUIRED_COLUMNS))).getvalue(), encoding='utf-8')
    assert load_evidence_validation_matrix(path).validations[0].dimension_id == row['dimension_id']


def test_no_operational_updates_or_numeric_confidence_fields():
    before = DEFAULT_RUBRIC_PATH.read_bytes()
    matrix = load_evidence_validation_matrix()
    matrix.awaiting_external_review()
    matrix.limited_support()
    matrix.counts_by_recommended_status()
    assert DEFAULT_RUBRIC_PATH.read_bytes() == before
    assert all(d.evidence_status == 'provisional_needs_evidence_review' for d in load_rubric().dimensions)
    assert not any('percent' in key or 'confidence' in key for key in REQUIRED_COLUMNS)


def test_direct_model_validation_and_immutable_collection(row):
    with pytest.raises(ValueError):
        EvidenceValidation(**dict(row, review_notes=None))
    for records in ((), ('invalid',)):
        with pytest.raises(ValueError):
            EvidenceValidationMatrix(records)
    records = [EvidenceValidation(**row)]
    matrix = EvidenceValidationMatrix(records)
    records.clear()
    assert len(matrix.validations) == 1
