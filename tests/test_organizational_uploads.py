"""Uploaded aggregates use the existing analyzer, privacy and follow-up paths."""
from io import BytesIO, StringIO
import csv

import pytest
from streamlit.testing.v1 import AppTest

from app.organizational.analyzer import analyze_csv
from app.organizational.dashboard import SAMPLE_PATH, diagnostic_summary_text
from app.organizational.data_inputs import analyze_uploaded_csv, csv_template
from app.organizational.action_plans import action_plans_for_report, load_action_plans
from app.tool_handoff import context_for_signal

DASHBOARD = 'app/organizational/dashboard.py'
HEADER = 'team_id,item_id,mean_score,respondent_count,period\n'
VALID = HEADER + 'North,Q01,2.5,10,2026-Q1\nNorth,Q02,3.5,10,2026-Q1\nSouth,Q07,3,12,2026-Q1\n'


def uploaded_app(monkeypatch, content):
    import streamlit as st
    monkeypatch.setattr(st, 'file_uploader', lambda *args, **kwargs: BytesIO(content) if content is not None else None)
    app = AppTest.from_file(DASHBOARD).run(timeout=30)
    app.radio[0].set_value('Upload CSV').run(timeout=30)
    return app


def test_sample_template_and_upload_match_existing_analysis():
    content = SAMPLE_PATH.read_bytes()
    uploaded = analyze_uploaded_csv(BytesIO(content))
    assert [r.to_dict() for r in uploaded] == [r.to_dict() for r in analyze_csv(SAMPLE_PATH)]
    assert [r.to_dict() for r in analyze_uploaded_csv(BytesIO(b'\xef\xbb\xbf' + content))] == [r.to_dict() for r in uploaded]
    template = list(csv.reader(StringIO(csv_template(SAMPLE_PATH))))
    sample = list(csv.reader(StringIO(SAMPLE_PATH.read_text())))
    assert template == sample[:4]
    assert len(analyze_uploaded_csv(BytesIO(csv_template(SAMPLE_PATH).encode()))) > 0


@pytest.mark.parametrize('content,expected', [
    (b'item_id,mean_score,respondent_count\nQ01,3,10\n', 'headers'),
    ((HEADER + 't,Q01,not-a-number,10,p\n').encode(), 'line 2'),
    ((HEADER + 't,Q01,6,10,p\n').encode(), 'mean_score'),
    ((HEADER + 't,Q13,3,10,p\n').encode(), 'item_id'),
    ((HEADER + 't,Q01,3,0,p\n').encode(), 'respondent_count'),
    ((HEADER + 't,Q01,3,-2,p\n').encode(), 'respondent_count'),
    ((HEADER + 't,Q01,3,2.5,p\n').encode(), 'line 2'),
    ((HEADER + ',Q01,3,10,p\n').encode(), 'team_id'),
    ((HEADER + 't,Q01,nan,10,p\n').encode(), 'mean_score'),
    ((HEADER + 't,Q01,3,10,p\nt,Q01,4,10,p\n').encode(), 'Duplicate'),
    ((HEADER + 't,Q01,3,10\n').encode(), 'number of columns'),
    ((HEADER + '"unterminated\n').encode(), 'Malformed CSV'),
    (b'\xff\xfe', 'UTF-8'),
    (b'', 'headers'),
    ((HEADER + 't,Q01,3,10,p,extra\n').encode(), 'number of columns'),
    (b'team_id,item_id,mean_score,respondent_count,email\nt,Q01,3,10,a@b.c\n', 'headers'),
])
def test_invalid_uploads_reuse_validation(content, expected):
    with pytest.raises(ValueError, match=expected):
        analyze_uploaded_csv(BytesIO(content))


def test_optional_period_and_threshold_are_unchanged():
    content = b'team_id,item_id,mean_score,respondent_count\nt,Q01,3,4\n'
    report, = analyze_uploaded_csv(BytesIO(content))
    assert report.period is None and report.suppressed
    assert report.grand_mean is None and not report.communication_signals
    assert action_plans_for_report(report, load_action_plans()) == ()
    with pytest.raises(ValueError, match='Suppressed'):
        context_for_signal(report, 'Q01')
    report, = analyze_uploaded_csv(BytesIO(content), minimum_responses=4)
    assert not report.suppressed and report.grand_mean == 3


