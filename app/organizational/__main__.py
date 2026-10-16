"""Run the Tool 2 synthetic demonstration: python -m app.organizational."""
from pathlib import Path

from .analyzer import analyze_csv
from .report import render_report


def main():
    """Analyze the bundled synthetic aggregates and print each team report."""
    sample_path = (
        Path(__file__).resolve().parents[2]
        / 'data' / 'organizational' / 'sample_q12_results.csv'
    )
    reports = analyze_csv(sample_path)
    print('SYNTHETIC INPUT DATA — fictional teams and scores for demonstration only.')
    print('Survey results are signals and hypotheses only; they do not establish causes.')
    print('Communication mappings are provisional and need evidence review.')
    print('No benchmark inference is made; percentile ranks are used only when supplied.')
    print()
    print('\n\n'.join(render_report(report) for report in reports))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
