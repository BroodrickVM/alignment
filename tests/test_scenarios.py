"""End-to-end scenarios with explicit independently specified expected outputs."""
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from app.organizational.analyzer import analyze_csv
from app.organizational.dashboard import diagnostic_summary_text

ROOT=Path(__file__).resolve().parents[1]
FIXTURES=ROOT/'tests/fixtures/scenarios'
DASHBOARD=ROOT/'app/organizational/dashboard.py'


def dashboard(name):
    # Exercise the actual page using an isolated fixture; no production file edits.
    source=DASHBOARD.read_text().replace(
        "SAMPLE_PATH = PROJECT_ROOT / 'data' / 'organizational' / 'sample_q12_results.csv'",
        'SAMPLE_PATH = Path('+repr(str(FIXTURES/(name+'.csv')))+')')
    source=source.replace('PROJECT_ROOT = Path(__file__).resolve().parents[2]',
                          'PROJECT_ROOT = Path('+repr(str(ROOT))+')')
    return AppTest.from_string(source).run(timeout=30)


def text(app):
    return '\n'.join(v.value for v in app.markdown)


@pytest.mark.parametrize('name,mean',[('all_equal',3),('all_high',4.5),('all_low',1.5)])
def test_uniform_profiles(name,mean):
    report,=analyze_csv(FIXTURES/(name+'.csv'))
    assert report.grand_mean==mean
    assert set(report.hierarchy_scores.values())=={mean}
    assert len(report.hierarchy_strengths)==len(report.hierarchy_opportunities)==4
    assert len(report.communication_signals)==9
    app=dashboard(name)
    assert not app.exception
    assert 'Available hierarchy areas are tied' in text(app)
    assert any('Item rankings include ties' in v.value for v in app.info)
    exported=diagnostic_summary_text(report)
    assert f'GrandMean: {mean:.2f}' in exported
    assert 'Item rankings include ties' in exported
    assert 'No causal inference is performed.' in exported


def test_one_low_item():
    report,=analyze_csv(FIXTURES/'one_low.csv')
    assert report.grand_mean==pytest.approx(46/12)
    assert report.opportunities[0].item_id=='Q07'
    assert report.opportunities[0].mean_score==2
    assert report.hierarchy_scores['Teamwork']==3.5
    assert report.hierarchy_opportunities==('Teamwork',)
    # Third-place ties retain all mapped items, not an invented unique priority.
    assert len(report.communication_signals)==9
    app=dashboard('one_low')
    assert not app.exception
    assert 'Q07 — Employee Voice' in text(app)
    assert 'No causal inference is performed.' in diagnostic_summary_text(report)


def test_missing_items():
    report,=analyze_csv(FIXTURES/'missing_items.csv')
    assert report.missing_items==('Q01','Q11','Q12')
    assert report.grand_mean==3
    assert report.hierarchy_scores['Growth'] is None
    assert report.hierarchy_scores['Basic Needs']==3
    app=dashboard('missing_items')
    assert not app.exception
    assert any('Missing items: Q01, Q11, Q12' in v.value for v in app.warning)
    assert 'Unavailable' in text(app)
    export=diagnostic_summary_text(report)
    assert 'Growth: unavailable' in export and 'No values were imputed' in export


def test_suppressed_team_no_outputs():
    report,=analyze_csv(FIXTURES/'small_team.csv')
    assert report.suppressed and report.item_means is None
    assert report.grand_mean is None and not report.communication_signals
    app=dashboard('small_team')
    assert not app.exception
    assert any('suppressed' in v.value for v in app.warning)
    assert 'Executive Summary' not in [v.value for v in app.header]
    assert not app.get('download_button')
    assert 'GrandMean:' not in diagnostic_summary_text(report)
    app.sidebar.number_input[0].set_value(4).run()
    assert not app.exception
    assert 'Executive Summary' in [v.value for v in app.header]


@pytest.mark.parametrize('name,message',[
 ('invalid_score','mean_score'),('invalid_count','respondent_count'),
 ('missing_value','Malformed CSV'),('duplicate','Duplicate')])
def test_invalid_inputs_fail_atomically(name,message):
    with pytest.raises(ValueError,match=message):
        analyze_csv(FIXTURES/(name+'.csv'))
    app=dashboard(name)
    assert not app.exception
    assert any(message in v.value for v in app.error)
    assert not app.get('download_button')
    assert 'Executive Summary' not in [v.value for v in app.header]


def test_group_isolation_and_selection():
    reports=analyze_csv(FIXTURES/'multiple_groups.csv')
    assert [(r.team_id,r.period,r.suppressed,r.grand_mean) for r in reports]==[
        ('SYNTHETIC_Mixed','P1',True,None),('SYNTHETIC_Mixed','P2',False,4),
        ('SYNTHETIC_Other','P1',False,2)]
    app=dashboard('multiple_groups')
    assert not app.exception
    assert not app.get('download_button')
    app.sidebar.selectbox[1].select('P2').run()
    assert not app.exception and len(app.get('download_button'))==2
    assert '4.00 / 5' in text(app)
    app.sidebar.selectbox[0].select('SYNTHETIC_Other').run()
    assert not app.exception
    assert '2.00 / 5' in text(app)
    assert 'SYNTHETIC_Mixed' not in diagnostic_summary_text(reports[2])
    assert 'SYNTHETIC_Other' not in diagnostic_summary_text(reports[1])
