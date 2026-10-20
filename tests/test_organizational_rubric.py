"""Rubric validation and opt-in enrichment must preserve current diagnostics."""
import csv
from dataclasses import replace
import io
import json

import pytest

from app.organizational import Q12Result, analyze_csv, analyze_results
from app.organizational.mappings import DEFAULT_MAPPINGS
from app.organizational.rubric import (
    CAUTION, DEFAULT_RUBRIC_PATH, EVIDENCE_STATUS, REQUIRED_COLUMNS,
    CommunicationRubric, RubricDimension, attach_rubric_metadata,
    get_dimension_by_id, get_dimension_by_item, identify_unmapped_items,
    load_rubric, relative_position, validate_relationship_type,
    validate_required_columns,
)


def csv_stream(rows, columns=REQUIRED_COLUMNS):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    stream.seek(0)
    return stream


@pytest.fixture
def row():
    with DEFAULT_RUBRIC_PATH.open(newline='') as stream:
        return next(csv.DictReader(stream))


def test_formal_rubric_matches_existing_mappings():
    rubric = load_rubric()
    assert len(rubric.dimensions) == 9
    expected_names = (
        'Expectations & Direction', 'Information & Resource Access',
        'Recognition Communication', 'Relational Support', 'Developmental Communication',
        'Employee Voice', 'Purpose Alignment', 'Team Norms & Coordination', 'Progress Feedback',
    )
    assert tuple(d.dimension_name for d in rubric.dimensions) == expected_names
    for dimension, mapping in zip(rubric.dimensions, DEFAULT_MAPPINGS):
        assert dimension.dimension_id == mapping.signal
        assert dimension.source_item == mapping.item_id
        assert dimension.relationship_type == mapping.relationship_type
        assert dimension.definition == mapping.description
        assert dimension.evidence_status == EVIDENCE_STATUS
        assert len(dimension.manager_questions) == 3
        assert all(q.endswith('?') for q in dimension.manager_questions)
        assert get_dimension_by_item(rubric, mapping.item_id) is dimension
        assert get_dimension_by_id(rubric, mapping.signal) is dimension
    assert identify_unmapped_items(rubric) == ('Q03', 'Q10', 'Q12')
    assert rubric.get_by_id('unknown') is None
    assert rubric.get_by_item('Q03') is None
    with pytest.raises(ValueError):
        rubric.get_by_item('Q13')


@pytest.mark.parametrize('relationship', ['direct', 'partial', 'indirect'])
def test_valid_relationships(relationship):
    assert validate_relationship_type(relationship) == relationship


@pytest.mark.parametrize('relationship', ['', 'causal', 'Direct', None, 1])
def test_invalid_relationships(relationship):
    with pytest.raises(ValueError, match='relationship_type'):
        validate_relationship_type(relationship)


@pytest.mark.parametrize('missing', REQUIRED_COLUMNS)
def test_each_required_column(missing):
    columns = [c for c in REQUIRED_COLUMNS if c != missing]
    with pytest.raises(ValueError, match='missing'):
        validate_required_columns(columns)


@pytest.mark.parametrize('columns', [(), REQUIRED_COLUMNS + ('extra',), REQUIRED_COLUMNS + ('source_item',)])
def test_invalid_headers(columns):
    with pytest.raises(ValueError):
        validate_required_columns(columns)


@pytest.mark.parametrize('column', REQUIRED_COLUMNS)
def test_empty_values_rejected(row, column):
    row[column] = '  '
    with pytest.raises(ValueError, match='row ending at line 2'):
        load_rubric(csv_stream([row]))


@pytest.mark.parametrize('item', ['Q03', 'Q10', 'Q12', 'Q00', 'Q13', 'q01', 'Q1'])
def test_unmapped_or_invalid_source_rejected(row, item):
    row['source_item'] = item
    with pytest.raises(ValueError, match='source_item'):
        load_rubric(csv_stream([row]))


@pytest.mark.parametrize('status', ['validated', 'needs_review', 'provisional', ''])
def test_evidence_status_stays_provisional(row, status):
    row['evidence_status'] = status
    with pytest.raises(ValueError, match='evidence_status'):
        load_rubric(csv_stream([row]))


@pytest.mark.parametrize('template', [
    '{unknown}', '{definition.__class__}', '{definition[0]}', '{}',
    '{observed_score:.2f}', '{definition!r}', '{definition',
])
def test_malformed_or_unsupported_templates(row, template):
    row['interpretation_template'] = template
    with pytest.raises(ValueError, match='interpretation_template'):
        load_rubric(csv_stream([row]))


def test_valid_csv_paths_reordered_columns_and_trimmed_cells(row, tmp_path):
    columns = tuple(reversed(REQUIRED_COLUMNS))
    stream = csv_stream([{k: ' ' + v + ' ' for k, v in row.items()}], columns)
    path = tmp_path / 'rubric.csv'
    path.write_text('\ufeff' + stream.getvalue(), encoding='utf-8')
    rubric = load_rubric(path)
    assert rubric.dimensions[0].source_item == 'Q01'
    assert len(identify_unmapped_items(rubric)) == 11


