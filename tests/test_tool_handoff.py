"""A manager-controlled handoff must not bypass model consent or privacy."""
from copy import deepcopy
from dataclasses import asdict
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from app.organizational import Q12Result, analyze_csv, analyze_results
from app.organizational.dashboard import SAMPLE_PATH
from app.tool_handoff import (
    CONTEXT_KEY, PREFILL_KEY, clear_handoff, context_for_signal,
    drafting_scaffold, prepare_handoff,
)


def sample_report():
    return analyze_csv(SAMPLE_PATH)[0]


def coach(state=None):
    app = AppTest.from_string('from app.tool1.dashboard import main\nmain()')
    for key, value in (state or {}).items():
        app.session_state[key] = value
    return app.run(timeout=30)


def button(app, label):
    return next(b for b in app.button if b.label == label)


def prepared_state():
    report = sample_report()
    state = {}
    prepare_handoff(state, report, report.communication_signals[0].source_q12_item)
    return state


def test_context_only_copies_selected_signal_allowlist_and_preserves_report():
    for report in analyze_csv(SAMPLE_PATH):
        before = deepcopy(report.to_dict())
        for signal in report.communication_signals:
            context = context_for_signal(report, signal.source_q12_item)
            assert set(context) <= {'origin', 'source_item', 'dimension_id', 'dimension_name',
                                    'observed_score', 'interpretation', 'manager_questions',
                                    'suggested_action', 'suggested_timeline'}
            assert context['origin'] == 'tool2'
            assert context['source_item'] == signal.source_q12_item
            assert context['dimension_id'] == signal.signal_name
            assert context['observed_score'] == signal.observed_score
            assert context['manager_questions'] == signal.manager_questions
        assert report.to_dict() == before
        unselected = next(item for item in ('Q03', 'Q10', 'Q12') if item not in [s.source_q12_item for s in report.communication_signals])
        with pytest.raises(ValueError, match='Only selected'):
            context_for_signal(report, unselected)


def test_suppressed_report_cannot_create_context_or_change_state():
    report, = analyze_results([Q12Result('private', 'Q01', 2, 1)])
    state = {'manager_notes': 'sensitive observation'}
    with pytest.raises(ValueError, match='Suppressed'):
        prepare_handoff(state, report, 'Q01')
    assert state == {'manager_notes': 'sensitive observation'}


def test_prepare_and_clear_preserve_existing_work_and_exclude_notes():
    report = sample_report()
    item = report.communication_signals[0].source_q12_item
    saved = {'completed': 'review'}
    state = {'tool1_draft': 'My existing draft', 'tool1_result': saved,
             'manager_notes': 'employee observation', 'tool1_revision': 'My revision',
             'tool1_model_consent': True}
    prepare_handoff(state, report, item)
    assert state['tool1_draft'] == 'My existing draft'
    assert 'employee observation' not in str(state[CONTEXT_KEY])
    assert not state['tool1_model_consent']
    clear_handoff(state)
    assert state['tool1_result'] == saved
    assert state['tool1_revision'] == 'My revision'
    assert state['tool1_draft'] == 'My existing draft'
    assert CONTEXT_KEY not in state


def test_scaffold_has_only_editable_prompts_and_clear_removes_untouched_prefill():
    state = prepared_state()
    scaffold = state['tool1_draft']
    assert scaffold == drafting_scaffold(state[CONTEXT_KEY])
    assert 'Drafting notes' in scaffold
    assert '[What is the purpose of your message?]' in scaffold
    assert '[Add timing, responsibilities, or other details only if appropriate.]' in scaffold
    for claim in ('Friday', 'Monday', '2026', 'Hi team', 'will improve engagement'):
        assert claim not in scaffold
    clear_handoff(state)
    assert state['tool1_draft'] == ''
    assert CONTEXT_KEY not in state and PREFILL_KEY not in state
    state = prepared_state()
    state['tool1_draft'] = 'Edited by manager'
    clear_handoff(state)
    assert state['tool1_draft'] == 'Edited by manager'


def test_coach_panel_editing_clear_and_no_model_calls(monkeypatch):
    import app.tool1.judge as judge
    request = Mock(side_effect=AssertionError('Unexpected model request'))
    monkeypatch.setattr(judge, 'judge', request)
    state = prepared_state()
    app = coach(state)
    assert not app.exception
    assert 'Context from Team Diagnostic' in [h.value for h in app.subheader]
    text = '\n'.join(m.value for m in app.markdown)
    context = state[CONTEXT_KEY]
    assert context['dimension_name'] in text and context['source_item'] in text
    assert all(q in text for q in context['manager_questions'])
    assert 'not a causal diagnosis' in '\n'.join(i.value for i in app.info)
    assert app.text_area[0].value == state['tool1_draft']
    app.text_area[0].set_value('Manager edited draft').run()
    button(app, 'Clear Team Diagnostic context').click().run()
    assert not app.exception
    assert app.text_area[0].value == 'Manager edited draft'
    assert 'Context from Team Diagnostic' not in [h.value for h in app.subheader]
    request.assert_not_called()


