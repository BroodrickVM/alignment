"""Privacy boundaries, aggregate quality rules and evidence review safeguards."""
from dataclasses import replace
import io
import pytest
from app.organizational.analyzer import analyze_results, load_q12_csv
from app.organizational.models import Q12Result
from app.organizational.report import render_report
from app.organizational.evidence_validation import load_evidence_validation_matrix


def team(n=5, name='team'):
    return [Q12Result(name, f'Q{i:02d}', 2 + i / 10, n) for i in range(1, 13)]


def test_privacy_threshold_boundary_and_no_payload_leak():
    rows = team()
    assert not analyze_results(rows)[0].suppressed
    rows[-1] = replace(rows[-1], respondent_count=4)
    report = analyze_results(rows)[0]
    assert report.suppressed
    assert report.grand_mean is None
    assert not any((report.hierarchy_scores, report.item_means, report.strengths,
                    report.opportunities, report.communication_signals, report.manager_questions,
                    report.missing_items, report.data_quality_notes))
    assert 'suppressed' in render_report(report)
    assert '2.10' not in render_report(report)
    assert not analyze_results(rows, minimum_responses=4)[0].suppressed


@pytest.mark.parametrize('value', [0, -1, True, 2.5, '5', None])
def test_invalid_threshold(value):
    with pytest.raises(ValueError, match='minimum_responses'):
        analyze_results(team(), minimum_responses=value)


def test_groups_and_periods_suppressed_independently():
    rows = team(4) + team(5, 'other') + [replace(r, period='next') for r in team(5)]
    assert [r.suppressed for r in analyze_results(rows)] == [True, False, False]


def test_missing_items_and_varying_counts_preserve_available_item_logic():
    rows = team()[1:]
    rows[0] = replace(rows[0], respondent_count=6)
    report = analyze_results(rows)[0]
    assert report.missing_items == ('Q01',)
    assert len(report.data_quality_notes) == 2
    assert report.grand_mean == sum(r.mean_score for r in rows) / len(rows)
    assert report.hierarchy_scores['Basic Needs'] == rows[0].mean_score


@pytest.mark.parametrize('value', ['', 'NaN', 'inf', '0', '5.1', 'abc'])
def test_invalid_csv_score_rejected(value):
    with pytest.raises(ValueError, match='line 2'):
        load_q12_csv(io.StringIO('team_id,item_id,mean_score,respondent_count\nt,Q01,' + value + ',5\n'))


def test_evidence_pending_cannot_be_promoted():
    matrix = load_evidence_validation_matrix()
    pending = replace(matrix.validations[0], validation_status='pending',
                      recommended_status='gallup_supported_external_review_pending', external_support_level='pending')
    for status in ('validated', 'partially_supported', 'indirect_support', 'insufficient_evidence'):
        with pytest.raises(ValueError, match='Pending external'):
            replace(pending, validation_status=status)


def test_dashboard_suppression_stops_before_scores_and_downloads():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file('app/organizational/dashboard.py').run()
    assert not app.exception
    app.sidebar.number_input[0].set_value(10000).run()
    assert not app.exception
    assert any('suppressed' in w.value for w in app.warning)
    assert not any(h.value == 'Executive Summary' for h in app.header)
    assert not app.get('download_button')


def test_evidence_relationships_match_existing_rubric():
    from app.organizational.rubric import load_rubric
    matrix = load_evidence_validation_matrix()
    for dimension in load_rubric().dimensions:
        assert matrix.get_by_source_item(dimension.source_item).relationship_type == dimension.relationship_type


def test_completed_evidence_review_requires_provenance_and_date():
    row = replace(load_evidence_validation_matrix().validations[0],
                  validation_status='pending', recommended_status='gallup_supported_external_review_pending',
                  external_support_level='pending', external_source_reference='pending',
                  reviewer='pending', reviewed_on='pending')
    with pytest.raises(ValueError, match='require source'):
        replace(row, external_support_level='moderate', validation_status='partially_supported')
    with pytest.raises(ValueError, match='ISO date'):
        replace(row, external_support_level='moderate', validation_status='partially_supported',
                external_source_reference='test fixture only', reviewer='test reviewer', reviewed_on='yesterday')


def test_suppressed_download_helper_contains_no_diagnostics():
    from app.organizational.dashboard import diagnostic_summary_text
    text = diagnostic_summary_text(analyze_results(team(4))[0])
    assert 'suppressed' in text
    assert 'GrandMean' not in text
    assert '2.10' not in text


def test_eligible_analysis_unchanged_by_threshold():
    from dataclasses import asdict
    first = asdict(analyze_results(team(10), minimum_responses=1)[0])
    second = asdict(analyze_results(team(10), minimum_responses=5)[0])
    for payload in (first, second):
        payload.pop('minimum_responses')
        payload.pop('limitations')
    assert first == second
