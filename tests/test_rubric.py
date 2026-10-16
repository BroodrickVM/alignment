"""Test observable heuristic behavior, configuration, and prototype integration."""
import math
import json
import pytest
from app.evaluation.rubric import CommunicationContext, Dimension, Rubric
from app.agents.personal_agent import PersonalAgent
from app.reports.report_generator import generate_report
from app.main import main
from app.rag.retriever import ResearchRetriever


def result(text, name, context=None):
    return next(r for r in Rubric().evaluate(text, context).results if r.dimension == name)


@pytest.mark.parametrize('text', ['', '  \n\t', None])
def test_empty_input_rejected(text):
    with pytest.raises(ValueError):
        Rubric().evaluate(text)


@pytest.mark.parametrize('text', ['Please review the proposal by Friday. Thanks.',
                                     'Do stuff somehow!!! YOU ARE USELESS.',
                                     'こんにちは、会議の予定を確認してください。',
                                     ' '.join(['word'] * 500)])
def test_all_scores_bounded_with_explanations(text):
    evaluation = Rubric().evaluate(text)
    assert len(evaluation.results) == 6
    assert evaluation.provisional
    assert 1 <= evaluation.overall_score <= 5
    assert all(1 <= r.score <= 5 and r.explanation and r.improvement_suggestion for r in evaluation.results)


def test_missing_context_is_disclosed():
    for name in ['Audience alignment', 'Purpose alignment']:
        r = result('Review the proposal.', name)
        assert r.score == 3
        assert 'not supplied' in r.explanation


def test_clarity_penalizes_long_vague_message():
    assert result(' '.join(['stuff'] * 40), 'Clarity').score < result('Please review the attached proposal.', 'Clarity').score


def test_consistency_flags_terms_without_claiming_contradiction():
    r = result('Approval is required, but feedback is optional.', 'Consistency')
    assert r.score == 3
    assert 'Possible opposing terms' in r.explanation


def test_actionability_distinguishes_action_owner_and_time():
    assert result('Please send your update; you can reply by Friday.', 'Actionability').score == 5
    assert result('The update is available.', 'Actionability').score == 2


def test_tone_flags_hostility():
    assert result('You are a useless idiot!!', 'Tone appropriateness').score < result('Please review this. Thanks.', 'Tone appropriateness').score


def test_purpose_overlap_is_explicitly_lexical():
    r = result('Please review the proposal.', 'Purpose alignment', CommunicationContext(purpose='Review proposal'))
    assert r.score == 4
    assert 'does not establish semantic alignment' in r.explanation


def test_custom_dimensions_and_weighted_mean():
    rubric = Rubric([Dimension('A', lambda t,c: (1,'Reason.','Suggestion.'), 1),
                     Dimension('B', lambda t,c: (5,'Reason.','Suggestion.'), 3)])
    evaluation = rubric.evaluate('Text.')
    assert evaluation.overall_score == 4
    assert [r.dimension for r in evaluation.results] == ['A', 'B']


@pytest.mark.parametrize('weight', [0, -1, math.inf, math.nan])
def test_invalid_weights_rejected(weight):
    with pytest.raises(ValueError):
        Rubric([Dimension('Custom', lambda t,c: (3,'Reason.','Suggestion.'), weight)])


@pytest.mark.parametrize('score', [0, 6, 3.5, True])
def test_invalid_custom_score_rejected(score):
    with pytest.raises(ValueError):
        Rubric([Dimension('Custom', lambda t,c: (score,'Reason.','Suggestion.'))]).evaluate('Text.')


def test_empty_and_duplicate_dimensions_rejected():
    d = Dimension('A', lambda t,c: (3,'Reason.','Suggestion.'))
    with pytest.raises(ValueError):
        Rubric([])
    with pytest.raises(ValueError):
        Rubric([d,d])


def test_report_preserves_original_and_marks_revision_as_template():
    original = 'The budget is $400; do not change it.'
    report = PersonalAgent().evaluate(original)
    rendered = generate_report(report)
    assert original in report.suggested_revision
    assert '[intended audience]' in rendered
    assert 'template only' in rendered
    assert 'Overall summary:' in rendered
    assert rendered.count('Dimension:') == 6


def test_cli_noninteractive(capsys):
    assert main(['--text', 'Please review the proposal.', '--purpose', 'Review proposal']) == 0
    assert 'Suggested revised communication:' in capsys.readouterr().out


def test_cli_interactive(monkeypatch, capsys):
    entries = iter(['Please review the proposal.', '', 'Team', 'Review proposal'])
    monkeypatch.setattr('builtins.input', lambda *args: next(entries))
    assert main([]) == 0
    assert 'Overall summary:' in capsys.readouterr().out


def test_retrieval_cannot_imply_loaded_evidence():
    with pytest.raises(NotImplementedError, match='no evidence'):
        ResearchRetriever().retrieve('clarity')


@pytest.mark.parametrize('context', [None, CommunicationContext('Project team', 'Review proposal')])
def test_personal_report_structured_output(context):
    original = 'Please review the proposal; you can reply by Friday. Thanks.'
    report = PersonalAgent().evaluate(original, context)
    output = report.to_dict()
    assert set(output) == {
        'dimensions', 'overall_alignment_score', 'overall_summary',
        'suggested_revised_communication', 'provisional',
    }
    assert [item['dimension'] for item in output['dimensions']] == [
        'Clarity', 'Consistency', 'Audience alignment', 'Purpose alignment',
        'Actionability', 'Tone appropriateness',
    ]
    for item, result in zip(output['dimensions'], report.evaluation.results):
        assert item == {
            'dimension': result.dimension,
            'score': result.score,
            'explanation': result.explanation,
            'improvement_suggestion': result.improvement_suggestion,
        }
        assert type(item['score']) is int and 1 <= item['score'] <= 5
        assert item['explanation'].strip()
        assert item['improvement_suggestion'].strip()
    assert output['overall_alignment_score'] == report.evaluation.overall_score
    assert output['overall_summary'] == report.evaluation.summary
    assert output['suggested_revised_communication'] == report.suggested_revision
    assert original in output['suggested_revised_communication']
    assert output['provisional'] is True
    assert json.loads(json.dumps(output)) == output


def test_rendered_report_includes_all_structured_fields():
    report = PersonalAgent().evaluate('Please send your update by Friday.')
    rendered = generate_report(report)
    for result in report.evaluation.results:
        assert f'Dimension: {result.dimension}\nScore: {result.score}/5' in rendered
        assert f'Explanation: {result.explanation}' in rendered
        assert f'Improvement suggestion: {result.improvement_suggestion}' in rendered
    assert f'Overall alignment score: {report.evaluation.overall_score:.2f}/5' in rendered
    assert f'Overall summary:\n{report.evaluation.summary}' in rendered
    assert f'Suggested revised communication:\n{report.suggested_revision}' in rendered


def test_structured_output_uses_custom_rubric_and_returns_independent_data():
    rubric = Rubric([Dimension('Custom', lambda t, c: (2, 'Reason.', 'Suggestion.'))])
    report = PersonalAgent(rubric).evaluate('Text.')
    output = report.to_dict()
    assert output['dimensions'][0]['dimension'] == 'Custom'
    assert output['overall_alignment_score'] == 2
    output['dimensions'][0]['score'] = 5
    assert report.to_dict()['dimensions'][0]['score'] == 2


def test_cli_includes_explicit_overall_alignment_score(capsys):
    assert main(['--text', 'Please review the proposal.']) == 0
    assert 'Overall alignment score:' in capsys.readouterr().out
