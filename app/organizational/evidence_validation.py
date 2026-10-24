"""Separate evidence-review records; never updates operational rubric or scores.

Initial support judgments were supplied in the project request; subsequent
preliminary reviews record sources, review scope and limits explicitly. A source title is
provenance, not proof that the underlying deck or external research was reviewed.
Support labels are categorical provisional judgments, not confidence percentages.
"""
import csv
from collections import Counter
from datetime import date
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Tuple

DEFAULT_MATRIX_PATH = Path(__file__).resolve().parents[2] / 'data/organizational/evidence_validation_matrix.csv'
GALLUP_SUPPORT_LEVELS = ('strong', 'moderate', 'limited', 'none')
EXTERNAL_SUPPORT_LEVELS = ('pending',) + GALLUP_SUPPORT_LEVELS
OVERALL_SUPPORT_LEVELS = tuple(f'{level}_provisional' for level in GALLUP_SUPPORT_LEVELS)
RECOMMENDED_STATUSES = (
    'gallup_supported_external_review_pending',
    'partial_support_external_review_pending',
    'indirect_support_external_review_pending',
    'limited_support_external_review_required',
    'partially_supported', 'indirect_support', 'insufficient_evidence', 'validated',
)
VALIDATION_STATUSES = ('pending', 'validated', 'partially_supported', 'indirect_support', 'insufficient_evidence')
RELATIONSHIP_TYPES = ('direct', 'partial', 'indirect')
SOURCE_ITEMS = ('Q01', 'Q02', 'Q04', 'Q05', 'Q06', 'Q07', 'Q08', 'Q09', 'Q11')


def validate_support_level(value, support_type='gallup'):
    """Validate a categorical support label; never assign a numeric confidence."""
    allowed = {'gallup': GALLUP_SUPPORT_LEVELS, 'external': EXTERNAL_SUPPORT_LEVELS,
               'overall': OVERALL_SUPPORT_LEVELS}
    if support_type not in allowed:
        raise ValueError('support_type must be gallup, external, or overall.')
    if value not in allowed[support_type]:
        raise ValueError(f'Invalid {support_type} support level: {value!r}.')
    return value


@dataclass(frozen=True)
class EvidenceValidation:
    dimension_id: str
    dimension_name: str
    source_item: str
    claim_being_made: str
    gallup_support_summary: str
    gallup_support_level: str
    external_research_support: str
    external_support_level: str
    overall_support_level: str
    recommended_status: str
    source_reference: str
    review_notes: str

    validation_status: str
    relationship_type: str
    allowed_language: str
    prohibited_language: str
    external_source_reference: str
    reviewer: str
    reviewed_on: str
    review_scope: str
    full_text_status: str

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'{field.name} must be nonempty text.')
        if self.review_scope not in ('pending', 'abstract_only', 'targeted_full_text_sections'):
            raise ValueError('Invalid review_scope.')
        if self.full_text_status not in ('pending', 'access_pending', 'targeted_sections_checked'):
            raise ValueError('Invalid full_text_status.')
        if (self.review_scope == 'targeted_full_text_sections') != (self.full_text_status == 'targeted_sections_checked'):
            raise ValueError('Review scope and full-text status must agree.')
        if self.validation_status not in VALIDATION_STATUSES:
            raise ValueError('Invalid validation_status.')
        if self.relationship_type not in RELATIONSHIP_TYPES:
            raise ValueError('Invalid relationship_type.')
        if self.external_support_level == 'pending' and self.validation_status != 'pending':
            raise ValueError('Pending external evidence requires pending validation status.')
        if self.validation_status != 'pending' and any(
            getattr(self, key) in ('pending', 'not_yet_reviewed')
            for key in ('external_source_reference', 'reviewer', 'reviewed_on')
        ):
            raise ValueError('Completed reviews require source references, reviewer and review date.')
        if self.validation_status != 'pending':
            try:
                date.fromisoformat(self.reviewed_on)
            except ValueError as error:
                raise ValueError('reviewed_on must be an ISO date for completed reviews.') from error
        if self.source_item not in SOURCE_ITEMS:
            raise ValueError('source_item must be one of the nine currently mapped Q12 items.')
        validate_support_level(self.gallup_support_level, 'gallup')
        validate_support_level(self.external_support_level, 'external')
        validate_support_level(self.overall_support_level, 'overall')
        if self.recommended_status in VALIDATION_STATUSES and self.recommended_status != self.validation_status:
            raise ValueError('Reviewed recommended_status must match validation_status.')
        if self.recommended_status not in RECOMMENDED_STATUSES:
            raise ValueError('Invalid recommended_status.')


