import pytest
from app.organizational import Q12Result, analyze_results
from app.organizational.mappings import DEFAULT_MAPPINGS, SignalMapping
from app.organizational.report import render_report


def test_exact_mapping_contract():
    expected = {
        'Q01': ('expectations_and_direction', 'direct'),
        'Q02': ('information_and_resource_access', 'partial'),
        'Q04': ('recognition_communication', 'direct'),
        'Q05': ('relational_support', 'indirect'),
        'Q06': ('developmental_communication', 'direct'),
        'Q07': ('employee_voice', 'direct'),
        'Q08': ('purpose_alignment', 'direct'),
        'Q09': ('team_norms_and_coordination', 'indirect'),
        'Q11': ('progress_feedback', 'direct'),
    }
    assert {m.item_id: (m.signal, m.relationship_type) for m in DEFAULT_MAPPINGS} == expected
    assert all(m.description and m.confidence_status == 'provisional' and m.evidence_status == 'needs_review' for m in DEFAULT_MAPPINGS)


def test_unmapped_items():
    report, = analyze_results([Q12Result('t', item, 2, 10) for item in ('Q03', 'Q10', 'Q12')])
    assert report.communication_signals == ()
    assert report.manager_questions == ()


def test_configurable_mapping():
    record = Q12Result('t', 'Q01', 3, 10)
    mapping = SignalMapping('Q01', 'custom_signal', 'priority clarity', 'partial')
    report, = analyze_results([record], [mapping])
    assert report.communication_signals[0].signal_name == 'custom_signal'
    assert 'priority clarity' in report.communication_signals[0].interpretation
    assert analyze_results([record], [])[0].communication_signals == ()
    with pytest.raises(ValueError, match='unique'):
        analyze_results([record], [mapping, mapping])


def test_relative_cutoff_ties_and_language():
    records = [Q12Result('t', f'Q{i:02d}', 3 if i < 5 else 5, 10) for i in range(1,13)]
    report, = analyze_results(records)
    assert {s.source_q12_item for s in report.communication_signals} == {'Q01', 'Q02', 'Q04'}
    for signal in report.communication_signals:
        assert 'may indicate' in signal.interpretation
        assert 'investigate' in signal.interpretation
        assert 'provisional' in signal.interpretation
        assert 'does not establish that manager communication is the cause' in signal.caution
        assert signal.manager_questions
        assert set(signal.manager_questions) <= set(report.manager_questions)
    output = render_report(report).lower()
    for phrase in ('proves', 'caused by', 'communication failure', 'bad score', 'good score', 'below gallup'):
        assert phrase not in output


def test_all_default_prompts_are_noncausal():
    # Equal scores include every mapped item under the documented cutoff rule.
    report, = analyze_results([Q12Result('t', f'Q{i:02d}', 3, 10) for i in range(1,13)])
    assert len(report.communication_signals) == 9
    for signal in report.communication_signals:
        assert signal.relationship_type in ('direct', 'partial', 'indirect')
        assert all(q.endswith('?') for q in signal.manager_questions)
        assert 'cause' not in signal.interpretation
