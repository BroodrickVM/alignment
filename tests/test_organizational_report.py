"""Manager-facing presentation checks without changing diagnostic scoring."""
from pathlib import Path

import pytest

from app.organizational import Q12Result, analyze_csv, analyze_results
from app.organizational.mappings import SignalMapping
from app.organizational.report import conversation_priorities, render_report


@pytest.fixture
def sample_reports():
    return analyze_csv(Path(__file__).resolve().parents[1] / 'data/organizational/sample_q12_results.csv')


def test_six_sections_and_executive_summary(sample_reports):
    headings = [
        '1. Executive Summary', '2. Stronger Signals',
        '3. Areas for Investigation', '4. Communication Signals to Explore',
        '5. Recommended Conversation Priorities', '6. Limitations',
    ]
    for report in sample_reports:
        output = render_report(report)
        positions = [output.index(heading) for heading in headings]
        assert positions == sorted(positions)
        assert f'Team ID: {report.team_id}' in output
        assert f'GrandMean: {report.grand_mean:.2f} / 5' in output
        assert 'Strongest Hierarchy Area: ' + ', '.join(report.hierarchy_strengths) in output
        assert 'Main Hierarchy Area for Investigation: ' + ', '.join(report.hierarchy_opportunities) in output
        assert 'Summary:' in output
        assert 'Opportunities' not in output
        assert 'Communication hypotheses:' not in output


def test_item_interpretations_and_signal_details(sample_reports):
    for report in sample_reports:
        output = render_report(report)
        stronger = output.split('2. Stronger Signals')[1].split('3. Areas for Investigation')[0]
        investigation = output.split('3. Areas for Investigation')[1].split('4. Communication Signals to Explore')[0]
        for section, records in ((stronger, report.strengths), (investigation, report.opportunities)):
            assert section.count('Interpretation:') == 3
            for record in records:
                assert f'{record.item_id}: {record.mean_score:.2f} / 5' in section
        for signal in report.communication_signals:
            assert f'Source Q12 item: {signal.source_q12_item}' in output
            assert f'Observed score: {signal.observed_score:.2f} / 5' in output
            assert f'Relationship type: {signal.relationship_type}' in output
            assert signal.interpretation in output
            assert signal.caution in output
            assert 2 <= len(signal.manager_questions) <= 3
            for question in signal.manager_questions:
                assert question in output
        for limitation in report.limitations:
            assert limitation in output


def test_priorities_are_signal_grounded(sample_reports):
    atlas = sample_reports[0]
    assert conversation_priorities(atlas) == (
        'Explore team experiences of opportunities for employee input.',
        'Explore team experiences of recognition of valued work.',
        'Explore team experiences of expectations and priorities.',
    )
    for report in sample_reports:
        before = report.to_dict()
        priorities = conversation_priorities(report)
        assert len(priorities) == 3
        output = render_report(report)
        assert all(priority in output for priority in priorities)
        assert 'Discussion priorities only, not prescriptions' in output
        assert report.to_dict() == before
        for phrase in ('bad', 'poor', 'proves', 'caused by', 'below gallup'):
            assert phrase not in output.split('6. Limitations')[0].lower()


def test_unmapped_items_have_no_invented_priorities():
    report, = analyze_results([Q12Result('t', item, 3, 10) for item in ('Q03', 'Q10', 'Q12')])
    output = render_report(report)
    assert conversation_priorities(report) == ()
    assert 'No communication signals selected' in output
    assert 'workplace relationships' in output
    assert 'opportunities to learn and grow' in output


def test_single_custom_signal_has_three_grounded_priorities_and_two_questions():
    report, = analyze_results([Q12Result('t', 'Q03', 3, 10)], [
        SignalMapping('Q03', 'custom_topic', 'a custom topic', 'partial'),
    ])
    assert len(conversation_priorities(report)) == 3
    assert all('custom topic' in priority for priority in conversation_priorities(report))
    questions = render_report(report).split('Questions to investigate:')[1].split('5. Recommended')[0]
    assert questions.count('    - ') == 2
    assert 'unavailable' in render_report(report)


def test_all_item_topics_and_tied_hierarchy_are_readable():
    report, = analyze_results([Q12Result('t', f'Q{i:02d}', 3, 10) for i in range(1, 13)])
    output = render_report(report)
    assert 'Strongest Hierarchy Area: Basic Needs, Individual, Teamwork, Growth' in output
    assert 'Hierarchy ties are listed together' in output
    assert len(report.communication_signals) == 9