def test_upload_mode_exists_and_waits_without_using_demo():
    app = AppTest.from_file(DASHBOARD).run(timeout=30)
    assert not app.exception
    assert app.radio[0].options == ['Use demonstration data', 'Upload CSV']
    app.radio[0].set_value('Upload CSV').run(timeout=30)
    assert not app.exception
    assert len(app.get('file_uploader')) == 1
    assert app.get('file_uploader')[0].label == 'Upload Q12-style survey results'
    assert not app.sidebar.selectbox
    assert any(b.label == 'Download CSV template' for b in app.get('download_button'))
    assert 'Executive Summary' not in [h.value for h in app.header]
    assert any('Do not upload employee names' in info.value for info in app.info)


def test_uploaded_teams_labels_download_actions_and_handoff(monkeypatch):
    import streamlit as st
    reports = analyze_uploaded_csv(BytesIO(VALID.encode()))
    app = uploaded_app(monkeypatch, VALID.encode())
    assert not app.exception
    assert app.sidebar.selectbox[0].options == ['North', 'South']
    for report in reports:
        app.sidebar.selectbox[0].select(report.team_id).run(timeout=30)
        assert not app.exception
        assert 'Suggested Manager Actions' in [h.value for h in app.header]
        assert 'Why these Q12-style items?' in [e.label for e in app.expander]
        assert 'Uploaded dataset' in [c.value for c in app.caption]
        assert not any('Synthetic demonstration' in i.value for i in app.info)
        text = '\n'.join(m.value for m in app.markdown)
        assert f'{report.grand_mean:.2f} / 5' in text
        for action in action_plans_for_report(report, load_action_plans()):
            assert action.plan.suggested_action in text
        summary = diagnostic_summary_text(report, 'Uploaded dataset')
        assert summary.startswith('Uploaded dataset\n')
        assert 'Synthetic demonstration data' not in summary
    destinations = []
    monkeypatch.setattr(st, 'switch_page', lambda page: destinations.append(page))
    selected = reports[-1].communication_signals[0]
    next(b for b in app.button if b.key == f'prepare-message-{selected.source_q12_item}').click().run()
    assert not app.exception
    assert destinations[-1].title == 'Tool 1 — Message Coach'
    assert app.session_state['tool2_message_context']['source_item'] == selected.source_q12_item
    # Switching back to demonstration mode still runs its original dataset.
    app.radio[0].set_value('Use demonstration data').run(timeout=30)
    assert not app.exception
    assert app.sidebar.selectbox[0].options == [r.team_id for r in analyze_csv(SAMPLE_PATH)]


def test_invalid_ui_upload_stops_and_explains_error(monkeypatch):
    app = uploaded_app(monkeypatch, (HEADER + 't,Q01,bad,10,p\n').encode())
    assert not app.exception
    assert any('line 2' in e.value for e in app.error)
    assert not app.sidebar.selectbox
    assert 'Executive Summary' not in [h.value for h in app.header]
    assert not any(b.label == 'Prepare communication in Message Coach' for b in app.button)


def test_uploaded_suppression_has_no_scores_actions_or_download(monkeypatch):
    app = uploaded_app(monkeypatch, (HEADER + 't,Q01,3,1,p\n').encode())
    assert not app.exception
    assert any('suppressed' in w.value for w in app.warning)
    assert 'Executive Summary' not in [h.value for h in app.header]
    assert not any(b.label == 'Prepare communication in Message Coach' for b in app.button)
    assert [b.label for b in app.get('download_button')] == ['Download CSV template']


def test_uploaded_discussion_summary_uses_correct_disclosure():
    from app.organizational.workflow import discussion_summary
    report = analyze_uploaded_csv(BytesIO(VALID.encode()))[0]
    text = discussion_summary(report, 'Q01', None, {}, dataset_label='Uploaded dataset')
    assert 'Uploaded dataset' in text
    assert 'Synthetic demonstration data' not in text
    assert 'does not establish causes' in text
