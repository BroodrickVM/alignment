import io
import json
from pathlib import Path
import pytest
from app.organizational import Q12Result, analyze_csv, analyze_results, load_q12_csv
from app.organizational.report import main, render_report


def records(scores, period=None):
    return [Q12Result('team', f'Q{i:02d}', score, 10, period=period) for i, score in enumerate(scores, 1)]


@pytest.mark.parametrize('score', [0, 5.1, float('nan'), float('inf'), True, '3'])
def test_invalid_scores(score):
    with pytest.raises(ValueError, match='mean_score'):
        Q12Result('team', 'Q01', score, 10)


@pytest.mark.parametrize('item', ['Q00', 'Q13', 'Q1', 'q01', ''])
def test_invalid_items(item):
    with pytest.raises(ValueError, match='item_id'):
        Q12Result('team', item, 3, 10)


@pytest.mark.parametrize('count', [0, -1, 1.5, True])
def test_invalid_counts(count):
    with pytest.raises(ValueError, match='respondent_count'):
        Q12Result('team', 'Q01', 3, count)


@pytest.mark.parametrize('percentile', [-1, 101, float('nan'), True])
def test_invalid_percentiles(percentile):
    with pytest.raises(ValueError, match='percentile_rank'):
        Q12Result('team', 'Q01', 3, 10, percentile)


def test_calculations_and_ordering():
    report, = analyze_results(records([1,2,3,4,5,1,2,3,4,5,1,2]))
    assert report.grand_mean == pytest.approx(33 / 12)
    assert report.hierarchy_scores == {'Basic Needs': 1.5, 'Individual': 3.25, 'Teamwork': 3.5, 'Growth': 1.5}
    assert [r.item_id for r in report.strengths] == ['Q05', 'Q10', 'Q04']
    assert [r.item_id for r in report.opportunities] == ['Q01', 'Q06', 'Q11']
    assert report.hierarchy_strengths == ('Teamwork',)
    assert report.hierarchy_opportunities == ('Basic Needs', 'Growth')
    assert json.loads(json.dumps(report.to_dict()))['item_means']['Q01'] == 1


def test_missing_items_and_unweighted_means():
    report, = analyze_results([Q12Result('team', 'Q01', 1, 1), Q12Result('team', 'Q03', 5, 100)], minimum_responses=1)
    assert report.grand_mean == 3
    assert len(report.missing_items) == 10
    assert report.hierarchy_scores['Growth'] is None
    assert report.hierarchy_scores['Basic Needs'] == 1
    assert any('No values were imputed' in x for x in report.limitations)


def test_duplicate_and_period_separation():
    with pytest.raises(ValueError, match='Duplicate'):
        analyze_results(records([3]) * 2)
    reports = analyze_results(records([1], 'first') + records([5], 'second'))
    assert [r.grand_mean for r in reports] == [1, 5]
    with pytest.raises(ValueError, match='At least one'):
        analyze_results([])


HEADER = 'team_id,item_id,mean_score,respondent_count\n'


@pytest.mark.parametrize('csv_text', [
    '', 'team_id,item_id\nt,Q01\n',
    'team_id,item_id,mean_score,respondent_count,employee_email\nt,Q01,3,10,x\n',
    'team_id,item_id,mean_score,mean_score,respondent_count\nt,Q01,3,3,10\n',
    HEADER + 't,Q01,3\n', HEADER + 't,Q01,3,10,extra\n',
    HEADER + 't,Q01,no,10\n', HEADER + 't,Q01,3,1.5\n',
    HEADER + 't,Q01,nan,10\n', HEADER + 't,Q13,3,10\n',
    HEADER + 't,Q01,3,10\nt,Q01,4,10\n', HEADER + '"unfinished,Q01,3,10\n',
    HEADER + ',Q01,3,10\n', HEADER,
])
def test_malformed_csv(csv_text):
    with pytest.raises(ValueError):
        load_q12_csv(io.StringIO(csv_text))


def test_optional_fields_and_bounds():
    csv_text = HEADER.rstrip() + ',percentile_rank,period\nt,Q01,1,10,0,p1\nt,Q02,5,11,100,p1\n'
    report, = analyze_csv(io.StringIO(csv_text))
    assert report.grand_mean == 3
    assert report.strengths[0].percentile_rank == 100
    assert report.period == 'p1'
    assert load_q12_csv(io.StringIO(HEADER.rstrip() + ',percentile_rank,period\nt,Q01,3,10,,\n'))[0].period is None


def test_synthetic_dataset_and_terminal(capsys):
    path = Path(__file__).resolve().parents[1] / 'data/organizational/sample_q12_results.csv'
    reports = analyze_csv(path)
    assert len(reports) == 3
    assert all(len(r.item_means) == 12 and r.team_id.startswith('SYNTHETIC_') for r in reports)
    assert main([str(path)]) == 0
    assert 'GrandMean:' in capsys.readouterr().out
    assert 'unavailable' in render_report(analyze_results(records([3]))[0])
