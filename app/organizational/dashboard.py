"""Local presentation layer. Run: streamlit run app/organizational/dashboard.py."""
from html import escape
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


# Concise presentation labels only; these do not define communication mappings.
ITEM_LABELS = {
    'Q01': 'Expectations & Direction', 'Q02': 'Information & Resources',
    'Q03': 'Use of Strengths', 'Q04': 'Recognition', 'Q05': 'Care & Support',
    'Q06': 'Development Support', 'Q07': 'Employee Voice',
    'Q08': 'Purpose Connection', 'Q09': 'Quality & Team Standards',
    'Q10': 'Close Workplace Relationships', 'Q11': 'Progress Feedback',
    'Q12': 'Learning & Growth',
}


def evidence_display_label(status):
    """Translate internal status text without modifying stored evidence values."""
    if status in ('needs_review', 'provisional_needs_evidence_review'):
        return 'Evidence review pending'
    return status.replace('_', ' ').capitalize()


DASHBOARD_CSS = """
<style>
:root { --aa-navy:#17365D; --aa-blue:#2F75B5; --aa-teal:#2E8B8B;
 --aa-text:#243042; --aa-secondary:#667085; }
.stApp { background:#F7F9FC; color:var(--aa-text); }
.block-container { max-width:1440px; padding-top:3.75rem; padding-bottom:2rem; }
h1,h2,h3 { color:var(--aa-navy); letter-spacing:-.02em; }
h1 { font-size:1.4rem !important; font-weight:650; margin:0; padding:.2rem 0; }
.st-key-page-title h2 { font-size:clamp(1.8rem,3vw,2.5rem); line-height:1.18;
 padding:.15rem 0 .4rem; margin:0; }
[data-testid="stHeadingWithActionElements"] h2 { scroll-margin-top:4rem; }
[data-testid="stHeadingWithActionElements"]:has(h2) { margin-top:1rem; }
.st-key-page-title [data-testid="stHeadingWithActionElements"] { margin-top:0; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color:#526174 !important; font-size:.9rem; line-height:1.5; }
.st-key-causal-caution [data-testid="stAlert"] p,
.st-key-validation-callout [data-testid="stAlert"] p { color:#243042 !important; opacity:1; }
.st-key-causal-caution [data-testid="stAlert"] { background:#EEF4FA; color:#243042;
 border-left:3px solid #2F75B5; padding:.7rem 1rem; }
.st-key-validation-callout [data-testid="stAlert"] { background:#EAF4F4;
 color:#17365D; border-left:4px solid #2E8B8B; font-weight:600; }
[class*="st-key-signal-direct-"] [data-testid="stExpander"] { border-left:4px solid #2E8B8B; }
[class*="st-key-signal-partial-"] [data-testid="stExpander"] { border-left:4px solid #647B93; }
[class*="st-key-signal-indirect-"] [data-testid="stExpander"] { border-left:4px solid #D9A441; }
[class*="st-key-signal-"] [data-testid="stExpander"] summary { font-weight:600; line-height:1.6; }
.aa-priority { padding:1rem 1.15rem; }
.aa-priority h3 { font-size:1.1rem; line-height:1.35; margin:.65rem 0 .3rem; padding:0; }
.aa-priority p { margin:.35rem 0 0; }
.aa-item-title { font-size:1.08rem; line-height:1.4; font-weight:600; color:#17365D;
 margin:.8rem 0 .4rem; }
[data-testid="stHeader"] { background:#F7F9FC; }
[data-testid="stSidebar"] { background:#EEF4FA; }
[data-testid="stSidebar"] .block-container { padding-top:1.5rem; }
[data-testid="stVerticalBlock"] { gap:1rem; }
[data-testid="stExpander"] { background:white; border:1px solid #DCE4ED;
 border-radius:14px; box-shadow:0 2px 8px #17365D06; margin-bottom:.4rem; }
[data-testid="stExpander"] summary { padding:.95rem; color:var(--aa-navy); }
[data-testid="stExpander"] summary code { background:#EEF4FA; color:#17365D;
 border-radius:20px; padding:.2rem .5rem; font-size:.85rem; }
.aa-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1rem; }
.aa-grid-four { grid-template-columns:repeat(4,minmax(0,1fr)); }
.aa-card { background:white; padding:1.25rem; border-radius:14px;
 box-shadow:0 2px 10px #17365D08; min-width:0; border-top:3px solid #2F75B5; }
.aa-card.green { border-top-color:#4F8A5B; }
.aa-card.gold { border-top-color:#D9A441; }
.aa-card.teal { border-top-color:#2E8B8B; }
.aa-card.gray { border-top-color:#526174; }
.aa-label { color:#526174; font-size:.9rem; margin-bottom:.55rem; }
.aa-value { color:#17365D; font-size:1.65rem; font-weight:650; line-height:1.25;
 overflow-wrap:anywhere; margin-bottom:.5rem; }
.aa-card p { font-size:.94rem; line-height:1.55; margin:.7rem 0 0; }
.aa-badge { display:inline-block; border-radius:20px; padding:.25rem .6rem;
 background:#EEF4FA; color:#17365D; font-size:.82rem; font-weight:600; }
.aa-badge.green { background:#EEF6F0; color:#31583A; }
.aa-badge.gold { background:#FFF7E6; color:#76530E; }
.aa-badge.teal { background:#EAF4F4; color:#215F5F; }
.aa-badge.gray { background:#EEF1F5; color:#455468; }
.aa-score { font-size:1.8rem; font-weight:650; color:#17365D; margin:.6rem 0; }
.aa-score small { font-size:.9rem; color:#526174; font-weight:400; }
.aa-scale { display:flex; justify-content:space-between; font-size:.82rem; color:#526174; }
.aa-card meter { appearance:none; -webkit-appearance:none; width:100%; height:.8rem; display:block; margin:.6rem 0 .3rem; }
.aa-card meter::-webkit-meter-bar { background:#E7EDF3; border:0; border-radius:10px; }
.aa-card meter::-webkit-meter-optimum-value { background:#2F75B5; border-radius:10px; }
.aa-card.green meter::-webkit-meter-optimum-value { background:#4F8A5B; }
.aa-card.gold meter::-webkit-meter-optimum-value { background:#D9A441; }
.aa-card.teal meter::-webkit-meter-optimum-value { background:#2E8B8B; }
.aa-card meter::-moz-meter-bar { background:#2F75B5; }
.aa-card.teal meter::-moz-meter-bar { background:#2E8B8B; }
.aa-card.green meter::-moz-meter-bar { background:#4F8A5B; }
.aa-card.gold meter::-moz-meter-bar { background:#D9A441; }
.aa-step { display:flex; gap:.8rem; align-items:flex-start; margin:.8rem 0; }
.aa-number { background:#EEF4FA; color:#17365D; border-radius:50%; min-width:2rem;
 height:2rem; text-align:center; line-height:2rem; font-weight:600; }
.aa-step p { margin:.2rem 0; }
.aa-footer { color:#526174; font-size:.85rem; border-top:1px solid #DCE4ED;
 padding-top:1.25rem; margin-top:2rem; }
@media(max-width:1000px) { .aa-grid-four { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media(max-width:650px) { .aa-grid,.aa-grid-four { grid-template-columns:1fr; }
 .block-container { padding-top:1.5rem; } }
</style>
"""


