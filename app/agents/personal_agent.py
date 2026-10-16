"""Orchestrate personal-use scoring and a conservative revision template."""
from dataclasses import dataclass
from typing import Optional
from ..evaluation.rubric import CommunicationContext, Evaluation, Rubric


@dataclass(frozen=True)
class PersonalReport:
    """Evaluation plus an author-editable suggestion; never sent automatically."""

    original: str
    context: CommunicationContext
    evaluation: Evaluation
    suggested_revision: str

    def to_dict(self) -> dict:
        """Return JSON-ready evaluation fields without changing the typed API."""
        return {
            'dimensions': [
                {
                    'dimension': result.dimension,
                    'score': result.score,
                    'explanation': result.explanation,
                    'improvement_suggestion': result.improvement_suggestion,
                }
                for result in self.evaluation.results
            ],
            'overall_alignment_score': self.evaluation.overall_score,
            'overall_summary': self.evaluation.summary,
            'suggested_revised_communication': self.suggested_revision,
            'provisional': self.evaluation.provisional,
        }


class PersonalAgent:
    """Run a local rubric; no model calls or research retrieval in this version."""

    def __init__(self, rubric: Optional[Rubric] = None):
        self.rubric = rubric or Rubric()

    def evaluate(self, communication: str, context: Optional[CommunicationContext] = None) -> PersonalReport:
        """Preserve original content and add explicit placeholders for missing detail."""
        context = context or CommunicationContext()
        evaluation = self.rubric.evaluate(communication, context)
        revision = (
            'Suggested structure (template only; review and replace brackets):\n'
            f'To: {context.audience.strip() or "[intended audience]"}\n'
            f'Purpose: {context.purpose.strip() or "[intended outcome]"}\n\n'
            f'{communication.strip()}\n\n'
            '[If a response is needed: please state the requested action, owner, and deadline.]\n'
            '[Add necessary background; remove this line if no additional context is needed.]'
        )
        return PersonalReport(communication, context, evaluation, revision)
