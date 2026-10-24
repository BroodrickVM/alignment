# Synthetic scenario fixtures

Every team, score and period is fictional. The eleven CSV files cover equal
scores, one lower item, missing item rows, an item below the reporting count,
high/low uniform scores, multiple team/period groups, invalid score/count, blank
required data and duplicate records. Deliberately invalid files must never be
used as demonstration data. Tests load these files through the normal CSV loader
and run isolated dashboard copies; no source/sample file is overwritten.

Expected outputs and results: `output/validation/scenario_test_report.md`.
