"""Session-only manager discussion notes; never changes diagnostic judgments."""
import json

OUTCOMES = ('Not assessed', 'Supports the hypothesis', 'Mixed or unclear', 'Suggests another explanation')
DECISIONS = ('Investigate further', 'Agree on an action', 'No action for now')


def context_key(report, item):
    return json.dumps([report.team_id, report.period, item], ensure_ascii=True)


def selected_signal(report, item):
    if report.suppressed:
        raise ValueError('Discussion workflow is unavailable for suppressed results.')
    signal = next((s for s in report.communication_signals if s.source_q12_item == item), None)
    if signal is None:
        raise ValueError('Select an available communication signal.')
    return signal


def discussion_summary(report, item, validation, notes):
    signal = selected_signal(report, item)
    if validation is not None and validation.source_item != item:
        raise ValueError('Evidence record does not match the selected signal.')
    lines = [
        'AlignAgent — Manager Discussion Guide and Follow-up',
        'Synthetic demonstration data — not real Gallup results.',
        f'Team: {report.team_id}', f'Period: {report.period or "Not supplied"}',
        f'Minimum reporting threshold: {report.minimum_responses} responses per supplied item.',
        '', '1. Observed survey signal',
        f'{item} — {signal.signal_name.replace("_", " ").title()}: {signal.observed_score:.2f} / 5',
        'Selected from relative within-team results; ties can include additional signals.',
        '', '2. Hypothesis and evidence limits', signal.interpretation, signal.caution,
        'This guide does not establish causes or validate a communication diagnosis.',
    ]
    if validation:
        lines.extend([f'Preliminary mapping review: {validation.validation_status}',
                      'Suggested discussion framing: ' + validation.allowed_language,
                      'Research source: ' + validation.external_source_reference,
                      'Review limits: ' + validation.review_notes])
    lines.extend(['', '3. Questions for discussion', *[f'- {q}' for q in signal.manager_questions],
                  '', '4. Employee observations — manager-entered, not verified by the tool',
                  notes.get('observations', '') or 'Not recorded.',
                  'How observations relate to the hypothesis: ' + notes.get('outcome', 'Not assessed'),
                  '', '5. Manager reflection — separate from employee observations',
                  notes.get('reflection', '') or 'Not recorded.',
                  '', '6. Next step — manager-entered, not a tool prescription',
                  'Decision: ' + notes.get('decision', 'Investigate further'),
                  notes.get('action', '') or 'No next-step details recorded.',
                  'Responsible role: ' + (notes.get('owner', '') or 'Not recorded.'),
                  'Follow-up date or timing: ' + (notes.get('follow_up', '') or 'Not recorded.'),
                  '', '7. Reporting cautions', *report.limitations,
                  'Use non-identifying summaries. Session notes are not a durable record; downloads are saved by the user.'])
    return '\n'.join(lines)


def prune_suppressed_notes(state, reports):
    """Remove saved and widget notes for any group now suppressed by policy."""
    blocked = {(r.team_id, r.period) for r in reports if r.suppressed}
    drafts = state.get('discussion_drafts', {})
    for key in list(drafts):
        team, period, _ = json.loads(key)
        if (team, period) in blocked:
            del drafts[key]
    for key in list(state):
        if key.startswith('discussion_widget:'):
            context = key[len('discussion_widget:'):].rsplit(':', 1)[0]
            team, period, _ = json.loads(context)
            if (team, period) in blocked:
                del state[key]


def render_workflow(report, matrix):
    import streamlit as st
    if report.suppressed:
        return
    st.header('Manager Discussion Workflow')
    st.caption('Notes are kept only in this browser session. They may be lost on reload, disconnection or restart. Save in session before downloading. Use non-identifying summaries; avoid names and sensitive personal details.')
    if not report.communication_signals:
        st.info('No communication signals are selected for this team/period, so no signal-based guide is available.')
        return
    group = json.dumps([report.team_id, report.period])
    item = st.selectbox('Choose a signal to discuss',
                        [s.source_q12_item for s in report.communication_signals],
                        format_func=lambda i: i + ' — ' + selected_signal(report, i).signal_name.replace('_', ' ').title(),
                        key='discussion_signal:' + group)
    signal = selected_signal(report, item)
    validation = matrix.get_by_source_item(item)
    key = context_key(report, item)
    drafts = st.session_state.setdefault('discussion_drafts', {})
    saved = drafts.get(key, {})
    st.subheader('Discussion guide')
    st.write(f'Observed {item} score: {signal.observed_score:.2f} / 5. This is a relative signal, not a causal explanation.')
    if validation:
        st.write('Suggested discussion framing: ' + validation.allowed_language)
        st.caption('Preliminary review: ' + validation.validation_status.replace('_', ' ') + '. ' + validation.review_notes)
    st.warning(signal.caution)
    for question in signal.manager_questions:
        st.write('- ' + question)
    with st.form('discussion_form:' + key):
        prefix = 'discussion_widget:' + key + ':'
        observations = st.text_area('Employee observations (non-identifying summary)', value=saved.get('observations', ''), key=prefix+'observations')
        outcome = st.selectbox('How do these observations relate to the hypothesis?', OUTCOMES,
                              index=OUTCOMES.index(saved.get('outcome', OUTCOMES[0])), key=prefix+'outcome')
        reflection = st.text_area('Manager reflection and alternative explanations', value=saved.get('reflection', ''), key=prefix+'reflection')
        decision = st.selectbox('Next-step decision', DECISIONS,
                               index=DECISIONS.index(saved.get('decision', DECISIONS[0])), key=prefix+'decision')
        action = st.text_area('Agreed next step or reason for taking no action', value=saved.get('action', ''), key=prefix+'action')
        owner = st.text_input('Responsible role (avoid personal names)', value=saved.get('owner', ''), key=prefix+'owner')
        follow_up = st.text_input('Follow-up date or timing', value=saved.get('follow_up', ''), key=prefix+'follow_up')
        if st.form_submit_button('Save notes in this session'):
            drafts[key] = dict(observations=observations, outcome=outcome, reflection=reflection,
                               decision=decision, action=action, owner=owner, follow_up=follow_up)
            st.success('Notes saved in this session. Download the summary to keep a copy.')
    if st.button('Clear saved notes for this signal', key='discussion_clear:' + key):
        drafts.pop(key, None)
        for widget in list(st.session_state):
            if widget.startswith('discussion_widget:' + key + ':'):
                del st.session_state[widget]
        st.rerun()
    st.caption('The download includes the guide and last saved notes for this signal only. Unsaved edits are excluded.')
    st.download_button('Download Discussion Summary',
                       data=discussion_summary(report, item, validation, drafts.get(key, {})),
                       file_name='alignagent-discussion-summary.txt', mime='text/plain; charset=utf-8',
                       key='discussion_download:' + key)
