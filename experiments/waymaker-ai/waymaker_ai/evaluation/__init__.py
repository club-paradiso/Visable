"""Evaluation runner, metrics and baselines for the Waymaker benchmark.

Why this lives beside the benchmark and not inside the backend: the runner must
score the existing backend as a *baseline*, so it may never share the
backend's process state. Backend baselines run in a subprocess with the
backend's own interpreter; this package stays standard-library only.

Entry point: ``python -m waymaker_ai.evaluation.runner --help``. Method and
metric definitions: docs/ai/waymaker-genesis/12-evaluation-methodology.md.
"""
