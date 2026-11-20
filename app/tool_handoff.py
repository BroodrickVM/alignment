"""Temporary, manager-controlled context; no model calls or diagnostic changes."""
from app.organizational.rubric import load_rubric
from importlib.util import find_spec

CONTEXT_KEY = 'tool2_message_context'
PREFILL_KEY = 'tool2_message_scaffold'


def context_for_signal(report, source_item):
    """Allowlist metadata from a selected, unsuppressed diagnostic signal only."""
    if report.suppressed:
        raise ValueError('Suppressed reports cannot provide Message Coach context.')
    signal = next((s for s in report.communication_signals if s.source_q12_item == source_item), None)
    if signal is None:
        raise ValueError('Only selected communication signals can provide context.')
    dimension = load_rubric().get_by_item(source_item)
    if dimension is None or dimension.dimension_id != signal.signal_name:
        raise ValueError('Selected signal has no matching communication dimension.')
    context = dict(origin='tool2', source_item=source_item,
                   dimension_id=dimension.dimension_id, dimension_name=dimension.dimension_name,
                   observed_score=signal.observed_score, interpretation=signal.interpretation,
                   manager_questions=tuple(signal.manager_questions))
    action = None
    if find_spec('app.organizational.action_plans') is not None:
        from app.organizational.action_plans import load_action_plans
        action = load_action_plans().get_by_source_item(source_item)
    if action is not None:
        context.update(suggested_action=action.suggested_action,
                       suggested_timeline=action.suggested_timeline)
    return context


def drafting_scaffold(context):
    return (f'Drafting notes — focus area: {context["dimension_name"]}\n\n'
            'Purpose: [What is the purpose of your message?]\n'
            'Discussion or invitation: [Which diagnostic question would you like to explore?]\n'
            'Information: [What does the team need to know?]\n'
            'Next step: [What action or discussion are you inviting?]\n'
            'Details: [Add timing, responsibilities, or other details only if appropriate.]')


def prepare_handoff(state, report, source_item):
    context = context_for_signal(report, source_item)
    previous = state.get(PREFILL_KEY)
    state[CONTEXT_KEY] = context
    if not state.get('tool1_draft') or state.get('tool1_draft') == previous:
        scaffold = drafting_scaffold(context)
        state['tool1_draft'] = scaffold
        state[PREFILL_KEY] = scaffold
    else:
        state.pop(PREFILL_KEY, None)
    # Consent applies to a submission, never to a new handoff.
    state['tool1_model_consent'] = False


def clear_handoff(state):
    scaffold = state.pop(PREFILL_KEY, None)
    if scaffold is not None and state.get('tool1_draft') == scaffold:
        state['tool1_draft'] = ''
    state.pop(CONTEXT_KEY, None)
