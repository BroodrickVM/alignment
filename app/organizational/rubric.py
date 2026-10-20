"""Provisional CSV rubric infrastructure; opt-in metadata, not a scoring engine.

Scores remain source item means on the 1–5 scale. No normalization, overall
communication score, absolute thresholds, or changes to analyzer behavior.
"""
import csv
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from string import Formatter
from typing import Tuple

from .models import ITEM_IDS, OrganizationDiagnosticReport

DEFAULT_RUBRIC_PATH = Path(__file__).resolve().parents[2] / 'data/organizational/communication_rubric.csv'
EVIDENCE_STATUS = 'provisional_needs_evidence_review'
RELATIONSHIP_TYPES = ('direct', 'partial', 'indirect')
UNMAPPED_ITEMS = ('Q03', 'Q10', 'Q12')
RELATIVE_POSITIONS = ('relatively stronger signal', 'middle signal', 'area for investigation')
CAUTION = ('The survey result alone does not establish that communication caused the result. '
           'This is a provisional hypothesis; investigate other work conditions and validate it with employees.')
TEMPLATE_FIELDS = {'dimension_name', 'source_item', 'observed_score', 'relative_position', 'definition'}


def validate_relationship_type(value):
    """Return a supported relationship label or raise ValueError."""
    if value not in RELATIONSHIP_TYPES:
        raise ValueError('relationship_type must be direct, partial, or indirect.')
    return value


@dataclass(frozen=True)
class RubricDimension:
    dimension_id: str
    dimension_name: str
    source_item: str
    relationship_type: str
    definition: str
    interpretation_template: str
    manager_question_1: str
    manager_question_2: str
    manager_question_3: str
    evidence_status: str
    limitations: str

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'{field.name} must be nonempty text.')
        if self.source_item not in ITEM_IDS or self.source_item in UNMAPPED_ITEMS:
            raise ValueError('source_item must be a currently mapped Q12 item; Q03, Q10, Q12 remain unmapped.')
        validate_relationship_type(self.relationship_type)
        if self.evidence_status != EVIDENCE_STATUS:
            raise ValueError(f'evidence_status must be {EVIDENCE_STATUS}.')
        try:
            for _, name, spec, conversion in Formatter().parse(self.interpretation_template):
                if name is not None and (name not in TEMPLATE_FIELDS or spec or conversion):
                    raise ValueError('Unsupported interpretation template field or formatting.')
        except ValueError as error:
            raise ValueError(f'Invalid interpretation_template: {error}') from error

    @property
    def manager_questions(self):
        return (self.manager_question_1, self.manager_question_2, self.manager_question_3)


REQUIRED_COLUMNS = tuple(field.name for field in fields(RubricDimension))


def validate_required_columns(columns):
    """Reject absent, duplicate, missing, or unsupported CSV columns."""
    columns = tuple(columns or ())
    if len(columns) != len(set(columns)):
        raise ValueError('Duplicate rubric columns.')
    missing = set(REQUIRED_COLUMNS) - set(columns)
    extra = set(columns) - set(REQUIRED_COLUMNS)
    if missing or extra:
        raise ValueError(f'Invalid rubric columns; missing: {sorted(missing)}; unsupported: {sorted(extra)}')


@dataclass(frozen=True)
class CommunicationRubric:
    dimensions: Tuple[RubricDimension, ...]

    def __post_init__(self):
        object.__setattr__(self, 'dimensions', tuple(self.dimensions))
        if not self.dimensions or not all(isinstance(d, RubricDimension) for d in self.dimensions):
            raise ValueError('Rubric needs at least one validated dimension.')
        for key in ('dimension_id', 'source_item'):
            if len({getattr(d, key) for d in self.dimensions}) != len(self.dimensions):
                raise ValueError(f'Duplicate rubric {key}.')

    def get_by_item(self, item_id):
        """Return None for valid unmapped items; reject invalid item IDs."""
        if item_id not in ITEM_IDS:
            raise ValueError('Item must be Q01 through Q12.')
        return next((d for d in self.dimensions if d.source_item == item_id), None)

    def get_by_id(self, dimension_id):
        """Return the matching dimension, or None if the ID is unknown."""
        return next((d for d in self.dimensions if d.dimension_id == dimension_id), None)

    def unmapped_items(self):
        return tuple(item for item in ITEM_IDS if self.get_by_item(item) is None)


