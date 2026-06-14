"""Shared support for i18n frontend tests after the locale externalization.

Localized UI copy used to live inline in ``index.html`` inside a ``UI_TRANSLATIONS``
object literal. It now lives in external per-locale JSON packs under
``data/i18n/`` (``ko.json`` / ``en.json`` / ``zh-CN.json``), loaded at runtime by
``index.html`` via the manifest. These helpers let the i18n tests assert the *same*
localized copy against the external packs — without re-inlining anything — and keep
key parity strict across the actively supported locales.

Traditional Chinese (``zh-Hant``) is no longer a separately supported display
locale: the manifest aliases ``zhHant -> zh-CN``. Tests therefore assert against the
three supported packs (``ko``, ``en``, ``zh-CN``) rather than the four inline packs
the old tests expected. Simplified-Chinese copy is checked against ``zh-CN``.

Strict cross-locale key parity and official-term invariants are enforced
separately by ``scripts/check_i18n_coverage.mjs`` and
``scripts/check_official_terms.mjs`` (both part of the ``scripts/check_repo.sh``
gate); these helpers complement that by asserting the presence of specific
localized copy that individual frontend PRs introduced.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
I18N_DIR = REPO_ROOT / "data" / "i18n"

MANIFEST = json.loads((I18N_DIR / "manifest.json").read_text(encoding="utf-8"))
SUPPORTED_LOCALES = tuple(MANIFEST["supportedLocales"])  # ('ko', 'en', 'zh-CN')


def load_pack(locale: str) -> dict:
    """Return the parsed locale JSON pack for a supported locale."""
    return json.loads((I18N_DIR / MANIFEST["files"][locale]).read_text(encoding="utf-8"))


def load_packs() -> dict:
    """Return ``{locale: parsed pack}`` for every supported locale."""
    return {locale: load_pack(locale) for locale in SUPPORTED_LOCALES}


def _iter_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _iter_values(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_values(item)


def pack_blob(locale: str) -> str:
    """Newline-joined string values of a locale pack.

    Mirrors the old ``assertIn(text, index_html)`` substring checks, but scoped to
    a single language so a Korean string is asserted against the Korean pack, an
    English string against the English pack, and Simplified-Chinese against
    ``zh-CN`` — exactly the copy that used to be inline.
    """
    return "\n".join(_iter_values(load_pack(locale)))


def pack_blobs() -> dict:
    """Return ``{locale: pack_blob(locale)}`` for every supported locale."""
    return {locale: pack_blob(locale) for locale in SUPPORTED_LOCALES}


def localized(packs: dict, locale: str, key: str) -> str:
    """Localized value for ``key`` in ``locale`` as a string.

    Array values (e.g. ``aiActionLabels``) are joined with newlines so callers can
    use ``assertIn(substring, localized(...))`` uniformly. Raises ``KeyError`` if
    the key is missing from the pack, so a dropped key fails loudly instead of
    silently passing.
    """
    value = packs[locale][key]
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value)
