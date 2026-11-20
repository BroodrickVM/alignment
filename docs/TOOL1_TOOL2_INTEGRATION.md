# CommsAlign: Team Diagnostic to Message Coach

Run `streamlit run streamlit_app.py` after installing `requirements.txt` and
`requirements-tool1.txt`. The overview and both tools remain independently
accessible through the shared sidebar. Tool 2's standalone entry point also
remains available; cross-page navigation uses the shared app.

## Manager-controlled workflow

Team Diagnostic → selected communication signal → manager clicks **Prepare
communication in Message Coach** → session-state handoff → Message Coach drafting
context → manager edits draft and chooses message type → explicit consent and
submission → existing Tool 1 evaluation.

Only signals already selected by an unsuppressed diagnostic have handoff controls.
The handoff creates `st.session_state['tool2_message_context']` with an explicit
allowlist: `origin='tool2'`, `source_item`, `dimension_id`, `dimension_name`,
`observed_score`, `interpretation`, and `manager_questions`. When available,
`suggested_action` and `suggested_timeline` are included as discussion options.
No team identifier, employee names, manager observations, discussion notes,
manager decisions, personal information, secrets, or credentials are copied.
Context is temporary Streamlit session state, not durable storage or a new export.
It is not automatically appended to a model request: the existing evaluation
receives only the manager-submitted draft and chosen message type.

Message Coach shows **Context from Team Diagnostic** above its review form.
The existing dimension and its questions provide signal-specific drafting context,
including cautious interpretations for partial and indirect mappings. If the draft
is empty (or is the previous untouched scaffold), a clearly labeled drafting-notes
scaffold supplies bracketed questions. It invents no employee facts, deadlines,
owners, dates, or commitments and is not a completed employee message. An existing
manager-written draft is preserved. The untouched scaffold cannot be evaluated;
the manager must edit it. Message type stays under manager control because a focus
area does not uniquely specify task instruction versus performance feedback.

**Clear Team Diagnostic context** removes the context and any untouched scaffold.
Edited drafts, revisions, and completed Tool 1 reviews remain available. **Return
to Team Diagnostic** navigates back without evaluating the draft. Another handoff
resets the draft-submission consent checkbox. Managers may also leave either tool
without taking any action.

## Boundaries

Opening Message Coach or transferring context makes no model request. Evaluation
still requires an explicit draft submission with consent to the configured GW Azure
service. Nothing is automatically sent to employees. The handoff creates no causal
claim: survey results are discussion signals, not diagnoses, and suggested actions
do not guarantee future score improvement.

Tool 1 rubric scoring, judgment rules, model pipeline, and evidence retrieval are
unchanged. Tool 2 item means, GrandMean, hierarchy calculations, rankings, signal
selection/order, evidence judgments, privacy thresholds, suppression,
Survey-to-Action selection, and manager discussion workflow are unchanged.
The local personal-agent CLI remains separate. See `app/tool1/UPSTREAM.md` for the
source snapshot provenance.

For live evaluation, configure `.env` locally using `.env.example` and the GW guide:
`GW_AZURE_OPENAI_KEY`, `GW_ENDPOINT`, `GW_API_VERSION`, and `GW_MODEL`. Never commit
secrets. Automated integration checks mock model submission; they do not establish
that a live GW connection is operational. This change does not push or deploy the
application.
