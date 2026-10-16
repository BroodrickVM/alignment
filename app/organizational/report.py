"""Readable terminal report. Run: python -m app.organizational.report CSV_PATH."""
import argparse
from .analyzer import analyze_csv


# Plain-language item topics describe survey content, not communication mappings.
ITEM_TOPICS = {
    'Q01': 'clarity of work expectations',
    'Q02': 'access to needed resources',
    'Q03': 'opportunities to use strengths at work',
    'Q04': 'recognition of valued work',
    'Q05': 'care and interpersonal support',
    'Q06': 'encouragement of development',
    'Q07': 'feeling heard and having opinions valued',
    'Q08': 'connection to organizational purpose',
    'Q09': 'shared commitment to quality',
    'Q10': 'close workplace relationships',
    'Q11': 'conversations about progress',
    'Q12': 'opportunities to learn and grow',
}

PRIORITY_TOPICS = {
    'expectations_and_direction': 'expectations and priorities',
    'information_and_resource_access': 'information and resource access',
    'recognition_communication': 'recognition of valued work',
    'relational_support': 'interpersonal support',
    'developmental_communication': 'coaching and development conversations',
    'employee_voice': 'opportunities for employee input',
    'purpose_alignment': 'connections between work and purpose',
    'team_norms_and_coordination': 'shared standards and coordination',
    'progress_feedback': 'progress and feedback conversations',
}


def conversation_priorities(report):
    """Offer up to three signal-grounded discussion topics, never prescriptions.

    With fewer than three distinct signals, use additional questions about the
    observed topic rather than inventing additional diagnostic signals.
    """
    topics = list(dict.fromkeys(
        PRIORITY_TOPICS.get(s.signal_name, s.signal_name.replace('_', ' '))
        for s in report.communication_signals
    ))
    if not topics:
        return ()
    priorities = [f'Explore team experiences of {topic}.' for topic in topics[:3]]
    if len(priorities) < 3:
        priorities.append(f'Discuss what currently works well around {topics[0]}.')
    if len(priorities) < 3:
        priorities.append(f'Ask what the team would like to understand better about {topics[0]}.')
    return tuple(priorities)


def render_report(report):
    lines = [f'Organizational Communication Diagnostic — {report.team_id}',
             '', '1. Executive Summary',
             f'Team ID: {report.team_id}',
             f'Period: {report.period or "not supplied"}',
             f'GrandMean: {report.grand_mean:.2f} / 5',
             'Strongest Hierarchy Area: ' + ', '.join(report.hierarchy_strengths),
             'Main Hierarchy Area for Investigation: ' + ', '.join(report.hierarchy_opportunities),
             'Summary: Available survey results show relative stronger and weaker signals within this team and period, offering hypotheses for discussion rather than causal conclusions.',
             'Hierarchy summaries:']
    lines.extend(f'  {name}: {score:.2f} / 5' if score is not None else f'  {name}: unavailable' for name, score in report.hierarchy_scores.items())
    lines.append('Hierarchy ties are listed together; rankings are relative to available results.')
    for label, records, stronger in [
        ('2. Stronger Signals', report.strengths, True),
        ('3. Areas for Investigation', report.opportunities, False),
    ]:
        lines.extend(['', label])
        for result in records:
            percentile = f'; supplied percentile: {result.percentile_rank:g}' if result.percentile_rank is not None else ''
            lines.append(f'  {result.item_id}: {result.mean_score:.2f} / 5 (n={result.respondent_count}){percentile}')
            topic = ITEM_TOPICS[result.item_id]
            interpretation = (
                f'A relatively stronger signal concerning {topic} within this team and period.'
                if stronger else
                f'A relatively lower-scoring signal concerning {topic}; explore team experiences.'
            )
            lines.append(f'  Interpretation: {interpretation}')
    lines.extend(['', '4. Communication Signals to Explore'])
    if not report.communication_signals:
        lines.append('  No mapped items in the lower-scoring selection.')
    for signal in report.communication_signals:
        lines.extend([f'  Signal: {signal.signal_name.replace("_", " ").title()}',
                      f'  Source Q12 item: {signal.source_q12_item}',
                      f'  Observed score: {signal.observed_score:.2f} / 5',
                      f'  Relationship type: {signal.relationship_type}; {signal.confidence_status}; {signal.evidence_status}',
                      f'  Interpretation: {signal.interpretation}', f'  Caution: {signal.caution}', '  Questions to investigate:'])
        questions = list(dict.fromkeys(signal.manager_questions))[:3]
        for question in ('What experiences might help the team understand this result?',
                         'What other work conditions should the team explore?'):
            if len(questions) >= 2:
                break
            if question not in questions:
                questions.append(question)
        lines.extend(f'    - {question}' for question in questions)
    lines.extend(['', '5. Recommended Conversation Priorities',
                  'Discussion priorities only, not prescriptions; based on the communication signals above.'])
    priorities = conversation_priorities(report)
    lines.extend(f'  - {priority}' for priority in priorities)
    if not priorities:
        lines.append('  No communication signals selected; no signal-based conversation priorities generated.')
    lines.extend(['', '6. Limitations'])
    lines.extend(f'  - {limitation}' for limitation in report.limitations)
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_path')
    args = parser.parse_args(argv)
    try:
        reports = analyze_csv(args.csv_path)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print('\n\n'.join(render_report(report) for report in reports))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
