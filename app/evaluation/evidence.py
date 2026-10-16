"""Load evidence metadata locally; structural checks do not verify research.

This module is independent of the scoring engine and performs no retrieval.
"""
import csv
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence, Union


REQUIRED_COLUMNS = (
    'source_id', 'authors', 'year', 'title', 'source_type', 'publication',
    'doi_or_url', 'communication_dimension', 'construct_definition',
    'supported_behavior', 'undesirable_behavior', 'evidence_summary',
    'measurement_guidance', 'applicable_context', 'limitations',
    'evidence_strength', 'notes',
)
DEFAULT_MATRIX_PATH = Path(__file__).resolve().parents[2] / 'data' / 'research' / 'evidence_matrix.csv'


class EvidenceValidationError(ValueError):
    """The matrix is not a structurally valid evidence CSV."""


def validate_required_columns(columns: Optional[Sequence[str]]) -> None:
    """Require all schema fields and reject empty or duplicate header names.

    Column order is flexible; additional named columns are allowed.
    """
    if not columns:
        raise EvidenceValidationError('Evidence matrix must contain a header.')
    if any(not isinstance(column, str) or not column.strip() for column in columns):
        raise EvidenceValidationError('Column names must be non-empty strings.')
    if len(set(columns)) != len(columns):
        raise EvidenceValidationError('Duplicate column names are not allowed.')
    missing = [column for column in REQUIRED_COLUMNS if column not in columns]
    if missing:
        raise EvidenceValidationError('Missing required columns: ' + ', '.join(missing))


def load_evidence_matrix(path: Union[str, Path] = DEFAULT_MATRIX_PATH) -> list:
    """Return row dictionaries from a UTF-8 CSV, including an empty matrix.

    Reject invalid encoding, CSV syntax, NUL characters, and mismatched row
    widths. Blank lines are ignored; blank cells are retained for review.
    File access errors propagate to the caller. No claim verification occurs.
    """
    rows = []
    try:
        with open(path, encoding='utf-8-sig', newline='') as stream:
            reader = csv.reader(stream, strict=True)
            columns = next(reader, None)
            validate_required_columns(columns)
            if any('\x00' in value for value in columns):
                raise EvidenceValidationError('NUL characters are not allowed.')
            for values in reader:
                if not values:
                    continue
                if len(values) != len(columns):
                    raise EvidenceValidationError(
                        f'Line {reader.line_num}: expected {len(columns)} cells, got {len(values)}.'
                    )
                if any('\x00' in value for value in values):
                    raise EvidenceValidationError(f'Line {reader.line_num}: NUL characters are not allowed.')
                rows.append(dict(zip(columns, values)))
    except (csv.Error, UnicodeError) as error:
        raise EvidenceValidationError(f'Malformed evidence file: {error}') from error
    return rows


def filter_evidence_by_dimension(evidence: Iterable[Mapping[str, str]], dimension: str) -> list:
    """Return matching rows using case-insensitive, whitespace-trimmed names.

    Unknown dimensions return an empty list. Each row links to one dimension.
    """
    if not isinstance(dimension, str) or not dimension.strip():
        raise ValueError('Dimension must be a non-empty string.')
    requested = dimension.strip().casefold()
    return [dict(row) for row in evidence
            if row['communication_dimension'].strip().casefold() == requested]


def get_evidence_for_dimension(dimension: str, path: Union[str, Path] = DEFAULT_MATRIX_PATH) -> list:
    """Load and validate a matrix, then return evidence for one dimension."""
    return filter_evidence_by_dimension(load_evidence_matrix(path), dimension)
