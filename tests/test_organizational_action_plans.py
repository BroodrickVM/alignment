"""Action metadata is validated independently and consumes unchanged diagnostics."""
import csv
import io
from copy import deepcopy
from dataclasses import asdict

import pytest
from streamlit.testing.v1 import AppTest

from app.organizational import Q12Result, analyze_csv, analyze_results
from app.organizational.action_plans import (
    ActionLibrary, REQUIRED_COLUMNS, action_plans_for_report, load_action_plans,
)
from app.organizational.dashboard import SAMPLE_PATH, diagnostic_summary_text
from app.organizational.rubric import load_rubric
from pathlib import Path
DASHBOARD = Path(__file__).resolve().parents[1] / 'app/organizational/dashboard.py'


def csv_source(rows, columns=REQUIRED_COLUMNS):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    stream.seek(0)
    return stream


def test_library_matches_all_authoritative_dimensions():
    library = load_action_plans()
    rubric = load_rubric()
    assert len(library.plans) == len(rubric.dimensions) == 9
    for dimension in rubric.dimensions:
        plan = library.get_by_dimension_id(dimension.dimension_id)
        assert plan == library.get_by_source_item(dimension.source_item)
        assert plan.dimension_name == dimension.dimension_name
        assert plan.source_item == dimension.source_item
        assert 'not a proven intervention' in plan.action_caution
        assert 'does not guarantee a future score improvement' in plan.action_caution
        assert 'will increase' not in plan.suggested_action.lower()
        assert 'expected score increase' not in str(asdict(plan)).lower()


@pytest.mark.parametrize('columns', [REQUIRED_COLUMNS[:-1], (*REQUIRED_COLUMNS, 'unsupported'), (*REQUIRED_COLUMNS, 'dimension_id')])
def test_schema_rejects_missing_extra_duplicate_columns(columns):
    with pytest.raises(ValueError, match='columns'):
        load_action_plans(csv_source([], columns))


@pytest.mark.parametrize('field', REQUIRED_COLUMNS)
def test_all_fields_require_text(field):
    row = asdict(load_action_plans().plans[0])
    row[field] = '  '
    with pytest.raises(ValueError, match='nonempty'):
        load_action_plans(csv_source([row]))


@pytest.mark.parametrize('key', ['dimension_id', 'source_item'])
def test_duplicate_mappings_rejected(key):
    rows = [asdict(p) for p in load_action_plans().plans[:2]]
    rows[1][key] = rows[0][key]
    with pytest.raises(ValueError, match=f'Duplicate action-plan {key}'):
        load_action_plans(csv_source(rows))


@pytest.mark.parametrize('key,value', [('source_item', 'Q03'), ('source_item', 'Q99'), ('source_item', 'Q02'), ('dimension_id', 'unknown'), ('dimension_name', 'Wrong')])
def test_invalid_mapping_rejected(key, value):
    row = asdict(load_action_plans().plans[0])
    row[key] = value
    with pytest.raises(ValueError):
        load_action_plans(csv_source([row]))


@pytest.mark.parametrize('items', [('Q01',), ('Q01', 'Q02'), ('Q03', 'Q10', 'Q12'), tuple(f'Q{i:02}' for i in range(1, 13))])
def test_selection_preserves_report_order_ties_and_sparse_signals(items):
    report, = analyze_results([Q12Result('t', item, 3, 10) for item in items])
    before = deepcopy(report.to_dict())
    selected = action_plans_for_report(report, load_action_plans())
    assert len(selected) == min(3, len(report.communication_signals))
    assert [s.plan.source_item for s in selected] == [s.source_q12_item for s in report.communication_signals[:3]]
    assert [s.observed_score for s in selected] == [s.observed_score for s in report.communication_signals[:3]]
    assert report.to_dict() == before


def test_suppression_and_missing_metadata():
    suppressed, = analyze_results([Q12Result('t', 'Q01', 3, 1)])
    assert suppressed.suppressed
    assert action_plans_for_report(suppressed, ActionLibrary(())) == ()
    report, = analyze_results([Q12Result('t', 'Q01', 3, 10)])
    with pytest.raises(ValueError, match='metadata for Q01'):
        action_plans_for_report(report, ActionLibrary(()))


def test_download_contains_actions_and_preserves_diagnostics():
    for report in analyze_csv(SAMPLE_PATH):
        before = deepcopy(report.to_dict())
        text = diagnostic_summary_text(report)
        assert text.index('Conversation Priorities') < text.index('Suggested Manager Actions') < text.index('What to Do Next')
        for selected in action_plans_for_report(report, load_action_plans()):
            assert all(str(value) in text for key, value in asdict(selected.plan).items() if key != 'dimension_id')
            assert f'{selected.observed_score:.2f} / 5' in text
        assert 'Survey results are signals and hypotheses only. They do not establish causes.' in text
        assert 'No causal inference is performed.' in text
        assert report.to_dict() == before


def test_dashboard_action_cards_and_workflow():
    app = AppTest.from_file(str(DASHBOARD)).run(timeout=30)
    assert not app.exception
    headings = [h.value for h in app.header]
    assert headings.index('Conversation Priorities') < headings.index('Suggested Manager Actions') < headings.index('What to Do Next')
    report = analyze_csv(SAMPLE_PATH)[0]
    text = '\n'.join(m.value for m in app.markdown)
    for selected in action_plans_for_report(report, load_action_plans()):
        assert selected.plan.suggested_timeline in text
        assert selected.plan.success_indicator in text
        assert selected.plan.action_caution in text
    assert 'Whole Company' not in text


@pytest.mark.parametrize('suffix', [',extra', ''])
def test_incorrect_row_width_rejected(suffix):
    if suffix:
        stream = io.StringIO(','.join(REQUIRED_COLUMNS) + '\n' + ','.join(['x'] * 8) + suffix + '\n')
    else:
        stream = io.StringIO(','.join(REQUIRED_COLUMNS) + '\nx,x\n')
    with pytest.raises(ValueError, match='number of action-plan columns'):
        load_action_plans(stream)


def test_missing_metadata_after_tie_cutoff_also_fails():
    report, = analyze_results([Q12Result('t', f'Q{i:02}', 3, 10) for i in range(1, 13)])
    library = load_action_plans()
    first_three = {s.source_q12_item for s in report.communication_signals[:3]}
    partial = ActionLibrary(tuple(p for p in library.plans if p.source_item in first_three))
    with pytest.raises(ValueError, match='metadata'):
        action_plans_for_report(report, partial)
