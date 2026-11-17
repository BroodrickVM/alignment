"""Manager discussion options, separate from diagnostic and evidence calculations."""
import csv
from dataclasses import dataclass, fields
from pathlib import Path

from .rubric import load_rubric

DEFAULT_ACTION_PLAN_PATH = Path(__file__).resolve().parents[2] / 'data/organizational/action_plan_rubric.csv'
ACTION_CAPTION = ('Structured follow-up options for the selected communication signals. '
                  'These are discussion and follow-up suggestions, not proven interventions.')
WHY_HIGHLIGHTED = ('This communication-related item is among the relatively lower-scoring '
                   'signals selected for investigation within this team and period.')


@dataclass(frozen=True)
class ActionPlan:
    dimension_id: str
    dimension_name: str
    source_item: str
    suggested_action: str
    suggested_timeline: str
    success_indicator: str
    follow_up_guidance: str
    action_caution: str

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'{field.name} must be nonempty text.')


REQUIRED_COLUMNS = tuple(field.name for field in fields(ActionPlan))


@dataclass(frozen=True)
class ActionLibrary:
    plans: tuple

    def __post_init__(self):
        object.__setattr__(self, 'plans', tuple(self.plans))
        rubric = load_rubric()
        for key in ('dimension_id', 'source_item'):
            if len({getattr(p, key) for p in self.plans}) != len(self.plans):
                raise ValueError(f'Duplicate action-plan {key}.')
        for plan in self.plans:
            dimension = rubric.get_by_id(plan.dimension_id)
            if dimension is None:
                raise ValueError(f'Unknown rubric dimension_id: {plan.dimension_id}.')
            if rubric.get_by_item(plan.source_item) is None:
                raise ValueError('source_item must be a currently mapped communication item.')
            if dimension.source_item != plan.source_item or dimension.dimension_name != plan.dimension_name:
                raise ValueError('Action-plan mapping conflicts with the communication rubric.')

    def get_by_dimension_id(self, dimension_id):
        return next((p for p in self.plans if p.dimension_id == dimension_id), None)

    def get_by_source_item(self, source_item):
        return next((p for p in self.plans if p.source_item == source_item), None)


def load_action_plans(source=DEFAULT_ACTION_PLAN_PATH):
    """Load validated metadata atomically; subsets never receive invented entries."""
    if isinstance(source, (str, Path)):
        with open(source, encoding='utf-8-sig', newline='') as stream:
            return load_action_plans(stream)
    try:
        reader = csv.DictReader(source, strict=True)
        columns = tuple(reader.fieldnames or ())
        if len(columns) != len(set(columns)) or set(columns) != set(REQUIRED_COLUMNS):
            raise ValueError('Invalid action-plan columns: missing, unsupported, or duplicate columns.')
        plans = []
        for row in reader:
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError('Incorrect number of action-plan columns.')
                plans.append(ActionPlan(**{key: value.strip() for key, value in row.items()}))
            except (TypeError, ValueError) as error:
                raise ValueError(f'Invalid action-plan row ending at line {reader.line_num}: {error}') from error
        return ActionLibrary(tuple(plans))
    except csv.Error as error:
        raise ValueError(f'Malformed action-plan CSV: {error}') from error


@dataclass(frozen=True)
class SelectedActionPlan:
    plan: ActionPlan
    observed_score: float
    why_highlighted: str = WHY_HIGHLIGHTED


def action_plans_for_report(report, action_library):
    """Consume existing signal order, cap at three, and never mutate the report."""
    if report.suppressed:
        return ()
    selected = []
    for signal in report.communication_signals:
        plan = action_library.get_by_source_item(signal.source_q12_item)
        if plan is None or plan.dimension_id != signal.signal_name:
            raise ValueError(f'Missing or conflicting action-plan metadata for {signal.source_q12_item}.')
        selected.append(SelectedActionPlan(plan, signal.observed_score))
    return tuple(selected[:3])
