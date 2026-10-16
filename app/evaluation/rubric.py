"""Provisional rule-based rubric, NOT scientifically validated.

Scores indicate simple text signals, not communication quality measured against
research. Replace rules, dimensions, and weights after evidence review. No
research sources, language models, or external services are used here.
"""
from dataclasses import dataclass
import re
from typing import Callable, Optional, Sequence, Tuple


@dataclass(frozen=True)
class CommunicationContext:
    """Optional author-provided intent; absent context must not be inferred."""

    audience: str = ""
    purpose: str = ""


@dataclass(frozen=True)
class DimensionResult:
    """A bounded score with transparent reasoning and an improvement suggestion."""

    dimension: str
    score: int
    explanation: str
    improvement_suggestion: str


Scorer = Callable[[str, CommunicationContext], Tuple[int, str, str]]


@dataclass(frozen=True)
class Dimension:
    """Configurable dimension, scoring function, and positive summary weight."""

    name: str
    scorer: Scorer
    weight: float = 1.0


@dataclass(frozen=True)
class Evaluation:
    """Structured report; overall score is a heuristic weighted mean only."""

    results: Tuple[DimensionResult, ...]
    overall_score: float
    summary: str
    provisional: bool = True


def words(text: str):
    """Extract case-insensitive word tokens for transparent placeholder rules."""
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower())


def clarity(text, context):
    sentences = [s for s in re.split(r'[.!?\n]+', text) if words(s)]
    longest = max((len(words(s)) for s in sentences), default=0)
    vague = set(words(text)) & {'stuff', 'things', 'somehow', 'whatever'}
    score = 5 - (2 if longest > 35 else 1 if longest > 25 else 0) - min(2, len(vague))
    if len(words(text)) < 5:
        score -= 1
    return score, f'Longest sentence: {longest} words; vague token types: {len(vague)}. This does not assess meaning.', 'Use specific nouns and short sentences; supply context for brief messages.'


def consistency(text, context):
    tokens = set(words(text))
    pairs = [('approve', 'reject'), ('required', 'optional'), ('always', 'never')]
    found = [f'{a}/{b}' for a, b in pairs if a in tokens and b in tokens]
    return 3 if found else 4, ('Possible opposing terms: ' + ', '.join(found) + '. Review their context.' if found else 'No configured opposing-term pair found; logical consistency has not been verified.'), 'Check dates, commitments, and any opposing terms for actual contradictions.'


def audience_alignment(text, context):
    if not context.audience.strip():
        return 3, 'Audience was not supplied; 3 is a neutral placeholder, not evidence of alignment.', 'Specify the audience and what they already know.'
    return 3, f'Audience supplied: {context.audience}. This prototype cannot determine audience suitability.', 'Adapt detail and terminology to the stated audience; ask a representative reader to review.'


def purpose_alignment(text, context):
    if not context.purpose.strip():
        return 3, 'Purpose was not supplied; 3 is a neutral placeholder.', 'State the intended outcome before evaluating alignment.'
    significant = {w for w in words(context.purpose) if len(w) > 3}
    overlap = significant & set(words(text))
    return 4 if overlap else 3, f'Purpose keyword matches: {len(overlap)}. Lexical overlap does not establish semantic alignment.', 'State the intended outcome explicitly and check whether the message supports it.'


def actionability(text, context):
    tokens = set(words(text))
    action = bool(tokens & {'review', 'send', 'confirm', 'submit', 'approve', 'schedule', 'reply', 'complete'})
    owner = bool(tokens & {'you', 'i', 'we'})
    timing = bool(tokens & {'by', 'before', 'today', 'tomorrow', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday'})
    return 2 + int(action) + int(owner) + int(timing), f'Action token: {action}; owner pronoun: {owner}; timing token: {timing}. Informational messages may not need a request.', 'If action is needed, name the task, responsible person, and deadline.'


def tone(text, context):
    tokens = set(words(text))
    hostile = tokens & {'stupid', 'idiot', 'useless'}
    polite = bool(tokens & {'please', 'thanks', 'thank'})
    caps = any(len(w) > 3 and w.isupper() for w in re.findall(r'\b[A-Za-z]+\b', text))
    score = 4 + int(polite) - min(2, len(hostile)) - int(caps or '!!' in text)
    return score, f'Courtesy token: {polite}; flagged terms: {len(hostile)}; capitals or repeated exclamation marks: {caps or "!!" in text}. Context and culture are not assessed.', 'Use respectful, specific wording and review emphasis; acronyms may trigger false positives.'


DEFAULT_DIMENSIONS = (
    Dimension('Clarity', clarity),
    Dimension('Consistency', consistency),
    Dimension('Audience alignment', audience_alignment),
    Dimension('Purpose alignment', purpose_alignment),
    Dimension('Actionability', actionability),
    Dimension('Tone appropriateness', tone),
)


class Rubric:
    """Evaluate text using replaceable scoring functions and weights.

    Configure by passing a sequence of Dimension objects. Scores must be
    integer values from 1 to 5; invalid custom scores fail explicitly.
    """

    def __init__(self, dimensions: Optional[Sequence[Dimension]] = None):
        self.dimensions = tuple(DEFAULT_DIMENSIONS if dimensions is None else dimensions)
        if not self.dimensions:
            raise ValueError('At least one dimension is required.')
        if len({d.name for d in self.dimensions}) != len(self.dimensions):
            raise ValueError('Dimension names must be unique.')
        import math
        for d in self.dimensions:
            if not d.name.strip() or not callable(d.scorer) or not math.isfinite(d.weight) or d.weight <= 0:
                raise ValueError('Dimensions need a name, callable scorer, and finite positive weight.')

    def evaluate(self, communication: str, context: Optional[CommunicationContext] = None) -> Evaluation:
        """Return provisional dimension results and a weighted overall summary."""
        if not isinstance(communication, str) or not communication.strip():
            raise ValueError('Communication must contain non-whitespace text.')
        context = context or CommunicationContext()
        results = []
        for dimension in self.dimensions:
            score, explanation, suggestion = dimension.scorer(communication, context)
            if type(score) is not int or not 1 <= score <= 5:
                raise ValueError(f'{dimension.name}: scorer must return an integer from 1 to 5.')
            results.append(DimensionResult(dimension.name, score, explanation, suggestion))
        overall = sum(r.score * d.weight for r, d in zip(results, self.dimensions)) / sum(d.weight for d in self.dimensions)
        priorities = ', '.join(r.dimension for r in results if r.score == min(x.score for x in results))
        summary = f'Provisional heuristic average: {overall:.2f}/5. Review first: {priorities}. Scores are not scientifically validated; neutral context scores represent uncertainty.'
        return Evaluation(tuple(results), round(overall, 2), summary)
