"""Shared entry point: streamlit run streamlit_app.py."""
import streamlit as st
from app.organizational.dashboard import main as team_diagnostic
from app.tool1.dashboard import main as message_coach


def overview():
    st.set_page_config(page_title='CommsAlign',layout='wide')
    st.markdown("""<style>
    .stApp {background:#F5F7FB;color:#20334A;}
    .block-container {max-width:1120px;padding-top:4rem;padding-bottom:3rem;}
    .st-key-brand h1 {text-align:center;font-size:clamp(2.8rem,6vw,4.6rem);letter-spacing:-.055em;color:#17365D;padding-bottom:.4rem;}
    .ca-symbol {display:block;width:160px;max-width:100%;height:auto;margin:0 auto 1.2rem;}
    .ca-eyebrow {text-align:center;text-transform:uppercase;letter-spacing:.18em;font-size:.75rem;font-weight:700;color:#47717D;margin-bottom:.3rem;}
    .st-key-overview-intro, .st-key-overview-intro [data-testid="stMarkdown"], .st-key-overview-intro [data-testid="stMarkdownContainer"] {width:100%;}
    .ca-intro {text-align:center;width:100%;max-width:none;margin:0 auto 2.6rem;color:#526174;font-size:1.12rem;line-height:1.7;}
    [class*="st-key-tool-card-"] {background:white;border:1px solid #DEE6EF;border-radius:22px;padding:1.8rem;box-shadow:0 12px 35px #17365D08;min-height:350px;}
    .st-key-tool-card-one {border-top:4px solid #2F75B5;}
    .st-key-tool-card-two {border-top:4px solid #2E8B8B;}
    [class*="st-key-tool-card-"] h2 {font-size:1.7rem;color:#17365D;letter-spacing:-.025em;}
    [class*="st-key-tool-card-"] p {line-height:1.65;}
    .ca-tag {color:#426A88;font-size:.76rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;}
    .ca-foot {text-align:center;color:#607086;font-size:.88rem;line-height:1.6;margin:2.2rem auto 0;max-width:760px;}
    </style>""",unsafe_allow_html=True)
    st.markdown('<img class="ca-symbol" alt="CommsAlign CA monogram" src="data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%22195%2095%20470%20355%22%3E%3Cpath%20d%3D%22M514%20164C423%2062%20238%20112%20218%20263C195%20422%20386%20495%20491%20376C402%20443%20267%20399%20264%20289C259%20171%20397%20106%20514%20164Z%22%20fill%3D%22%2317365D%22%2F%3E%3Cg%20fill%3D%22none%22%20stroke%3D%22%232E8B8B%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M388%20412C425%20340%20477%20229%20519%20141C524%20130%20531%20131%20535%20143C563%20237%20593%20340%20627%20405%22%20stroke-width%3D%2223%22%2F%3E%3Cpath%20d%3D%22M361%20346C436%20314%20531%20352%20640%20291%22%20stroke-width%3D%2215%22%2F%3E%3C%2Fg%3E%3C%2Fsvg%3E">',unsafe_allow_html=True)
    st.markdown('<div class="ca-eyebrow">Workplace communication, with perspective</div>',unsafe_allow_html=True)
    with st.container(key='brand'):
        st.title('CommsAlign')
    with st.container(key='overview-intro'):
        st.markdown('<p class="ca-intro">Understand your team’s signals. Bring more clarity to your messages.<br>Two tools to support thoughtful workplace conversations.</p>',unsafe_allow_html=True)
    with st.container(key='tool-card-one'):
        st.markdown('<div class="ca-tag">Tool 1 · Review a message</div>',unsafe_allow_html=True)
        st.header('Message Coach')
        st.write('Draft and review manager communication informed by a selected team signal, or open Message Coach independently.')
        st.markdown('- Review your draft against a message-specific rubric.\n- Inspect the evidence behind each rating.\n- Download the review for your own revision.')
        st.caption('Live evaluation requires your GW Azure connection. Automated rewriting is not available yet.')
        if st.button('Open',key='open-message-coach',type='primary',use_container_width=True):
            st.switch_page(st.Page(message_coach,title='Tool 1 — Message Coach',url_path='message-coach'))
    with st.container(key='tool-card-two'):
        st.markdown('<div class="ca-tag">Tool 2 · Explore team signals</div>',unsafe_allow_html=True)
        st.header('Team Diagnostic')
        st.write('Identify communication-related survey signals and carry a selected focus area into Message Coach.')
        st.markdown('- See relative strengths and areas to explore.\n- Review evidence and privacy limitations.\n- Capture learning and export a follow-up summary.')
        st.caption('Currently uses synthetic demonstration data. Small-group results are suppressed by the reporting rule.')
        if st.button('Open',key='open-team-diagnostic',type='primary',use_container_width=True):
            st.switch_page(st.Page(team_diagnostic,title='Tool 2 — Team Diagnostic',url_path='team-diagnostic'))
    st.markdown('<p class="ca-foot">A starting point for discussion, not a diagnosis. Survey interpretations and message ratings remain provisional. Selected non-sensitive context can be passed between tools in the current browser session. Nothing is automatically sent to employees. Model evaluation requires explicit draft submission with consent.</p>',unsafe_allow_html=True)


if __name__=='__main__':
    # Retain manager-written widget content while another shared page is open.
    for key in ('tool1_draft', 'tool1_revision'):
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]
    st.navigation([
        st.Page(overview,title='Overview',default=True),
        st.Page(message_coach,title='Tool 1 — Message Coach',url_path='message-coach'),
        st.Page(team_diagnostic,title='Tool 2 — Team Diagnostic',url_path='team-diagnostic'),
    ]).run()

