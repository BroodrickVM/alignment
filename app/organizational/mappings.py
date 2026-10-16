"""Replaceable hypotheses; these associations have not been validated."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SignalMapping:
    item_id: str
    signal: str
    description: str
    relationship_type: str
    confidence_status: str = 'provisional'
    evidence_status: str = 'needs_review'

    def __post_init__(self):
        from .models import ITEM_IDS
        if self.item_id not in ITEM_IDS or self.relationship_type not in ('direct', 'partial', 'indirect'):
            raise ValueError('Invalid mapping item or relationship type.')
        if not self.signal.strip() or not self.description.strip():
            raise ValueError('Mapping signal and description are required.')
        if self.confidence_status != 'provisional' or self.evidence_status != 'needs_review':
            raise ValueError('Mappings must remain provisional and need review.')


DEFAULT_MAPPINGS = tuple(SignalMapping(*row) for row in (
    ('Q01', 'expectations_and_direction', 'clarity of expectations and work direction', 'direct'),
    ('Q02', 'information_and_resource_access', 'access to information and resources needed to perform work', 'partial'),
    ('Q04', 'recognition_communication', 'recognition and reinforcement of valued work', 'direct'),
    ('Q05', 'relational_support', 'perceived care and interpersonal support', 'indirect'),
    ('Q06', 'developmental_communication', 'coaching and encouragement of development', 'direct'),
    ('Q07', 'employee_voice', 'whether employees feel their opinions are heard and valued', 'direct'),
    ('Q08', 'purpose_alignment', 'connection between work and organizational mission or purpose', 'direct'),
    ('Q09', 'team_norms_and_coordination', 'shared commitment to quality and team standards', 'indirect'),
    ('Q11', 'progress_feedback', 'conversations about progress and performance', 'direct'),
))
