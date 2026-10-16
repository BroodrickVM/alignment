"""Presentation helpers and interactive dashboard regression checks."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.organizational import Q12Result, analyze_csv, analyze_results
from app.organizational.dashboard import SAMPLE_PATH, hierarchy_chart_spec, item_rows
from app.organizational.report import conversation_priorities

DASHBOARD = Path(__file__).resolve().parents[1] / 'app/organizational/dashboard.py'


def test_tables_preserve_scores_counts_order_and_report():
    report = analyze_csv(SAMPLE_PATH)[0]
    before = report.to_dict()
    for records, stronger in ((report.strengths, True), (report.opportunities, False)):
        rows = item_rows(records, stronger)
        assert [r['Q12 Item'] for r in rows] == [r.item_id for r in records]
        assert [r['Mean Score'] for r in rows] == [r.mean_score for r in records]
        assert [r['Respondent Count'] for r in rows] == [r.respondent_count for r in records]
        assert all('signal concerning' in r['Plain-Language Interpretation'] for r in rows)
    assert report.to_dict() == before


def test_chart_full_scale_and_missing_values():
    report, = analyze_results([Q12Result('t', 'Q01', 1, 10)])
    chart = hierarchy_chart_spec(report)
    assert chart['encoding']['y']['scale'] == {'domain': [1, 5], 'zero': False, 'nice': False}
    assert chart['encoding']['y2']['datum'] == 1
    assert chart['encoding']['x']['axis']['title'] == 'Engagement Hierarchy Area'
    assert chart['encoding']['y']['axis']['title'] == 'Mean Score (1–5)'
    assert chart['data']['values'] == [{'area': 'Basic Needs', 'score': 1.0}]


def test_dashboard_renders_and_team_selector_updates_all_outputs():
    reports = analyze_csv(SAMPLE_PATH)
    app = AppTest.from_file(str(DASHBOARD)).run(timeout=30)
    assert not app.exception
    assert app.title[0].value == 'AlignAgent — Organizational Communication Diagnostic'
    assert any('Synthetic demonstration data — not real Gallup results.' == info.value for info in app.info)
    assert app.warning[0].value == 'Survey results are signals and hypotheses only. They do not establish causes.'
    assert app.selectbox[0].options == [r.team_id for r in reports]
    for report in reports:
        app.selectbox[0].select(report.team_id).run(timeout=30)
        assert not app.exception
        assert app.metric[0].value == f'{report.grand_mean:.2f} / 5'
        assert [metric.value for metric in app.metric][1:] == [f'{score:.2f} / 5' for score in report.hierarchy_scores.values()]
        for table, records in zip(app.dataframe, (report.strengths, report.opportunities)):
            assert table.value['Q12 Item'].tolist() == [r.item_id for r in records]
            assert table.value['Mean Score'].tolist() == [r.mean_score for r in records]
        assert [e.label for e in app.expander if e.label not in ('Methodology', 'Limitations')] == [
            f'{s.signal_name.replace("_", " ").title()} — {s.source_q12_item}' for s in report.communication_signals
        ]
        text = '\n'.join(m.value for m in app.markdown)
        assert report.team_id in text
        assert report.period in text
        assert ', '.join(report.hierarchy_strengths) in text
        assert ', '.join(report.hierarchy_opportunities) in text
        for priority in conversation_priorities(report):
            assert priority in text
        for limitation in report.limitations:
            assert limitation in text
        for signal in report.communication_signals:
            assert signal.interpretation in text
            assert signal.caution in [w.value for w in app.warning]
            assert all(question in text for question in signal.manager_questions)
        assert 'Missing items are not imputed' in text
        assert 'How this prototype works' in [h.value for h in app.sidebar.header]
        assert 'What to Do Next' in [h.value for h in app.header]
        assert 'Validate the hypotheses with employees before taking action.' in [i.value for i in app.info]
        assert 'No causal inference is performed.' in '\n'.join(m.value for m in app.sidebar.markdown)
        assert 'Methodology' in [e.label for e in app.sidebar.expander]
        assert len(app.get('download_button')) == 1
        assert app.get('download_button')[0].label == 'Download Diagnostic Summary'
        from app.organizational.dashboard import executive_narrative, NEXT_STEPS
        assert executive_narrative(report) in text
        assert all(step in text for step in NEXT_STEPS)
        assert text.count('**Evidence status:** needs review') == len(report.communication_signals)


def test_download_contains_selected_team_sections_cautions_and_next_steps():
    from app.organizational.dashboard import (
        diagnostic_summary_text, executive_narrative, NEXT_STEPS, SYNTHETIC_LABEL,
    )
    reports = analyze_csv(SAMPLE_PATH)
    for report in reports:
        before = report.to_dict()
        text = diagnostic_summary_text(report)
        headings = (
            'Executive Summary', 'Hierarchy scores:', 'Stronger Signals',
            'Areas for Investigation', 'Communication Signals to Explore',
            'Recommended Conversation Priorities', 'What to Do Next', '7. Limitations',
        )
        positions = [text.index(heading) for heading in headings]
        assert positions == sorted(positions)
        assert SYNTHETIC_LABEL in text
        assert executive_narrative(report) in text
        assert 'No causal inference is performed.' in text
        assert 'Validate the hypotheses with employees before taking action.' in text
        assert all(step in text for step in NEXT_STEPS)
        assert all(limitation in text for limitation in report.limitations)
        for signal in report.communication_signals:
            assert signal.caution in text
            assert signal.interpretation in text
            assert all(question in text for question in signal.manager_questions)
        for other in reports:
            if other.team_id != report.team_id:
                assert other.team_id not in text
        assert report.to_dict() == before
        assert text == diagnostic_summary_text(report)


def test_narrative_handles_ties_and_no_mapped_signals_without_inventing_results():
    from app.organizational.dashboard import executive_narrative, diagnostic_summary_text
    report, = analyze_results([Q12Result('t', item, 3, 10) for item in ('Q03', 'Q10', 'Q12')])
    narrative = executive_narrative(report)
    assert 'Available hierarchy areas are tied' in narrative
    assert 'No mapped communication signals were selected' in narrative
    assert 'employee voice' not in narrative
    assert 'Missing items: Q01' in diagnostic_summary_text(report)
    assert 'No values were imputed' in diagnostic_summary_text(report)


def test_sample_narrative_uses_current_results():
    from app.organizational.dashboard import executive_narrative
    report = analyze_csv(SAMPLE_PATH)[0]
    assert executive_narrative(report) == (
        'This team shows relatively stronger signals in Teamwork, while Basic Needs '
        'is the primary hierarchy area for investigation. Communication-related signals '
        'suggest exploring employee voice, recognition communication and clarity of expectations.'
    )