def test_untouched_scaffold_and_missing_consent_block_evaluation(monkeypatch):
    import app.tool1.judge as judge
    request = Mock(side_effect=AssertionError('Unexpected model request'))
    monkeypatch.setattr(judge, 'judge', request)
    app = coach(prepared_state())
    app.checkbox[0].check()
    button(app, 'Evaluate draft').click().run()
    assert any('Edit the drafting scaffold' in e.value for e in app.error)
    app.text_area[0].set_value('Please review [topic] with the team.')
    app.checkbox[0].uncheck()
    button(app, 'Evaluate draft').click().run()
    assert any('Confirm the model submission' in e.value for e in app.error)
    request.assert_not_called()


def test_clearing_context_retains_completed_review():
    from app.tool1.judge import JudgeResult
    result = JudgeResult('task_instruction', 'task_instruction_v1.2', True, False, None,
                         {}, 'borderline', None, 'low', 'Mock only')
    state = prepared_state()
    state['tool1_result'] = {'draft': 'Completed draft', 'result': asdict(result)}
    app = coach(state)
    button(app, 'Clear Team Diagnostic context').click().run()
    assert not app.exception
    assert app.session_state['tool1_result'] == state['tool1_result']
    assert app.text_area[0].value == ''
    assert any(b.label == 'Download Message Review' for b in app.get('download_button'))


def test_independent_pages_overview_and_selected_controls():
    app = coach()
    assert not app.exception
    assert not any(h.value == 'Context from Team Diagnostic' for h in app.subheader)
    app = AppTest.from_file('app/organizational/dashboard.py').run(timeout=30)
    assert not app.exception
    assert [b.key for b in app.button if b.label == 'Prepare communication in Message Coach'] == [
        f'prepare-message-{s.source_q12_item}' for s in sample_report().communication_signals]
    app.sidebar.number_input[0].set_value(100).run()
    assert not app.exception
    assert not any(b.label == 'Prepare communication in Message Coach' for b in app.button)
    app = AppTest.from_file('streamlit_app.py').run(timeout=30)
    assert not app.exception
    text = '\n'.join(m.value for m in app.markdown)
    assert 'carry a selected focus area into Message Coach' in text
    assert 'Model evaluation requires explicit draft submission with consent' in text
    assert 'Nothing is automatically sent to employees' in text


def test_handoff_button_routes_to_existing_coach_without_request(monkeypatch):
    import streamlit as st
    import app.tool1.judge as judge
    request = Mock(side_effect=AssertionError('Unexpected model request'))
    monkeypatch.setattr(judge, 'judge', request)
    destinations = []
    monkeypatch.setattr(st, 'switch_page', lambda page: destinations.append(page))
    app = AppTest.from_file('app/organizational/dashboard.py').run(timeout=30)
    report = sample_report()
    before = deepcopy(report.to_dict())
    for signal in report.communication_signals:
        next(b for b in app.button if b.key == f'prepare-message-{signal.source_q12_item}').click().run()
        assert not app.exception
        context = app.session_state[CONTEXT_KEY]
        assert context['source_item'] == signal.source_q12_item
        assert destinations[-1].title == 'Tool 1 — Message Coach'
        assert destinations[-1].url_path == 'message-coach'
        target = coach({CONTEXT_KEY: context, 'tool1_draft': app.session_state['tool1_draft'],
                        PREFILL_KEY: app.session_state[PREFILL_KEY]})
        assert not target.exception
        assert 'Context from Team Diagnostic' in [h.value for h in target.subheader]
        button(target, 'Return to Team Diagnostic').click().run()
        assert not target.exception
        assert destinations[-1].title == 'Tool 2 — Team Diagnostic'
        assert destinations[-1].url_path == 'team-diagnostic'
    assert report.to_dict() == before
    request.assert_not_called()


def test_all_nine_dimensions_supply_specific_context():
    report, = analyze_results([Q12Result('t', f'Q{i:02}', 3, 10) for i in range(1, 13)])
    contexts = [context_for_signal(report, s.source_q12_item) for s in report.communication_signals]
    assert len(contexts) == 9
    assert len({c['dimension_id'] for c in contexts}) == 9
    assert len({c['manager_questions'] for c in contexts}) == 9
    for context in contexts:
        assert context['dimension_name'] in drafting_scaffold(context)
        assert 'provisional communication hypothesis' in context['interpretation']


def test_edited_draft_with_explicit_consent_uses_existing_pipeline(monkeypatch):
    import sys
    from types import ModuleType, SimpleNamespace
    from app.tool1.judge import JudgeResult
    import app.tool1.config as config
    pipeline = ModuleType('app.tool1.pipeline')
    result = JudgeResult('task_instruction', 'task_instruction_v1.2', True, False, None,
                         {}, 'borderline', None, 'low', 'Mock only')
    pipeline.run = Mock(return_value=SimpleNamespace(before=result, rewrite=None, after=None))
    monkeypatch.setitem(sys.modules, 'app.tool1.pipeline', pipeline)
    monkeypatch.setattr(config, 'load_settings', lambda: None)
    app = coach(prepared_state())
    pipeline.run.assert_not_called()
    draft = 'Please bring questions about our priorities to our next team discussion.'
    app.text_area[0].set_value(draft)
    app.checkbox[0].check()
    kind = app.selectbox[0].value
    button(app, 'Evaluate draft').click().run()
    assert not app.exception
    pipeline.run.assert_called_once_with(draft, kind)
    assert app.session_state['tool1_result']['draft'] == draft