def _card_grid(cards, four=False):
    """Render escaped display content in a responsive presentation-only grid."""
    st.markdown('<div class="aa-grid' + (' aa-grid-four' if four else '') + '">' +
                ''.join(cards) + '</div>', unsafe_allow_html=True)


def signal_cards(records, stronger):
    """Present the same ranked item rows as compact cards."""
    tone = 'green' if stronger else 'gold'
    badge = 'Stronger signal' if stronger else 'Area to explore'
    cards = []
    for row in item_rows(records, stronger):
        cards.append(
            f'<article class="aa-card {tone}"><span class="aa-badge {tone}">{badge}</span>'
            f'<div class="aa-item-title">{escape(row["Q12 Item"])} — {escape(ITEM_LABELS[row["Q12 Item"]])}</div>'
            f'<div class="aa-score">{row["Mean Score"]:.2f} <small>/ 5</small></div>'
            f'<div class="aa-label">Respondents: {row["Respondent Count"]}</div>'
            f'<p>{escape(row["Plain-Language Interpretation"])}</p></article>'
        )
    _card_grid(cards)


def main():
    st.set_page_config(page_title='AlignAgent — Tool 2', layout='wide')
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)
    st.markdown('<span class="aa-badge">Prototype</span>', unsafe_allow_html=True)
    st.title('AlignAgent')
    with st.container(key='page-title'):
        st.header('Organizational Communication Diagnostic')
    st.write('Translate aggregated engagement survey results into structured communication signals and manager discussion prompts.')
    st.caption('Uses synthetic Q12-style demonstration data.')
    with st.container(key='causal-caution'):
        st.warning('Survey results are signals and hypotheses only. They do not establish causes.')

    try:
        reports = analyze_csv(SAMPLE_PATH)
    except (ValueError, OSError) as error:
        st.error(f'Unable to load the synthetic demonstration data: {error}')
        st.stop()

    with st.sidebar:
        st.header('Select Team')
        team_id = st.selectbox('Team ID', list(dict.fromkeys(r.team_id for r in reports)))
        team_reports = [r for r in reports if r.team_id == team_id]
        if len(team_reports) > 1:
            period = st.selectbox('Period', [r.period for r in team_reports],
                                  format_func=lambda value: value or 'Not supplied')
            report = next(r for r in team_reports if r.period == period)
        else:
            report = team_reports[0]
        with st.expander('Methodology'):
            st.write('How this prototype works')
            st.write('Aggregated survey data → validation → Q12 hierarchy analysis → relative team-level patterns → provisional communication mapping → manager discussion prompts')
            st.write('No causal inference is performed.')
            st.caption('Mappings are provisional and need evidence review. No benchmark percentile is inferred. No LLM or RAG is used.')
        with st.expander('Data Disclosure'):
            st.info(SYNTHETIC_LABEL)
            st.caption('The bundled dataset contains fictional teams and invented scores for demonstration only.')
        with st.expander('Limitations'):
            st.write('Results are relative to each team and period. Small groups may create privacy risks; no suppression policy is implemented.')
            st.caption('See Methodology & Limitations below for the full cautions.')

    st.header('Executive Summary')
    st.caption(f'Team ID: {report.team_id} · Period: {report.period or "Not supplied"}')
    summary_cards = [
        ('GrandMean', f'{report.grand_mean:.2f} / 5', 'Available item means', ''),
        ('Strongest Hierarchy Area', ', '.join(report.hierarchy_strengths), 'Relative stronger signal', 'green'),
        ('Primary Area to Explore', ', '.join(report.hierarchy_opportunities), 'Area for investigation', 'gold'),
        ('Team', report.team_id.removeprefix('SYNTHETIC_'), 'Synthetic demonstration team', 'teal'),
    ]
    _card_grid([
        f'<article class="aa-card {tone}"><div class="aa-label">{escape(label)}</div>'
        f'<div class="aa-value">{escape(value)}</div><div class="aa-label">{escape(note)}</div></article>'
        for label, value, note, tone in summary_cards
    ], four=True)
    st.write(executive_narrative(report))
    st.caption('Areas are relative within this team and period. All tied hierarchy areas are listed.')

    st.header('Hierarchy Profile')
    hierarchy_cards = []
    for area, score in report.hierarchy_scores.items():
        strongest = area in report.hierarchy_strengths
        investigate = area in report.hierarchy_opportunities
        tone = 'gold' if investigate else 'green' if strongest else 'teal'
        label = ('Tied across areas' if strongest and investigate else
                 'Area to explore' if investigate else 'Strongest area' if strongest else 'Hierarchy area')
        score_html = f'{score:.2f} <small>/ 5</small>' if score is not None else '<small>Unavailable</small>'
        meter = (f'<meter min="1" max="5" value="{score}" aria-label="{escape(area)}: {score:.2f} out of 5">{score:.2f} out of 5</meter>'
                 if score is not None else '')
        hierarchy_cards.append(
            f'<article class="aa-card {tone}"><div class="aa-label">{escape(area)}</div>'
            f'<div class="aa-score">{score_html}</div>{meter}'
            f'<div class="aa-scale"><span>1</span><span>Mean score (1–5)</span><span>5</span></div>'
            f'<p><span class="aa-badge {tone}">{label}</span></p></article>'
        )
    _card_grid(hierarchy_cards, four=True)
    st.caption('Scores are aggregated team-level means from synthetic demonstration data.')
    st.caption('Bars show the full valid 1–5 scale, starting at 1. Missing areas are unavailable and are not imputed. Tied areas are labeled explicitly.')

    st.header('Stronger Signals')
    st.caption('Relative strengths within this team and period.')
    signal_cards(report.strengths, True)
    st.header('Areas for Investigation')
    st.caption('Relatively lower-scoring items to discuss with the team.')
    signal_cards(report.opportunities, False)

    st.header('Communication Signals to Explore')
    st.caption('Open a signal to explore the interpretation and questions. Relationships are provisional associations, not causal explanations.')
    if not report.communication_signals:
        st.info('No mapped items in the lower-scoring selection.')
    for signal_index, signal in enumerate(report.communication_signals):
        name = signal.signal_name.replace('_', ' ').title()
        evidence = evidence_display_label(signal.evidence_status)
        tone = {'direct': 'teal', 'partial': 'gray', 'indirect': 'gold'}.get(signal.relationship_type, 'gray')
        with st.container(key=f'signal-{signal.relationship_type}-{signal_index}'):
            with st.expander(f'{name} · {signal.source_q12_item} · {signal.observed_score:.2f} / 5 · `{signal.relationship_type}` · `{evidence}`'):
                st.markdown(
                    f'<span class="aa-badge {tone}">{escape(signal.relationship_type)} relationship</span> '
                    f'<span class="aa-badge gray">Evidence: {escape(evidence)}</span>',
                    unsafe_allow_html=True,
                )
                st.subheader(name)
                st.write(f'**Source Q12 item:** {signal.source_q12_item}')
                st.write(f'**Observed score:** {signal.observed_score:.2f} / 5')
                st.write(f'**Relationship type:** {signal.relationship_type}')
                st.write(f'**Evidence status:** {evidence}')
                st.caption(f'Confidence: {signal.confidence_status}')
                st.write(f'**Interpretation:** {signal.interpretation}')
                st.warning(signal.caution)
                st.subheader('Questions to discuss with the team')
                for number, question in enumerate(signal.manager_questions, 1):
                    st.write(f'{number}. {question}')
    st.header('Conversation Priorities')
    st.caption('Topics to explore with the team — not prescriptions.')
    priorities = conversation_priorities(report)
    _card_grid([
        f'<article class="aa-card teal aa-priority"><span class="aa-badge">Discussion {number}</span>'
        f'<h3>Explore {escape(report.communication_signals[min(number - 1, len(report.communication_signals) - 1)].signal_name.replace("_", " "))}</h3>'
        f'<p>{escape(priority)}</p></article>'
        for number, priority in enumerate(priorities, 1)
    ])
    if not priorities:
        st.info('No communication signals selected; no signal-based conversation priorities generated.')

    st.header('What to Do Next')
    st.caption('Suggested discussion steps, not prescriptions.')
    step_titles = ('Review signals.', 'Discuss with team.', 'Ask follow-up questions.',
                   'Capture what you learn.', 'Decide whether action is needed.')
    st.markdown('<div class="aa-card">' + ''.join(
        f'<div class="aa-step"><span class="aa-number">{number}</span><div>'
        f'<strong>{escape(title)}</strong><p>{escape(step)}</p></div></div>'
        for number, (title, step) in enumerate(zip(step_titles, NEXT_STEPS), 1)
    ) + '</div>', unsafe_allow_html=True)
    with st.container(key='validation-callout'):
        st.info(VALIDATION_CAUTION)

    with st.expander('Methodology & Limitations'):
        st.write('Aggregated results describe signals, not causes. Communication mappings remain provisional and need evidence review.')
        for limitation in report.limitations:
            st.write(f'- {limitation}')
        st.write('- ' + MISSING_ITEMS_CAUTION)
        if report.missing_items:
            st.write('**Missing items:** ' + ', '.join(report.missing_items))

    st.download_button(
        'Download Diagnostic Summary', data=diagnostic_summary_text(report),
        file_name='alignagent-diagnostic-summary.txt', mime='text/plain; charset=utf-8', type='primary',
    )
    st.markdown('<footer class="aa-footer">AlignAgent prototype. Inspired by contemporary employee-engagement reporting practices. Not affiliated with or endorsed by Gallup.</footer>', unsafe_allow_html=True)


if __name__ == '__main__':
    main()
