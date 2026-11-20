"""Session-only interface for the teammates' Tool 1 judge."""
from dataclasses import asdict
import html
import json
import re
import streamlit as st
import altair as alt
from app.tool1.rubrics import RUBRICS


def dimension_label(name):
    return re.sub(r'^[DF]\d+_', '', name).replace('_',' ').capitalize()


def score_chart(result):
    if result['abstain']:
        return
    rows=[]
    unscored=[]
    for name,rating in result['dimensions'].items():
        label=dimension_label(name)
        if rating['status']=='scored' and rating['score'] is not None:
            rows.append({'Dimension':label,'Score':rating['score'],'Baseline':1})
        else:
            unscored.append(label)
    if rows:
        st.subheader('Rubric scores')
        chart=alt.Chart(alt.Data(values=rows)).encode(
            y=alt.Y('Dimension:N',sort=[row['Dimension'] for row in rows],title=None),
            x=alt.X('Score:Q',scale=alt.Scale(domain=[1,5],zero=False),
                    axis=alt.Axis(values=[1,2,3,4,5]),title='Score (1–5)'),
            tooltip=['Dimension:N','Score:Q'],
        )
        bars=chart.mark_bar(color='#2F75B5',size=22).encode(x2='Baseline:Q')
        points=chart.mark_point(filled=True,color='#2F75B5',size=65)
        labels=chart.mark_text(align='left',dx=9,color='#20334A').encode(text='Score:Q')
        st.altair_chart((bars+points+labels).properties(height=max(120,len(rows)*48)),use_container_width=True)
        st.caption('Bars start at 1, the lowest rubric score. Higher scores indicate closer alignment with the rubric.')
    if unscored:
        st.caption('Not scored: '+', '.join(unscored)+'. See the explanations below.')


def clear_message():
    st.session_state['tool1_result']=None
    st.session_state['tool1_draft']=''
    st.session_state.pop('tool1_revision',None)
    st.session_state.pop('tool1_rescore',None)


def render_team_context():
    from app.tool_handoff import CONTEXT_KEY, clear_handoff
    context = st.session_state.get(CONTEXT_KEY)
    if not context:
        return
    st.subheader('Context from Team Diagnostic')
    st.caption('Selected by the manager in Tool 2; temporary context in this browser session.')
    st.write(f'**Focus area:** {context["dimension_name"]}')
    st.write(f'**Source Q12-style item:** {context["source_item"]}')
    st.write(f'**Observed score:** {context["observed_score"]:.2f} / 5')
    st.write(context['interpretation'])
    st.write('**Questions you may explore:**')
    for question in context['manager_questions']:
        st.write('- ' + question)
    if context.get('suggested_action'):
        st.write('**Discussion option:** ' + context['suggested_action'])
    if context.get('suggested_timeline'):
        st.write('**Suggested timeline for discussion:** ' + context['suggested_timeline'])
    st.info('Use this context to inform your draft. The survey result is a discussion signal, not a causal diagnosis. Suggested actions and timelines are options, not commitments or proven interventions.')
    st.caption('Choose the message type that fits your communication. Edit any drafting scaffold before evaluation. Existing drafts and completed reviews are retained.')
    st.button('Clear Team Diagnostic context', on_click=clear_handoff, args=(st.session_state,))
    if st.button('Return to Team Diagnostic'):
        from app.organizational.dashboard import main as team_diagnostic
        st.switch_page(st.Page(team_diagnostic, title='Tool 2 — Team Diagnostic',
                               url_path='team-diagnostic'))


