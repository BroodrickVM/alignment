"""Local presentation layer. Run: streamlit run app/organizational/dashboard.py."""
from pathlib import Path
import sys

# Streamlit executes this file as a script; resolve imports from any working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.organizational.analyzer import analyze_csv
from app.organizational.report import ITEM_TOPICS, conversation_priorities, render_report

SAMPLE_PATH = PROJECT_ROOT / 'data' / 'organizational' / 'sample_q12_results.csv'
SYNTHETIC_LABEL = 'Synthetic demonstration data — not real Gallup results.'
NEXT_STEPS = (
    'Review the identified signals.',
    'Discuss the findings with the team.',
    'Ask the suggested questions to understand what is behind the survey results.',
    'Document what the team says.',
    'Decide whether additional evidence or action is needed.',
)
VALIDATION_CAUTION = 'Validate the hypotheses with employees before taking action.'
MISSING_ITEMS_CAUTION = 'Missing items are not imputed; available-item summaries may not be comparable to complete summaries.'


def _join_topics(topics):
    if len(topics) < 2:
        return ''.join(topics)
    return ', '.join(topics[:-1]) + ' and ' + topics[-1]


def executive_narrative(report):
    """Describe existing rankings and selected signals without new inference."""
    if set(report.hierarchy_strengths) == set(report.hierarchy_opportunities):
        hierarchy = ('Available hierarchy areas are tied; the results do not distinguish '
                     'a strongest area from an area for investigation.')
    else:
        stronger = _join_topics(report.hierarchy_strengths)
        investigation = _join_topics(report.hierarchy_opportunities)
        verb = 'is the primary hierarchy area' if len(report.hierarchy_opportunities) == 1 else 'are tied hierarchy areas'
        hierarchy = (f'This team shows relatively stronger signals in {stronger}, '
                     f'while {investigation} {verb} for investigation.')
    topics = tuple(dict.fromkeys(
        'clarity of expectations' if signal.signal_name == 'expectations_and_direction'
        else signal.signal_name.replace('_', ' ')
        for signal in report.communication_signals
    ))
    communication = (
        f'Communication-related signals suggest exploring {_join_topics(topics)}.'
        if topics else 'No mapped communication signals were selected for exploration.'
    )
    return f'{hierarchy} {communication}'


def diagnostic_summary_text(report):
    """Download the selected report with the same cautions and discussion steps."""
    text = render_report(report)
    text = text.replace('Hierarchy summaries:', executive_narrative(report) + '\n\nHierarchy scores:', 1)
    next_section = '\n'.join([
        '6. What to Do Next', 'Suggested discussion steps, not prescriptions.',
        *(f'{number}. {step}' for number, step in enumerate(NEXT_STEPS, 1)),
        VALIDATION_CAUTION, '', '7. Limitations',
    ])
    text = text.replace('6. Limitations', next_section, 1)
    return '\n'.join([
        SYNTHETIC_LABEL,
        'Survey results are signals and hypotheses only. They do not establish causes.',
        'No causal inference is performed.', '', text,
        '- ' + MISSING_ITEMS_CAUTION,
    ])



def item_rows(records, stronger):
    """Present existing rankings without rescoring or introducing thresholds."""
    return [
        {
            'Q12 Item': record.item_id,
            'Mean Score': record.mean_score,
            'Respondent Count': record.respondent_count,
            'Plain-Language Interpretation': (
                f'A relatively stronger signal concerning {ITEM_TOPICS[record.item_id]} within this team and period.'
                if stronger else
                f'A relatively lower-scoring signal concerning {ITEM_TOPICS[record.item_id]}; explore team experiences.'
            ),
        }
        for record in records
    ]


def hierarchy_chart_spec(report):
    """Show the full valid response scale, with bars explicitly based at 1."""
    return {
        'description': 'Hierarchy mean scores on the complete 1–5 survey scale. Bars start at 1, the minimum valid response.',
        'data': {'values': [
            {'area': area, 'score': score}
            for area, score in report.hierarchy_scores.items() if score is not None
        ]},
        'height': 300,
        'mark': {'type': 'bar', 'color': '#285D7A', 'clip': True},
        'encoding': {
            'x': {'field': 'area', 'type': 'nominal',
                  'sort': list(report.hierarchy_scores),
                  'axis': {'title': 'Engagement Hierarchy Area', 'labelAngle': 0}},
            'y': {'field': 'score', 'type': 'quantitative',
                  'scale': {'domain': [1, 5], 'zero': False, 'nice': False},
                  'axis': {'title': 'Mean Score (1–5)', 'values': [1, 2, 3, 4, 5]}},
            'y2': {'datum': 1},
            'tooltip': [
                {'field': 'area', 'type': 'nominal', 'title': 'Hierarchy Area'},
                {'field': 'score', 'type': 'quantitative', 'title': 'Mean Score', 'format': '.2f'},
            ],
        },
    }


