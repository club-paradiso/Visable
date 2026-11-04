"""Visable Legal Corpus — bilingual (KO/EN) immigration law repository.

Collects official Korean statute text and official English translation
*metadata* from the National Law Information Center (law.go.kr, Ministry of
Government Legislation) into a versioned, hash-verified corpus under
``backend/data/legal-corpus/``.

Safety invariants (see ``backend/data/legal-corpus/SOURCE_POLICY.md``):

* Only official sources are collected. No blog/wiki/AI-generated text is
  ever treated as statute text.
* Korean statute text is stored in full: statutes are excluded from
  copyright protection (Copyright Act Art. 7) and law.go.kr law information
  is open public data, free to use with attribution.
* English translations are KLRI (or ministry) copyrighted works whose
  redistribution is prohibited without a licence, so only translation
  metadata, article titles, per-article hashes and official links are
  stored — never the English body text.
* A failed verification never promotes data: unverified or stale material
  keeps an explicit non-verified status instead of being presented as
  current law.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "1.0.0"
