# Human review protocol

Labels are deliberately blank. These sheets compare model-generated plans, not complete deployed proposals; independently rate full proposals for the final assignment quality study. Read each job in synthetic_dev.json, then label support/partial/unsupported from the cited corpus. Do not look at automated verifier outputs first. Obtain separate judge labels, join by item ID, and run python -m evals.runners.judge_calibration evals/datasets/human_calibration.csv after at least 30 human labels.

For the blind panel, ask real classmates to choose A/B/tie and give a reason. Model order alternates; do not disclose it to raters. Never fill human cells with a model.