def main():
    st.set_page_config(page_title='AlignAgent — Tool 2', layout='wide')
    st.title('AlignAgent — Organizational Communication Diagnostic')
    st.write('Explore communication-related signals from aggregated Q12-style team survey results.')
    st.info(SYNTHETIC_LABEL)
    st.warning('Survey results are signals and hypotheses only. They do not establish causes.')

    with st.sidebar:
        st.header('How this prototype works')
        st.write('Aggregated Q12-style data → validation → hierarchy summaries → relative strengths and areas for investigation → provisional communication signal mapping → manager discussion questions')
        st.caption('Mappings are provisional and need evidence review. No benchmark percentile is inferred. No LLM or RAG is used.')
        with st.expander('Methodology'):
            st.write('Aggregated survey data → validation → Q12 hierarchy analysis → relative team-level patterns → provisional communication mapping → manager discussion prompts')
            st.write('No causal inference is performed.')

    try:
        reports = analyze_csv(SAMPLE_PATH)
    except (ValueError, OSError) as error:
        st.error(f'Unable to load the synthetic demonstration data: {error}')
        st.stop()

    team_id = st.selectbox('Team ID', list(dict.fromkeys(r.team_id for r in reports)))
    team_reports = [r for r in reports if r.team_id == team_id]
    if len(team_reports) > 1:
        period = st.selectbox('Period', [r.period for r in team_reports],
                              format_func=lambda value: value or 'Not supplied')
        report = next(r for r in team_reports if r.period == period)
    else:
        report = team_reports[0]

    st.header('Executive Summary')
    st.write(f'**Team ID:** {report.team_id}')
    st.write(f'**Period:** {report.period or "Not supplied"}')
    st.metric('GrandMean', f'{report.grand_mean:.2f} / 5')
    left, right = st.columns(2)
    left.write('**Strongest Hierarchy Area**')
    left.write(', '.join(report.hierarchy_strengths))
    right.write('**Main Hierarchy Area for Investigation**')
    right.write(', '.join(report.hierarchy_opportunities))
    st.write(executive_narrative(report))
    st.caption('Areas are relative within this team and period. All tied hierarchy areas are listed.')

    st.header('Hierarchy Profile')
    cards = st.columns(len(report.hierarchy_scores))
    for card, (area, score) in zip(cards, report.hierarchy_scores.items()):
        card.metric(area, f'{score:.2f} / 5' if score is not None else 'Unavailable')
    st.vega_lite_chart(hierarchy_chart_spec(report))
    st.caption('Scores are team-level averages from synthetic survey data. The chart shows the full 1–5 response scale; bars start at 1, the minimum valid score. Missing areas are not plotted or imputed.')

    for title, records, stronger in (
        ('Stronger Signals', report.strengths, True),
        ('Areas for Investigation', report.opportunities, False),
    ):
        st.header(title)
        st.dataframe(item_rows(records, stronger), hide_index=True,
                     column_config={'Mean Score': st.column_config.NumberColumn(format='%.2f')})

    st.header('Communication Signals to Explore')
    if not report.communication_signals:
        st.info('No mapped items in the lower-scoring selection.')
    for signal in report.communication_signals:
        name = signal.signal_name.replace('_', ' ').title()
        with st.expander(f'{name} — {signal.source_q12_item}'):
            st.subheader(name)
            st.write(f'**Source Q12 item:** {signal.source_q12_item}')
            st.write(f'**Observed score:** {signal.observed_score:.2f} / 5')
            st.write(f'**Relationship type:** {signal.relationship_type}')
            st.write(f'**Evidence status:** {signal.evidence_status.replace("_", " ")}')
            st.caption(f'Confidence: {signal.confidence_status}')
            st.write(f'**Interpretation:** {signal.interpretation}')
            st.warning(signal.caution)
            st.subheader('Questions to discuss with the team')
            for number, question in enumerate(signal.manager_questions, 1):
                st.write(f'{number}. {question}')

    st.header('Recommended Conversation Priorities')
    st.write('Conversation priorities to explore with the team.')
    st.caption('These are discussion prompts, not prescriptions.')
    priorities = conversation_priorities(report)
    for priority in priorities:
        st.write(f'- {priority}')
    if not priorities:
        st.info('No communication signals selected; no signal-based conversation priorities generated.')

    st.header('What to Do Next')
    st.caption('Suggested discussion steps, not prescriptions.')
    for number, step in enumerate(NEXT_STEPS, 1):
        st.write(f'{number}. {step}')
    st.info(VALIDATION_CAUTION)

    with st.expander('Limitations', expanded=True):
        for limitation in report.limitations:
            st.write(f'- {limitation}')
        st.write('- ' + MISSING_ITEMS_CAUTION)
        if report.missing_items:
            st.write('**Missing items:** ' + ', '.join(report.missing_items))

    st.download_button(
        'Download Diagnostic Summary',
        data=diagnostic_summary_text(report),
        file_name='alignagent-diagnostic-summary.txt',
        mime='text/plain; charset=utf-8',
    )


if __name__ == '__main__':
    main()