def test_malformed_csv_and_empty_input(row):
    for text in ('', ','.join(REQUIRED_COLUMNS) + '\n', ','.join(REQUIRED_COLUMNS) + '\n"unterminated'):
        with pytest.raises(ValueError):
            load_rubric(io.StringIO(text))
    good = csv_stream([row]).getvalue()
    header, data = good.splitlines()
    for text in (header + '\n' + data + ',extra\n', header + '\nshort,row\n'):
        with pytest.raises(ValueError, match='number of rubric columns'):
            load_rubric(io.StringIO(text))


@pytest.mark.parametrize('key', ['source_item', 'dimension_id'])
def test_duplicate_keys_fail_atomically(row, key):
    other = dict(row)
    other['dimension_id'] = 'other' if key == 'source_item' else row['dimension_id']
    other['source_item'] = 'Q02' if key == 'dimension_id' else row['source_item']
    with pytest.raises(ValueError, match='Duplicate rubric ' + key):
        load_rubric(csv_stream([row, other]))


def test_direct_model_validation_and_immutable_collection(row):
    with pytest.raises(ValueError):
        CommunicationRubric(())
    with pytest.raises(ValueError):
        CommunicationRubric(('invalid',))
    with pytest.raises(ValueError):
        RubricDimension(**dict(row, definition=None))
    dimensions = [RubricDimension(**row)]
    rubric = CommunicationRubric(dimensions)
    dimensions.clear()
    assert len(rubric.dimensions) == 1


def test_enrichment_exact_scores_and_no_mutation():
    reports = analyze_csv(DEFAULT_RUBRIC_PATH.parent / 'sample_q12_results.csv')
    for report in reports:
        before = report.to_dict()
        enriched = attach_rubric_metadata(report)
        assert len(enriched) == len(report.communication_signals)
        for new, old in zip(enriched, report.communication_signals):
            assert new.source_item == old.source_q12_item
            assert new.observed_score == old.observed_score == report.item_means[new.source_item]
            assert 1 <= new.observed_score <= 5
            assert new.relationship_type == old.relationship_type
            assert new.evidence_status == EVIDENCE_STATUS
            assert new.relative_position == 'area for investigation'
            assert new.caution.startswith(CAUTION)
            assert 'does not establish that communication caused the result' in new.caution
            assert 'provisional hypothesis' in new.interpretation
            assert len(new.manager_questions) == 3
            assert set(new.to_dict()) == {
                'dimension_name', 'source_item', 'observed_score', 'relative_position',
                'relationship_type', 'evidence_status', 'interpretation', 'caution', 'manager_questions',
            }
            assert json.loads(json.dumps(new.to_dict()))['observed_score'] == old.observed_score
            for phrase in ('caused by', 'proves', 'bad', 'good', 'percent', 'overall communication score'):
                assert phrase not in new.interpretation.lower()
        assert report.to_dict() == before
        assert attach_rubric_metadata(report) == enriched


def test_relative_positions_use_existing_rankings_and_no_absolute_thresholds():
    # Even a 4/5 can be an area for investigation in a relatively stronger team.
    report, = analyze_results([Q12Result('t', f'Q{i:02d}', 4 + i / 12, 10) for i in range(1, 13)])
    assert relative_position(report, 'Q01') == 'area for investigation'
    assert relative_position(report, 'Q07') == 'middle signal'
    assert relative_position(report, 'Q12') == 'relatively stronger signal'
    tied, = analyze_results([Q12Result('t', f'Q{i:02d}', 3, 10) for i in range(1, 13)])
    assert all(s.relative_position == 'area for investigation' for s in attach_rubric_metadata(tied))
    sparse, = analyze_results([Q12Result('t', 'Q01', 5, 10)])
    assert relative_position(sparse, 'Q01') == 'area for investigation'
    with pytest.raises(ValueError, match='missing'):
        relative_position(sparse, 'Q02')


def test_unmapped_inputs_and_empty_signals_not_enriched():
    report, = analyze_results([Q12Result('t', item, 3, 10) for item in ('Q03', 'Q10', 'Q12')])
    assert attach_rubric_metadata(report) == ()


def test_missing_mapping_and_conflicting_metadata_fail():
    report, = analyze_results([Q12Result('t', 'Q01', 3, 10)])
    rubric = load_rubric()
    subset = CommunicationRubric((rubric.get_by_item('Q02'),))
    with pytest.raises(ValueError, match='No rubric dimension'):
        attach_rubric_metadata(report, subset)
    conflict = CommunicationRubric((replace(rubric.get_by_item('Q01'), relationship_type='indirect'),))
    with pytest.raises(ValueError, match='relationship conflicts'):
        attach_rubric_metadata(report, conflict)
    wrong_score = replace(report.communication_signals[0], observed_score=4)
    with pytest.raises(ValueError, match='must equal'):
        attach_rubric_metadata(replace(report, communication_signals=(wrong_score,)))
