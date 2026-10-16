"""Neutral investigation prompts, not causal explanations."""
from .models import CommunicationSignal

QUESTIONS = {
    'Q01': ('Do employees understand what success looks like in their roles?', 'Are priorities communicated consistently?', 'Are responsibilities and expected outcomes explicit?'),
    'Q02': ('Can employees find the information needed for their work?', 'Which resource constraints or access barriers should be investigated?'),
    'Q04': ('How is valued work recognized?', 'What recognition do team members find meaningful?'),
    'Q05': ('What helps team members feel supported?', 'What interpersonal or organizational conditions should be explored?'),
    'Q06': ('How do employees experience development conversations?', 'What coaching and development support would be useful?'),
    'Q07': ('How are employee opinions invited and considered?', 'Do employees receive follow-up on suggestions?'),
    'Q08': ('How do employees connect their work to organizational purpose?', 'Which aspects of the mission need discussion?'),
    'Q09': ('How does the team discuss shared quality standards?', 'What workflow or resource conditions affect coordination?'),
    'Q11': ('How do employees experience conversations about progress?', 'What feedback would help employees understand their progress?'),
}


def make_signal(result, mapping):
    return CommunicationSignal(
        mapping.signal, result.item_id, result.mean_score, mapping.relationship_type,
        f'This relatively lower-scoring result may indicate an opportunity to investigate {mapping.description}. It is a provisional communication hypothesis.',
        'This survey result alone does not establish that manager communication is the cause. Other work conditions may contribute; investigate with the team.',
        QUESTIONS.get(result.item_id, (f'How does the team experience {mapping.description}?',)),
        mapping.confidence_status, mapping.evidence_status,
    )
