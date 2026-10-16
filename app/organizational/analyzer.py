"""Strict CSV validation and within-team, within-period descriptive analysis."""
import csv
from pathlib import Path
from .diagnostics import make_signal
from .mappings import DEFAULT_MAPPINGS
from .models import ITEM_IDS, OrganizationDiagnosticReport, Q12Result

HIERARCHY = {
    'Basic Needs': ITEM_IDS[:2], 'Individual': ITEM_IDS[2:6],
    'Teamwork': ITEM_IDS[6:10], 'Growth': ITEM_IDS[10:],
}
REQUIRED = {'team_id', 'item_id', 'mean_score', 'respondent_count'}
OPTIONAL = {'percentile_rank', 'period'}


def load_q12_csv(source):
    """Read a path or text stream. Reject the entire input on malformed data.

    Unknown columns are rejected to keep the input contract aggregate-only.
    Missing items are retained as gaps and reported by analyze_results.
    """
    if isinstance(source, (str, Path)):
        with open(source, newline='', encoding='utf-8-sig') as stream:
            return load_q12_csv(stream)
    try:
        reader = csv.DictReader(source, strict=True)
        headers = reader.fieldnames
        if not headers or len(headers) != len(set(headers)) or not REQUIRED <= set(headers) or set(headers) - REQUIRED - OPTIONAL:
            raise ValueError('CSV headers must contain the required columns and only supported optional columns.')
        results = []
        for row in reader:
            line = reader.line_num
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError('Incorrect number of columns.')
                values = {key: value.strip() for key, value in row.items()}
                results.append(Q12Result(
                    values['team_id'], values['item_id'], float(values['mean_score']),
                    int(values['respondent_count']),
                    float(values['percentile_rank']) if values.get('percentile_rank') else None,
                    values.get('period') or None,
                ))
            except (ValueError, TypeError) as error:
                raise ValueError(f'Malformed CSV row ending at line {line}: {error}') from error
    except csv.Error as error:
        raise ValueError(f'Malformed CSV: {error}') from error
    _group_results(results)
    return tuple(results)


def _group_results(results):
    groups, seen = {}, set()
    for result in results:
        if not isinstance(result, Q12Result):
            raise ValueError('Inputs must be validated Q12Result records.')
        key = (result.team_id, result.period, result.item_id)
        if key in seen:
            raise ValueError(f'Duplicate team/item/period record: {key}')
        seen.add(key)
        groups.setdefault((result.team_id, result.period), []).append(result)
    if not groups:
        raise ValueError('At least one aggregated record is required.')
    return groups


def analyze_results(results, mappings=None):
    """Return one report per team/period. Means weight available items equally.

    Opportunities are the bottom three items; communication signals include all
    mapped items at or below the third-lowest score, preserving cutoff ties.
    Rankings break ties by item ID and are relative, not quality thresholds.
    """
    configured = tuple(DEFAULT_MAPPINGS if mappings is None else mappings)
    if len({m.item_id for m in configured}) != len(configured):
        raise ValueError('Mapping item IDs must be unique.')
    mapping_by_item = {m.item_id: m for m in configured}
    reports = []
    for (team, period), records in _group_results(results).items():
        by_item = {r.item_id: r for r in records}
        ascending = sorted(records, key=lambda r: (r.mean_score, r.item_id))
        strengths = tuple(sorted(records, key=lambda r: (-r.mean_score, r.item_id))[:3])
        opportunities = tuple(ascending[:3])
        scores = {}
        for name, ids in HIERARCHY.items():
            available = [by_item[item].mean_score for item in ids if item in by_item]
            scores[name] = sum(available) / len(available) if available else None
        present = {name: score for name, score in scores.items() if score is not None}
        cutoff = opportunities[-1].mean_score
        signals = tuple(make_signal(r, mapping_by_item[r.item_id]) for r in ascending if r.mean_score <= cutoff and r.item_id in mapping_by_item)
        missing = tuple(item for item in ITEM_IDS if item not in by_item)
        limitations = [
            'Aggregated item means describe signals and patterns; they do not establish causes or individual experiences.',
            'Communication mappings and prompts are provisional, need evidence review, and are not a validated diagnostic instrument.',
            'Strengths and opportunities are relative within this team and period; no absolute good/bad thresholds are used. Cutoff ties may produce more than three communication signals.',
            'GrandMean and hierarchy means equally weight available item means, not respondent counts. Response distributions, uncertainty, and nonresponse bias cannot be assessed from these aggregates.',
            'Small groups may pose re-identification risks; apply an organization-approved minimum reporting size before sharing. No suppression policy is implemented.',
            'Percentile ranks, when supplied, are passed through only; their benchmark source and comparability are not verified. No benchmark percentile is inferred.',
        ]
        if missing:
            limitations.append('Missing items: ' + ', '.join(missing) + '. No values were imputed; incomplete summaries may not be comparable to complete summaries.')
        reports.append(OrganizationDiagnosticReport(
            team, sum(r.mean_score for r in records) / len(records), scores,
            strengths, opportunities, signals,
            tuple(dict.fromkeys(q for signal in signals for q in signal.manager_questions)),
            tuple(limitations), period, missing,
            tuple(name for name, score in present.items() if score == max(present.values())),
            tuple(name for name, score in present.items() if score == min(present.values())),
            {item: by_item[item].mean_score for item in ITEM_IDS if item in by_item},
        ))
    return tuple(reports)


def analyze_csv(source, mappings=None):
    return analyze_results(load_q12_csv(source), mappings)