def load_rubric(source=DEFAULT_RUBRIC_PATH):
    """Read a UTF-8 CSV path or text stream; fail atomically on malformed rows.

    Subsets are supported for review. Duplicate IDs/items are rejected and no
    missing dimensions or metadata are invented.
    """
    if isinstance(source, (str, Path)):
        with open(source, encoding='utf-8-sig', newline='') as stream:
            return load_rubric(stream)
    try:
        reader = csv.DictReader(source, strict=True)
        validate_required_columns(reader.fieldnames)
        dimensions = []
        for row in reader:
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError('Incorrect number of rubric columns.')
                dimensions.append(RubricDimension(**{key: value.strip() for key, value in row.items()}))
            except (TypeError, ValueError) as error:
                raise ValueError(f'Invalid rubric row ending at line {reader.line_num}: {error}') from error
        return CommunicationRubric(tuple(dimensions))
    except csv.Error as error:
        raise ValueError(f'Malformed rubric CSV: {error}') from error


def get_dimension_by_item(rubric, item_id):
    return rubric.get_by_item(item_id)


def get_dimension_by_id(rubric, dimension_id):
    return rubric.get_by_id(dimension_id)


def identify_unmapped_items(rubric):
    return rubric.unmapped_items()


def relative_position(report, item_id):
    """Use existing rankings; lower cutoff ties take precedence over strengths.

    Follows the analyzer's bottom-three cutoff (including ties) for areas for
    investigation, then its existing top-three list, then middle. Overlap in
    sparse/tied data is resolved in favor of investigation, not a quality label.
    """
    if not report.item_means or item_id not in report.item_means:
        raise ValueError('Source item mean is missing from the report.')
    if report.opportunities and report.item_means[item_id] <= report.opportunities[-1].mean_score:
        return 'area for investigation'
    if item_id in {result.item_id for result in report.strengths}:
        return 'relatively stronger signal'
    return 'middle signal'


@dataclass(frozen=True)
class RubricSignal:
    dimension_name: str
    source_item: str
    observed_score: float
    relative_position: str
    relationship_type: str
    evidence_status: str
    interpretation: str
    caution: str
    manager_questions: Tuple[str, ...]

    def to_dict(self):
        return asdict(self)


def attach_rubric_metadata(report: OrganizationDiagnosticReport, rubric=None):
    """Return enriched copies of existing signals; leave the report untouched.

    Does not generate extra signals, re-rank items, or calculate a new score.
    Missing mappings and conflicting source scores/relationships fail explicitly.
    The current analyzer selects lower-scoring signals, so these normally carry
    'area for investigation'; the other labels support existing item rankings.
    """
    rubric = load_rubric() if rubric is None else rubric
    enriched = []
    for signal in report.communication_signals:
        dimension = rubric.get_by_item(signal.source_q12_item)
        if dimension is None:
            raise ValueError(f'No rubric dimension for existing signal {signal.source_q12_item}.')
        position = relative_position(report, dimension.source_item)
        if signal.observed_score != report.item_means[dimension.source_item]:
            raise ValueError('Signal score must equal the observed source item mean.')
        if signal.relationship_type != dimension.relationship_type:
            raise ValueError('Rubric relationship conflicts with the existing signal.')
        interpretation = dimension.interpretation_template.format(
            dimension_name=dimension.dimension_name, source_item=dimension.source_item,
            observed_score=signal.observed_score, relative_position=position,
            definition=dimension.definition,
        )
        enriched.append(RubricSignal(
            dimension.dimension_name, dimension.source_item, signal.observed_score,
            position, dimension.relationship_type, dimension.evidence_status,
            interpretation, CAUTION + ' ' + dimension.limitations,
            dimension.manager_questions,
        ))
    return tuple(enriched)
