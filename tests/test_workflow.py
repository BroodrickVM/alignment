from dataclasses import replace
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from app.organizational.analyzer import analyze_csv
from app.organizational.dashboard import SAMPLE_PATH
from app.organizational.evidence_validation import load_evidence_validation_matrix
from app.organizational.workflow import context_key, discussion_summary, prune_suppressed_notes

DASHBOARD=Path('app/organizational/dashboard.py')


def field(elements,label):
    return next(e for e in elements if e.label==label)


def test_export_preserves_separation_and_rejects_suppressed_or_wrong_signal():
    report=analyze_csv(SAMPLE_PATH)[0]
    item=report.communication_signals[0].source_q12_item
    matrix=load_evidence_validation_matrix()
    notes={'observations':'TEAM INPUT', 'reflection':'MANAGER VIEW', 'decision':'No action for now',
           'action':'Review again next month', 'owner':'Team lead','follow_up':'Next month'}
    before=report.to_dict()
    text=discussion_summary(report,item,matrix.get_by_source_item(item),notes)
    assert text.index('Employee observations') < text.index('TEAM INPUT') < text.index('Manager reflection') < text.index('MANAGER VIEW')
    assert 'No action for now' in text and 'not verified by the tool' in text
    assert 'do not establish causes' in text
    assert report.to_dict()==before
    with pytest.raises(ValueError,match='suppressed'):
        discussion_summary(replace(report,suppressed=True),item,None,notes)
    with pytest.raises(ValueError,match='available'):
        discussion_summary(report,'Q00',None,notes)
    other=next(v for v in matrix.validations if v.source_item!=item)
    with pytest.raises(ValueError,match='does not match'):
        discussion_summary(report,item,other,notes)


def test_session_save_signal_team_isolation_restore_clear_and_suppress():
    app=AppTest.from_file(str(DASHBOARD)).run(timeout=30)
    reports=analyze_csv(SAMPLE_PATH)
    report=reports[0]
    first=report.communication_signals[0].source_q12_item
    field(app.text_area,'Employee observations (non-identifying summary)').set_value('Employees described conflicting priorities.')
    field(app.text_area,'Manager reflection and alternative explanations').set_value('Check workload as well.')
    field(app.selectbox,'Next-step decision').select('No action for now')
    field(app.button,'Save notes in this session').click().run()
    assert not app.exception
    key=context_key(report,first)
    assert app.session_state['discussion_drafts'][key]['decision']=='No action for now'
    picker=field(app.selectbox,'Choose a signal to discuss')
    second=report.communication_signals[1].source_q12_item
    picker.set_value(second).run()
    assert field(app.text_area,'Employee observations (non-identifying summary)').value==''
    field(app.selectbox,'Choose a signal to discuss').set_value(first).run()
    assert field(app.text_area,'Employee observations (non-identifying summary)').value=='Employees described conflicting priorities.'
    app.sidebar.selectbox[0].select(reports[1].team_id).run()
    assert field(app.text_area,'Employee observations (non-identifying summary)').value==''
    app.sidebar.selectbox[0].select(report.team_id).run()
    assert field(app.text_area,'Manager reflection and alternative explanations').value=='Check workload as well.'
    field(app.button,'Clear saved notes for this signal').click().run()
    assert not app.exception
    assert key not in app.session_state['discussion_drafts']
    assert field(app.text_area,'Employee observations (non-identifying summary)').value==''
    field(app.text_area,'Employee observations (non-identifying summary)').set_value('TEMPORARY NOTE')
    field(app.button,'Save notes in this session').click().run()
    app.sidebar.number_input[0].set_value(10000).run()
    assert not app.exception
    assert not app.session_state['discussion_drafts']
    assert not app.text_area and not app.get('download_button')
    app.sidebar.number_input[0].set_value(5).run()
    assert field(app.text_area,'Employee observations (non-identifying summary)').value==''


def test_prune_preserves_other_period_and_no_note_leaks_between_sessions():
    report=analyze_csv(SAMPLE_PATH)[0]
    period2=replace(report,period='P2')
    key=context_key(report,'Q07'); other=context_key(period2,'Q07')
    state={'discussion_drafts':{key:{'observations':'hidden'},other:{'observations':'kept'}},
           'discussion_widget:'+key+':observations':'hidden'}
    prune_suppressed_notes(state,[replace(report,suppressed=True),period2])
    assert state=={'discussion_drafts':{other:{'observations':'kept'}}}
    first=AppTest.from_file(str(DASHBOARD)).run()
    field(first.text_area,'Employee observations (non-identifying summary)').set_value('PRIVATE SESSION NOTE')
    field(first.button,'Save notes in this session').click().run()
    second=AppTest.from_file(str(DASHBOARD)).run()
    assert not second.session_state['discussion_drafts']
    assert field(second.text_area,'Employee observations (non-identifying summary)').value==''
