"""Waymaker Legal Intelligence (WLIE) reference implementation (specs 06 and 07).

Modules, in dependency order: ``identity`` (exact titles, official hosts,
bundle records), ``citations`` (the citation scanner), ``injection``
(instruction-like text flags), ``adapters`` (the offline fixture adapter),
``temporal`` (candidate-version selection), ``verification`` (the seven
layers) and ``evidence_package`` (the bounded package a model receives).
Nothing is imported here, so importing one module never loads the others.
"""
