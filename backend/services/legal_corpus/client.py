"""HTTP client for official Korean law sources (law.go.kr).

Two access paths, both official and both serving the same National Law
Information Center content:

1. **Public web endpoints** (default, no credential): the same pages a
   citizen reads — ``/법령/<법령명>`` (current-version discovery),
   ``lsInfoR.do`` (Korean body), ``engLsInfoR.do`` (English body),
   ``admRulInfoR.do`` (administrative-rule body) and ``flDownload.do``
   (annex files). These work without any API key.

2. **DRF Open API** (optional cross-check): ``lawSearch.do`` /
   ``lawService.do`` with ``target=law|eflaw|elaw|admrul``. Used only when
   the ``LAW_API_OC`` environment variable is set. The OC value is an
   identifier the *user* registers at open.law.go.kr together with the
   calling server IP/domain; an unregistered caller is rejected by the
   provider (verified 2026-11-04: ``OC=test`` from an unregistered host
   returns a user-verification failure). The OC is never logged, never
   written to the corpus, and never placed in any file.

Failure policy: errors are classified (``timeout`` / ``http`` /
``network`` / ``empty``) and raised as :class:`LawSourceError`. Callers
must treat a fetch failure as "source unavailable" and keep any existing
verified snapshot — never as "the law is gone" or "the old snapshot is
current".
"""

from __future__ import annotations

import http.client
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional, Tuple

BASE = "https://www.law.go.kr"
DRF_BASE = "http://www.law.go.kr/DRF"
USER_AGENT = "VisableLegalCorpus/1.0 (+https://github.com/club-paradiso/Visable)"

DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 5


class LawSourceError(RuntimeError):
    """A classified failure while talking to an official law source."""

    def __init__(self, kind: str, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.kind = kind  # timeout | http | network | empty | parse
        self.status = status


class LawGoKrClient:
    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        oc: Optional[str] = None,
        sleep=time.sleep,
    ):
        self.timeout = timeout
        self.retries = max(1, retries)
        # Credential comes from the environment only; never from files in
        # the repository and never hard-coded.
        self._oc = oc if oc is not None else (os.environ.get("LAW_API_OC") or None)
        self._sleep = sleep

    # -- low level ---------------------------------------------------------

    def _get(self, url: str, *, binary: bool = False):
        last_exc: Optional[Exception] = None
        for attempt in range(self.retries):
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = resp.read()
                if not data:
                    raise LawSourceError("empty", "empty response body")
                return data if binary else data.decode("utf-8", "replace")
            except LawSourceError:
                raise
            except urllib.error.HTTPError as exc:  # 4xx/5xx — do not retry 4xx
                if exc.code < 500:
                    raise LawSourceError("http", f"HTTP {exc.code}", status=exc.code) from exc
                last_exc = exc
            except TimeoutError as exc:
                last_exc = exc
            except urllib.error.URLError as exc:
                last_exc = exc
            except http.client.HTTPException as exc:
                # law.go.kr intermittently truncates chunked responses
                # (http.client.IncompleteRead). The partial body is never
                # used — the whole request is retried instead.
                last_exc = exc
            if attempt < self.retries - 1:
                self._sleep(min(2 ** attempt, 8))
        kind = "timeout" if isinstance(last_exc, TimeoutError) else "network"
        raise LawSourceError(kind, f"request failed after {self.retries} attempts: {type(last_exc).__name__}")

    # -- public web endpoints ----------------------------------------------

    def discover_current(self, title_ko: str) -> Tuple[str, str]:
        """Return ``(mst, effective_from_yyyymmdd)`` of the current version.

        The public ``/법령/<법령명>`` page frames the current version; its
        iframe URL carries the current ``lsiSeq`` (MST) and ``efYd``.
        """
        import re

        url = f"{BASE}/" + urllib.parse.quote(f"법령/{title_ko}")
        html = self._get(url)
        m = re.search(r"lsInfoP\.do\?lsiSeq=(\d+)&[^\"']*efYd=(\d{8})", html)
        if not m:
            raise LawSourceError("parse", f"could not discover current version for {title_ko}")
        return m.group(1), m.group(2)

    def fetch_law_body_html(self, mst: str, effective_from: str) -> str:
        """Full Korean body HTML for one version (본문 + 부칙 + 별표 목록)."""
        ef = effective_from.replace("-", "")
        return self._get(f"{BASE}/LSW/lsInfoR.do?lsiSeq={mst}&efYd={ef}&ancYnChk=0")

    def fetch_english_body_html(self, mst: str) -> str:
        """English body HTML for the version identified by ``mst``.

        law.go.kr serves an English *shell* (header only, no articles) when
        no translation exists for that version; callers must check for
        actual article content instead of trusting the HTTP 200.
        """
        return self._get(f"{BASE}/LSW/engLsInfoR.do?lsiSeq={mst}")

    def fetch_notice_body_html(self, adm_rul_seq: str) -> str:
        return self._get(f"{BASE}/LSW/admRulInfoR.do?admRulSeq={adm_rul_seq}")

    def download_annex_file(self, fl_seq: str, byl_cls_cd: str = "110201", ext: Optional[str] = None) -> bytes:
        q = f"gubun=&flSeq={fl_seq}&bylClsCd={byl_cls_cd}"
        if ext:
            q = f"gubun=&flExt={ext}&flSeq={fl_seq}&bylClsCd={byl_cls_cd}"
        return self._get(f"{BASE}/LSW/flDownload.do?{q}", binary=True)

    # -- DRF Open API (optional, credential-gated) ---------------------------

    @property
    def drf_available(self) -> bool:
        return bool(self._oc)

    def drf_search_json(self, target: str, query: str) -> str:
        """Raw DRF ``lawSearch.do`` response text (JSON). Requires OC.

        The OC travels as a query parameter by the provider's own design;
        this method never logs the URL.
        """
        if not self._oc:
            raise LawSourceError("empty", "LAW_API_OC is not set; DRF API unavailable")
        q = urllib.parse.urlencode(
            {"OC": self._oc, "target": target, "type": "JSON", "query": query, "display": 20}
        )
        return self._get(f"{DRF_BASE}/lawSearch.do?{q}")

    def drf_service_json(self, target: str, mst: str) -> str:
        """Raw DRF ``lawService.do`` response text (JSON). Requires OC."""
        if not self._oc:
            raise LawSourceError("empty", "LAW_API_OC is not set; DRF API unavailable")
        q = urllib.parse.urlencode({"OC": self._oc, "target": target, "type": "JSON", "MST": mst})
        return self._get(f"{DRF_BASE}/lawService.do?{q}")
