"""Render a personal report as editable plain text without external services."""
from ..agents.personal_agent import PersonalReport


def generate_report(report: PersonalReport) -> str:
    """Include every dimension, score, explanation, recommendation, and revision."""
    lines = ['AlignAgent | Personal-Use Communication Evaluation',
             'PROVISIONAL: configurable rule-based signals, not a validated research rubric.', '']
    for result in report.evaluation.results:
        lines.extend([
            f'Dimension: {result.dimension}',
            f'Score: {result.score}/5',
            f'Explanation: {result.explanation}',
            f'Improvement suggestion: {result.improvement_suggestion}', '',
        ])
    lines.extend([f'Overall alignment score: {report.evaluation.overall_score:.2f}/5', '',
                  'Overall summary:', report.evaluation.summary, '',
                  'Suggested revised communication:', report.suggested_revision])
    return '\n'.join(lines)
