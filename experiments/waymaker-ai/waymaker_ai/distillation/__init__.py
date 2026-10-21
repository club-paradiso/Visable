"""Artemis training scaffolding: teacher policy, leakage guard, SFT builder, config checks.

Nothing here trains a model. These modules decide whether a training run may
start and what exactly it would see; they stay standard-library only so the
gates run on any machine, without torch. See
docs/ai/waymaker-genesis/13-artemis-experiment.md.
"""
