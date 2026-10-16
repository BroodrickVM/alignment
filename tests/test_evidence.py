"""Structural tests using synthetic parser fixtures, never research records."""
import csv

import pytest

from app.evaluation.evidence import (
    DEFAULT_MATRIX_PATH,
    REQUIRED_COLUMNS,
    EvidenceValidationError,
    filter_evidence_by_dimension,
    get_evidence_for_dimension,
    load_evidence_matrix,
    validate_required_columns,
)


EXPECTED_COLUMNS = (
    'source_id', 'authors', 'year', 'title', 'source_type', 'publication',
    'doi_or_url', 'communication_dimension', 'construct_definition',
    'supported_behavior', 'undesirable_behavior', 'evidence_summary',
    'measurement_guidance', 'applicable_context', 'limitations',
    'evidence_strength', 'notes',
)


def write_matrix(tmp_path, rows=(), columns=REQUIRED_COLUMNS, encoding='utf-8'):
    path = tmp_path / 'synthetic_matrix.csv'
    with path.open('w', encoding=encoding, newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)
    return path


def synthetic_row(dimension):
    row = dict.fromkeys(REQUIRED_COLUMNS, '')
    row['communication_dimension'] = dimension
    row['notes'] = 'Synthetic parser fixture only, not research.\nQuoted, multiline text: "café".'
    return row


def test_repository_matrix_has_only_exact_requested_headers():
    assert REQUIRED_COLUMNS == EXPECTED_COLUMNS
    with DEFAULT_MATRIX_PATH.open(encoding='utf-8', newline='') as stream:
        assert list(csv.reader(stream)) == [list(EXPECTED_COLUMNS)]
    assert load_evidence_matrix() == []
    assert get_evidence_for_dimension('Clarity') == []


def test_header_only_matrix(tmp_path):
    assert load_evidence_matrix(write_matrix(tmp_path)) == []


def test_load_preserves_quoted_multiline_unicode_and_blank_cells(tmp_path):
    row = synthetic_row('Clarity')
    path = write_matrix(tmp_path, [list(row.values())], encoding='utf-8-sig')
    assert load_evidence_matrix(str(path)) == [row]


def test_column_order_and_additional_columns(tmp_path):
    columns = tuple(reversed(REQUIRED_COLUMNS)) + ('extra',)
    row = synthetic_row('Clarity')
    row['extra'] = 'Parser extension'
    path = write_matrix(tmp_path, [[row[column] for column in columns]], columns)
    validate_required_columns(columns)
    assert load_evidence_matrix(path) == [row]


@pytest.mark.parametrize('columns', [
    None, [], REQUIRED_COLUMNS[:-1], REQUIRED_COLUMNS + ('notes',),
    REQUIRED_COLUMNS + ('',), REQUIRED_COLUMNS + ('  ',),
    REQUIRED_COLUMNS + (None,),
])
def test_invalid_headers_rejected(columns):
    with pytest.raises(EvidenceValidationError):
        validate_required_columns(columns)


@pytest.mark.parametrize('columns', [
    REQUIRED_COLUMNS[:-1], REQUIRED_COLUMNS + ('notes',), REQUIRED_COLUMNS + ('',),
])
def test_loader_rejects_invalid_headers(tmp_path, columns):
    with pytest.raises(EvidenceValidationError):
        load_evidence_matrix(write_matrix(tmp_path, columns=columns))


@pytest.mark.parametrize('contents', [b'', b'\xff\xfe', b'"unclosed header'])
def test_empty_invalid_encoding_and_csv_rejected(tmp_path, contents):
    path = tmp_path / 'invalid.csv'
    path.write_bytes(contents)
    with pytest.raises(EvidenceValidationError):
        load_evidence_matrix(path)


@pytest.mark.parametrize('size', [len(REQUIRED_COLUMNS) - 1, len(REQUIRED_COLUMNS) + 1])
def test_wrong_row_width_rejected(tmp_path, size):
    path = write_matrix(tmp_path, [[''] * size])
    with pytest.raises(EvidenceValidationError, match='expected .* cells'):
        load_evidence_matrix(path)


def test_malformed_quoted_row_rejected(tmp_path):
    path = write_matrix(tmp_path)
    with path.open('a', encoding='utf-8') as stream:
        stream.write('"unterminated')
    with pytest.raises(EvidenceValidationError, match='Malformed evidence file'):
        load_evidence_matrix(path)


def test_nul_rejected(tmp_path):
    row = synthetic_row('Clarity')
    row['notes'] = '\x00'
    with pytest.raises(EvidenceValidationError, match='NUL'):
        load_evidence_matrix(write_matrix(tmp_path, [list(row.values())]))


def test_blank_lines_ignored(tmp_path):
    path = write_matrix(tmp_path)
    with path.open('a', encoding='utf-8') as stream:
        stream.write('\n\n')
    assert load_evidence_matrix(path) == []


def test_missing_file_propagates(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_evidence_matrix(tmp_path / 'missing.csv')


def test_filter_and_dimension_lookup(tmp_path):
    rows = [synthetic_row(name) for name in ['Clarity', 'Actionability', ' clarity ']]
    expected = [rows[0], rows[2]]
    assert filter_evidence_by_dimension(iter(rows), ' CLARITY ') == expected
    assert filter_evidence_by_dimension(rows, 'Unknown') == []
    assert filter_evidence_by_dimension([], 'Clarity') == []
    path = write_matrix(tmp_path, [list(row.values()) for row in rows])
    assert get_evidence_for_dimension('Clarity', path) == expected
    assert get_evidence_for_dimension('Unknown', path) == []
    filtered = filter_evidence_by_dimension(rows, 'Clarity')
    filtered[0]['notes'] = 'Changed copy'
    assert rows[0]['notes'] != 'Changed copy'


@pytest.mark.parametrize('dimension', ['', '  ', None])
def test_invalid_dimension_request_rejected(dimension):
    with pytest.raises(ValueError, match='Dimension'):
        filter_evidence_by_dimension([], dimension)


def test_dimension_lookup_validates_file_first(tmp_path):
    path = write_matrix(tmp_path, columns=['communication_dimension'])
    with pytest.raises(EvidenceValidationError, match='Missing required columns'):
        get_evidence_for_dimension('Clarity', path)