REQUIRED_COLUMNS = tuple(field.name for field in fields(EvidenceValidation))


def validate_required_columns(columns):
    columns = tuple(columns or ())
    if len(columns) != len(set(columns)):
        raise ValueError('Duplicate evidence matrix columns.')
    missing = set(REQUIRED_COLUMNS) - set(columns)
    extra = set(columns) - set(REQUIRED_COLUMNS)
    if missing or extra:
        raise ValueError(f'Invalid evidence matrix columns; missing: {sorted(missing)}; unsupported: {sorted(extra)}')


@dataclass(frozen=True)
class EvidenceValidationMatrix:
    validations: Tuple[EvidenceValidation, ...]

    def __post_init__(self):
        object.__setattr__(self, 'validations', tuple(self.validations))
        if not self.validations or not all(isinstance(v, EvidenceValidation) for v in self.validations):
            raise ValueError('Matrix needs at least one validated evidence record.')
        for key in ('dimension_id', 'source_item'):
            if len({getattr(v, key) for v in self.validations}) != len(self.validations):
                raise ValueError(f'Duplicate evidence matrix {key}.')

    def get_by_dimension_id(self, dimension_id):
        return next((v for v in self.validations if v.dimension_id == dimension_id), None)

    def get_by_source_item(self, source_item):
        return next((v for v in self.validations if v.source_item == source_item), None)

    def awaiting_external_review(self):
        """Pending is taken from the explicit external support field."""
        return tuple(v for v in self.validations if v.external_support_level == 'pending')

    def limited_support(self):
        """Return records rated limited in any reviewed support field or overall."""
        return tuple(v for v in self.validations if
                     v.gallup_support_level == 'limited' or
                     v.external_support_level == 'limited' or
                     v.overall_support_level == 'limited_provisional')

    def counts_by_recommended_status(self):
        """Return counts of observed categories only; no confidence percentages."""
        return dict(Counter(v.recommended_status for v in self.validations))


def load_evidence_validation_matrix(source=DEFAULT_MATRIX_PATH):
    """Load a UTF-8 CSV path or text stream atomically, without changing data.

    Subsets can be loaded for review; the bundled matrix contains all nine
    dimensions. Missing records are never invented. Unknown columns are rejected.
    """
    if isinstance(source, (str, Path)):
        with open(source, encoding='utf-8-sig', newline='') as stream:
            return load_evidence_validation_matrix(stream)
    try:
        reader = csv.DictReader(source, strict=True)
        validate_required_columns(reader.fieldnames)
        records = []
        for row in reader:
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError('Incorrect number of evidence matrix columns.')
                records.append(EvidenceValidation(**{key: value.strip() for key, value in row.items()}))
            except (ValueError, TypeError) as error:
                raise ValueError(f'Invalid evidence matrix row ending at line {reader.line_num}: {error}') from error
        return EvidenceValidationMatrix(tuple(records))
    except csv.Error as error:
        raise ValueError(f'Malformed evidence matrix CSV: {error}') from error


def get_validation_by_dimension_id(matrix, dimension_id):
    return matrix.get_by_dimension_id(dimension_id)


def get_validation_by_source_item(matrix, source_item):
    return matrix.get_by_source_item(source_item)


def dimensions_awaiting_external_review(matrix):
    return matrix.awaiting_external_review()


def dimensions_with_limited_support(matrix):
    return matrix.limited_support()


def counts_by_recommended_status(matrix):
    return matrix.counts_by_recommended_status()
