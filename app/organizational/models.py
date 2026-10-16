"""Typed aggregated inputs and transparent diagnostic outputs."""
from dataclasses import asdict, dataclass
from math import isfinite
from typing import Dict, Optional, Tuple

ITEM_IDS = tuple(f'Q{i:02d}' for i in range(1, 13))


@dataclass(frozen=True)
class Q12Result:
    team_id: str
    item_id: str
    mean_score: float
    respondent_count: int
    percentile_rank: Optional[float] = None
    period: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.team_id, str) or not self.team_id.strip():
            raise ValueError('team_id must be nonempty.')
        if self.item_id not in ITEM_IDS:
            raise ValueError('item_id must be Q01 through Q12.')
        if isinstance(self.mean_score, bool) or not isinstance(self.mean_score, (int, float)) or not isfinite(self.mean_score) or not 1 <= self.mean_score <= 5:
            raise ValueError('mean_score must be finite and between 1 and 5.')
        if type(self.respondent_count) is not int or self.respondent_count <= 0:
            raise ValueError('respondent_count must be a positive integer.')
        if self.percentile_rank is not None and (isinstance(self.percentile_rank, bool) or not isinstance(self.percentile_rank, (int, float)) or not isfinite(self.percentile_rank) or not 0 <= self.percentile_rank <= 100):
            raise ValueError('percentile_rank must be finite and between 0 and 100.')
        if self.period is not None and (not isinstance(self.period, str) or not self.period.strip()):
            raise ValueError('period must be nonempty when supplied.')


@dataclass(frozen=True)
class CommunicationSignal:
    signal_name: str
    source_q12_item: str
    observed_score: float
    relationship_type: str
    interpretation: str
    caution: str
    manager_questions: Tuple[str, ...]
    confidence_status: str = 'provisional'
    evidence_status: str = 'needs_review'


@dataclass(frozen=True)
class OrganizationDiagnosticReport:
    team_id: str
    grand_mean: float
    hierarchy_scores: Dict[str, Optional[float]]
    strengths: Tuple[Q12Result, ...]
    opportunities: Tuple[Q12Result, ...]
    communication_signals: Tuple[CommunicationSignal, ...]
    manager_questions: Tuple[str, ...]
    limitations: Tuple[str, ...]
    period: Optional[str] = None
    missing_items: Tuple[str, ...] = ()
    hierarchy_strengths: Tuple[str, ...] = ()
    hierarchy_opportunities: Tuple[str, ...] = ()
    item_means: Optional[Dict[str, float]] = None

    def to_dict(self):
        """Return a JSON-serializable representation, including input provenance."""
        return asdict(self)