def main():
    st.set_page_config(page_title='CommsAlign — Message Coach',layout='wide')
    st.title('Tool 1 — Message Coach')
    st.write('Review a task instruction or performance feedback draft using the team’s rubric.')
    st.info('Scores are rubric-based model judgments, not validated measures of communication effectiveness. Review the evidence and output yourself.')
    st.caption('Evaluation sends your draft to the configured GW Azure service only when you submit it with consent. No message is sent to employees. The rewrite never invents facts: anything only you know is left as a [gap?] to fill in. Avoid identifying or sensitive content.')
    st.session_state.setdefault('tool1_result',None)
    if (st.session_state['tool1_result'] or {}).get('sample'):
        st.session_state['tool1_result']=None
    render_team_context()
    with st.form('tool1_review'):
        kind=st.selectbox('Message type',list(RUBRICS),format_func=lambda value:value.replace('_',' ').title())
        draft=st.text_area('Draft message',height=200,key='tool1_draft')
        consent=st.checkbox('I agree to send this draft to the configured GW Azure model for evaluation.', key='tool1_model_consent')
        submit=st.form_submit_button('Evaluate draft')
    if submit:
        st.session_state['tool1_result']=None
        st.session_state.pop('tool1_revision',None)
        st.session_state.pop('tool1_rescore',None)
        if not draft.strip():
            st.error('Enter a draft message to evaluate.')
        elif draft == st.session_state.get('tool2_message_scaffold'):
            st.error('Edit the drafting scaffold into your own message before evaluating.')
        elif not consent:
            st.error('Confirm the model submission before evaluating.')
        else:
            progress=st.progress(10,text='10% — Checking connection settings')
            st.caption('Progress reflects review stages. It stays at 25% while the model responds.')
            try:
                from app.tool1.config import load_settings
                from app.tool1.pipeline import run
                try:
                    load_settings()
                except RuntimeError:
                    progress.empty()
                    st.error('GW Azure settings are missing. Configure the required settings in your local .env file; never paste API keys into chat or commit them to GitHub.')
                else:
                    progress.progress(25,text='25% — Scoring, rewriting, and scoring the rewrite…')
                    with st.spinner('Reviewing and rewriting the draft…'):
                        res=run(draft,kind)
                    st.session_state['tool1_result']={'draft':draft,'kind':kind,'result':asdict(res.before),
                        'rewrite':asdict(res.rewrite) if res.rewrite else None,'after':asdict(res.after) if res.after else None}
                    progress.progress(100,text='100% — Review complete. Your results are below.')
            except ImportError:
                progress.empty()
                st.error('Install requirements-tool1.txt to enable the model connection.')
            except Exception:
                progress.empty()
                st.error('Evaluation could not be completed. Check the GW connection settings and model access, then retry. No result has been substituted.')
    with st.expander('Connection setup and rubric'):
        st.write('Install requirements-tool1.txt, then copy .env.example to .env and enter your GW-provided settings locally. Never commit .env.')
        st.code('GW_AZURE_OPENAI_KEY\nGW_ENDPOINT\nGW_API_VERSION\nGW_MODEL')
        st.markdown(RUBRICS[kind].text())
    saved=st.session_state['tool1_result']
    if saved:
        result=saved['result']
        st.subheader('Evaluation of the last submitted draft')
        st.text(saved['draft'])
        if result['abstain']:
            st.warning('Judge abstained: '+str(result['abstain_reason'] or 'Outside rubric scope.'))
        else:
            st.write('Rubric label: '+str(result['label']).replace('_',' '))
        st.caption('Model-reported confidence: '+result['confidence_level']+' — '+result['confidence_note'])
        score_chart(result)
        for name,rating in result['dimensions'].items():
            st.write('**'+dimension_label(name)+'**')
            st.write(f'Status: {rating["status"]}; score: {rating["score"] if rating["score"] is not None else "Not scored"}')
            for quote in rating['evidence']:
                st.text('Evidence: '+quote)
            st.write(rating['note'])
        for warning in result['warnings']:
            st.warning(warning)
        rw=saved.get('rewrite')
        if rw:
            st.subheader('Suggested rewrite')
            st.caption('Highlighted [gaps?] are details only you know. The tool never guesses them.')
            st.markdown('<div style="border:1px solid #DEE6EF;border-radius:10px;padding:12px;background:white;white-space:pre-wrap">'
                        +re.sub(r'(\[[^\[\]]*\?\])',r'<mark>\1</mark>',html.escape(rw['rewrite']))+'</div>',unsafe_allow_html=True)
            for w in rw['warnings']:
                st.warning(w)
            after=saved.get('after')
            if after and rw['changes']:
                st.write('Rewrite label: '+str(after['label']).replace('_',' '))
                score_chart(after)
            if rw['changes']:
                st.subheader('Why these changes')
                cards={c['id']:c for c in rw['cards']}
                for ch in rw['changes']:
                    with st.expander(dimension_label(str(ch.get('dimension','')))+': '+str(ch.get('what',''))):
                        st.write(ch.get('why',''))
                        for cid in ch.get('card_ids') or []:
                            c=cards.get(cid)
                            if c:
                                st.markdown(f"**Evidence ({c['setting']}).** {c['finding']}  \n_{c['source']}, {c['locator']}. Limits: {c['limits']}_")
                        if not ch.get('card_ids'):
                            st.caption('No evidence card applies to this change; it follows the rubric only.')
            st.subheader('Fill in the gaps and re-score')
            st.session_state.setdefault('tool1_revision',rw['rewrite'])
            revision=st.text_area('Your version',height=220,key='tool1_revision')
            if st.button('Re-score my version',disabled=not revision.strip()):
                from app.tool1.pipeline import rescore
                try:
                    with st.spinner('Scoring your version…'):
                        st.session_state['tool1_rescore']=asdict(rescore(revision,saved.get('kind',kind)))
                except Exception:
                    st.error('Re-scoring could not be completed. Check the GW connection and retry.')
            again=st.session_state.get('tool1_rescore')
            if again:
                if again['abstain']:
                    st.warning('Judge abstained: '+str(again['abstain_reason']))
                else:
                    st.write('Your version label: '+str(again['label']).replace('_',' '))
                    score_chart(again)
            st.download_button('Download your revision',revision,file_name='commsalign-revised-draft.txt',mime='text/plain')
        st.download_button('Download Message Review',json.dumps(saved,indent=2),file_name='commsalign-message-review.json',mime='application/json')
        st.button('Clear message and result',on_click=clear_message)
