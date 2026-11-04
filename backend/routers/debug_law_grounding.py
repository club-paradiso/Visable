"""Law-grounding diagnostics: /api/debug/law-grounding*.

Moved from backend/paradiso_backend.py in Phase 6 of the rebuild (docs/rebuild/DECISIONS.md ADR-013).
The handler bodies are the original text; identifiers that resolve to module globals of
paradiso_backend are qualified as ``pb.<name>`` so the facade stays the single owner of state,
configuration and helpers, and tests that monkeypatch ``paradiso_backend.<name>`` keep working.
No ``from __future__ import annotations`` here on purpose: FastAPI must see the real annotation
objects (``pb.X`` is a closure variable of the factory, not a module global).
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request


def build_router(pb) -> APIRouter:
    """Routes of this group, registered in their original order. ``pb`` is the paradiso_backend module."""
    router = APIRouter()

    @router.get(
        "/api/debug/law-grounding/preflight",
        dependencies=[Depends(pb._debug_rate_limit)],
    )
    async def debug_law_grounding_preflight(question: Optional[str] = None) -> Dict[str, Any]:
        """Operator-safe law-grounding readiness preflight (no external call, no secrets).

        Reports the resolved mode, whether the API key / endpoint are configured
        (booleans only), whether a sample question would trigger grounding, the
        statutory query that would be issued, and explicit warning markers
        (LAW_GROUNDING_DISABLED / LAW_GROUNDING_AUDIT_ONLY / LAW_API_KEY_MISSING /
        LAW_API_ENDPOINT_MISSING). Useful even when external calls are disabled.
        """
        return pb.law_grounding_preflight(question or "")


    @router.get(
        "/api/debug/law-grounding/selftest",
        dependencies=[Depends(pb._debug_rate_limit)],
    )
    async def debug_law_grounding_selftest(question: Optional[str] = None) -> Dict[str, Any]:
        """Browser-friendly, one-call LIVE check of Open Law API grounding.

        Gated behind PARADISO_ENABLE_DEBUG_ENDPOINTS (default OFF -> 404): it can
        trigger a live outbound call and reveals deployment readiness detail that
        anonymous callers have no business probing (M-10).

        Unlike the preflight (which makes NO external call), this performs the same
        mode-gated, secret-free law.go.kr search the answer path uses — against a
        default statute query — and returns a plain-language verdict. An operator
        can open this single URL on the deployed host (e.g. Railway) to confirm
        whether law grounding actually works, distinguishing the common failure
        modes: grounding disabled, no credential, HTTP 403 (OC valid but the
        calling IP is not allow-listed on open.law.go.kr), unreachable host
        (outbound/egress blocked), timeout, or reachable-but-no-results.

        The OC value is NEVER returned; the source URL is sanitized at the tool
        boundary. Read-only; never raises (beyond the availability gate above).
        """
        pb._require_debug_endpoints_enabled()
        sample = (question or "").strip() or "출입국관리법"
        cfg = pb.load_grounding_config()
        result: Dict[str, Any] = {}

        if cfg.mode == "disabled":
            verdict = "DISABLED"
            message = ("법령 조회가 꺼져 있습니다. 환경변수 LAW_GROUNDING_MODE=audit "
                       "(또는 enabled)로 설정하세요.")
        elif not cfg.law_api_configured:
            verdict = "NO_CREDENTIAL"
            message = ("법령 API 인증값이 없습니다. open.law.go.kr에서 발급받은 OC를 "
                       "환경변수 LAW_API_OC에 설정하세요.")
        else:
            try:
                result = pb.search_laws(sample, config=cfg)
            except Exception:  # pragma: no cover - selftest must never crash
                result = {"status": "error", "error_type": "selftest_exception",
                          "raw_status": 0, "result_count": 0, "source_url": ""}
            status = result.get("status")
            error_type = result.get("error_type", "")
            raw_status = int(result.get("raw_status", 0) or 0)
            count = int(result.get("result_count", 0) or 0)
            if status == "ok" and count > 0:
                verdict = "WORKING"
                message = (f"✅ 정상 작동 — law.go.kr 응답 OK, 결과 {count}건. "
                           "실시간 법령 조회와 인용 검증이 켜졌습니다.")
            elif status == "ok":
                verdict = "REACHABLE_NO_RESULTS"
                message = ("⚠️ law.go.kr 연결은 되지만 이 질의에 결과가 없습니다. "
                           "다른 질의로 재시도하세요(예: ?question=출입국관리법).")
            elif error_type == "law_api_http_error" and raw_status == 403:
                verdict = "FORBIDDEN_403"
                message = ("❌ law.go.kr이 403(접근 거부)을 반환했습니다. OC는 전달됐지만 "
                           "호출 서버 IP가 open.law.go.kr에 허용 등록되지 않았을 가능성이 "
                           "큽니다. open.law.go.kr OPEN API 신청에서 이 서버의 아웃바운드 "
                           "IP를 허용 목록에 등록하세요.")
            elif error_type == "law_api_http_error":
                verdict = f"HTTP_{raw_status or 'ERROR'}"
                message = f"❌ law.go.kr이 HTTP {raw_status or '오류'}를 반환했습니다."
            elif error_type == "law_api_timeout":
                verdict = "TIMEOUT"
                message = "❌ law.go.kr 응답 시간 초과. 잠시 후 다시 시도하세요."
            elif error_type == "law_api_bad_response" and raw_status == 0:
                verdict = "UNREACHABLE"
                message = ("❌ law.go.kr에 네트워크로 연결되지 않습니다(아웃바운드/egress "
                           "차단 또는 DNS 문제). 배포 환경에서 www.law.go.kr 아웃바운드 "
                           "접근이 허용돼야 합니다.")
            else:
                verdict = "ERROR"
                message = f"❌ 법령 조회 실패: {error_type or 'unknown'}."

        return {
            "verdict": verdict,
            "message": message,
            "mode": cfg.mode,
            "law_api_credential_source": cfg.law_api_credential_source,
            "law_api_oc_configured": cfg.law_api_oc_configured,
            "law_api_key_fallback_configured": cfg.law_api_key_fallback_configured,
            "ready_for_external_calls": (
                cfg.mode in {"audit", "enabled"} and cfg.law_api_configured
            ),
            "sample_query": sample,
            "live_call_status": result.get("status", "not_attempted"),
            "live_error_type": result.get("error_type", ""),
            "live_http_status": int(result.get("raw_status", 0) or 0),
            "live_result_count": int(result.get("result_count", 0) or 0),
            "sanitized_source_url": result.get("source_url", ""),
        }


    @router.get(
        "/api/debug/law-grounding/netdiag",
        dependencies=[Depends(pb._debug_rate_limit)],
    )
    async def debug_law_grounding_netdiag() -> Dict[str, Any]:
        """Deep, read-only network diagnostic for the Open Law API host.

        Gated behind PARADISO_ENABLE_DEBUG_ENDPOINTS (default OFF -> 404): it
        returns resolved outbound IPs / network topology and triggers external
        probes, which must not be available to anonymous callers (M-10).

        When the selftest reports UNREACHABLE (HTTP status 0 / law_api_bad_response)
        the failure is below HTTP and could be DNS, a fully-blocked egress, the
        Korean government server refusing this server's (foreign / cloud) IP, a
        port-80-only block, or an HTTP-layer issue. This endpoint runs a small set
        of layered probes and returns the precise, secret-free cause plus a
        recommended remediation.

        The OC is NEVER sent in any probe and NEVER returned. Each probe is bounded
        by ``LAW_NETDIAG_TIMEOUT_SECONDS`` (default 4s). Never raises (beyond the
        availability gate above).
        """
        pb._require_debug_endpoints_enabled()
        import socket as _socket
        import urllib.error as _uerr
        import urllib.request as _ureq

        law_host = "www.law.go.kr"
        drf_path = "/DRF/lawSearch.do?target=law&type=JSON&query=test"  # no OC sent
        try:
            timeout = float(pb.os.environ.get("LAW_NETDIAG_TIMEOUT_SECONDS") or 4.0)
        except (TypeError, ValueError):
            timeout = 4.0
        timeout = timeout if timeout > 0 else 4.0

        cfg = pb.load_grounding_config()
        secrets = [s for s in (cfg.law_api_oc, cfg.law_api_key) if s]

        def _scrub(text: str) -> str:
            out = str(text or "")
            for secret in secrets:
                out = out.replace(secret, "[REDACTED]")
            return out[:300]

        def _tcp(host: str, port: int) -> Dict[str, Any]:
            try:
                with _socket.create_connection((host, port), timeout=timeout):
                    return {"ok": True, "detail": f"TCP connect {host}:{port} OK"}
            except Exception as exc:  # noqa: BLE001 - diagnostic must never raise
                return {"ok": False, "detail": _scrub(f"{type(exc).__name__}: {exc}")}

        def _http(url: str) -> Dict[str, Any]:
            req = _ureq.Request(
                url,
                headers={"User-Agent": "Paradiso-netdiag/1.0", "Accept": "*/*"},
            )
            try:
                with _ureq.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                    code = int(getattr(resp, "status", 0) or getattr(resp, "code", 0) or 0)
                    return {"ok": True, "http_status": code, "detail": f"HTTP {code}"}
            except _uerr.HTTPError as exc:
                # Any HTTP status (even 4xx/5xx) proves end-to-end reachability.
                code = int(getattr(exc, "code", 0) or 0)
                return {"ok": True, "http_status": code, "detail": _scrub(f"HTTPError {code}")}
            except Exception as exc:  # noqa: BLE001 - diagnostic must never raise
                return {"ok": False, "http_status": 0, "detail": _scrub(f"{type(exc).__name__}: {exc}")}

        # 1) DNS resolution of the law host (no connection made).
        try:
            infos = _socket.getaddrinfo(law_host, None)
            dns = {"ok": True, "resolved_ips": sorted({i[4][0] for i in infos})}
        except Exception as exc:  # noqa: BLE001
            dns = {"ok": False, "detail": _scrub(f"{type(exc).__name__}: {exc}")}

        # 2) Control egress to a neutral host by IP literal (no DNS dependency).
        egress = _tcp("1.1.1.1", 443)
        # 3) Raw TCP reachability of the law host on :80 and :443.
        law_tcp_80 = _tcp(law_host, 80)
        law_tcp_443 = _tcp(law_host, 443)
        # 4) HTTP(S) GET without the OC — distinguishes HTTP-layer from TCP-layer.
        law_http = _http(f"http://{law_host}{drf_path}")
        law_https = _http(f"https://{law_host}{drf_path}")

        diagnosis = pb.classify_law_host_reachability({
            "dns_ok": dns.get("ok", False),
            "egress_ok": egress.get("ok", False),
            "law_https_ok": law_https.get("ok", False),
            "law_http_ok": law_http.get("ok", False),
            "law_tcp_443_ok": law_tcp_443.get("ok", False),
            "law_tcp_80_ok": law_tcp_80.get("ok", False),
        })

        recommendations = {
            "DNS_FAILURE": ("배포 환경이 www.law.go.kr 도메인을 DNS로 해석하지 못합니다. "
                            "Railway DNS 설정/도메인 차단 여부를 확인하세요."),
            "EGRESS_BLOCKED": ("아웃바운드 자체가 막혀 있습니다(중립 호스트 1.1.1.1:443도 실패). "
                               "Railway 네트워킹/방화벽에서 외부 접속을 허용하세요."),
            "REACHABLE_HTTPS": ("www.law.go.kr에 HTTPS로 연결됩니다. 실시간 법령 호출은 이미 https를 "
                                "기본으로 사용하므로 전송 경로는 정상입니다. 직전 selftest 실패는 일시적이거나 "
                                "OC/호출 IP 허용 문제일 수 있으니 selftest 결과(403=IP 미등록)를 확인하세요."),
            "REACHABLE_HTTP": ("www.law.go.kr에 HTTP로 연결됩니다. 직전 selftest 실패는 일시적"
                               "(타임아웃 등)일 수 있으니 selftest를 다시 실행해 보세요."),
            "LAWGOKR_CONNECTION_REFUSED": ("중립 호스트는 되지만 www.law.go.kr은 80/443 모두 연결이 "
                                           "거부/차단됩니다. 한국 정부 서버가 해외·클라우드 IP의 접속을 "
                                           "막는 것으로 보입니다. 한국 소재 프록시를 거치도록 LAW_API_BASE_URL을 "
                                           "설정하거나, open.law.go.kr에 호출 IP 허용을 요청해야 합니다."),
            "HTTP_PORT_80_BLOCKED": ("443은 열리지만 80이 막힙니다. 실시간 법령 호출은 이미 https(443)를 "
                                     "기본으로 사용하므로 전송 경로는 정상입니다."),
            "HTTP_LAYER_ISSUE": ("TCP는 연결되지만 HTTP 응답을 받지 못합니다. 프록시/방화벽의 HTTP 검사 "
                                 "또는 서버 측 차단 가능성이 있습니다."),
        }

        return {
            "diagnosis": diagnosis,
            "recommendation": recommendations.get(diagnosis, ""),
            "law_host": law_host,
            "probe_timeout_seconds": timeout,
            "probes": {
                "dns_resolution": dns,
                "egress_control_1_1_1_1_443": egress,
                "law_tcp_80": law_tcp_80,
                "law_tcp_443": law_tcp_443,
                "law_http_get_no_oc": law_http,
                "law_https_get_no_oc": law_https,
            },
            "note": "이 진단은 OC 값을 전송하지 않으며 응답에도 포함하지 않습니다.",
        }


    @router.post(
        "/api/debug/law-grounding",
        dependencies=[Depends(pb._debug_rate_limit)],
    )
    async def debug_law_grounding(req: pb.DebugLawGroundingRequest) -> Dict[str, Any]:
        """Development/debug endpoint only, not a legal-advice production route.

        Gated behind PARADISO_ENABLE_DEBUG_ENDPOINTS (default OFF -> 404, M-10).
        Always includes a non-secret `preflight` readiness block. When a question
        is supplied, also returns the (mode-gated, non-crashing) grounding context.
        """
        pb._require_debug_endpoints_enabled()
        prompt = (req.question or req.text or "").strip()
        if not prompt:
            # Empty body keeps the documented 400 contract. Operators who want a
            # no-question readiness probe should use GET /api/debug/law-grounding/preflight.
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "empty_prompt",
                    "message": "Provide a non-empty 'question' or 'text', or use GET /api/debug/law-grounding/preflight.",
                },
            )
        pb.logger.info("debug-law-grounding request received (text_length=%d)", len(prompt))
        context = pb.build_law_grounding_context(prompt)
        context["preflight"] = pb.law_grounding_preflight(prompt)

        # Structured, secret-free evidence-pack view (Part F). Detects status /
        # question type, exposes the deterministic plan, and reports the normalized
        # evidence count + source confidence. Reuses ``context`` so it makes no extra
        # external call. OC / API-key values never appear; source URLs are sanitized.
        visa_hint = (req.visa_code or req.status or "").strip() or None
        visa_code_detected, _sub = pb._detect_visa_codes(visa_hint, None, prompt)
        task_type_detected = pb._detect_task_type(prompt)
        try:
            pack = pb.build_law_evidence_pack(
                prompt,
                visa_code=visa_code_detected,
                task_type=task_type_detected,
                law_context=context,
            )
        except Exception:  # pragma: no cover - debug view must never crash
            pack = None

        cfg = pb.load_grounding_config()
        context["evidence_pack"] = pack
        context["debug"] = {
            "mode": cfg.mode,
            "law_api_configured": cfg.law_api_configured,
            "law_api_oc_configured": cfg.law_api_oc_configured,
            "law_api_key_fallback_configured": cfg.law_api_key_fallback_configured,
            "law_api_credential_source": cfg.law_api_credential_source,
            "law_grounding_mode": cfg.mode,
            "detected_status": visa_code_detected,
            "task_type_detected": task_type_detected,
            "question_type": (pack or {}).get("question_type"),
            "risk_level": (pack or {}).get("risk_level"),
            "immigration_facts": (pack or {}).get("immigration_facts", {}),
            "legal_issue_types": (pack or {}).get("legal_issue_types", []),
            "proposed_activity_type": (pack or {}).get("proposed_activity_type", []),
            "source_plan": (pack or {}).get("source_plan", {}),
            "planned_law_queries": (pack or {}).get("planned_law_queries", []),
            "law_api_attempted": (pack or {}).get("law_api_attempted", False),
            "law_queries_attempted": (pack or {}).get("law_queries_attempted", []),
            "normalized_evidence_count": (pack or {}).get("law_evidence_count", 0),
            "error_type": (pack or {}).get("law_grounding_error", "") or context.get("error_type", ""),
            "parser_status": (pack or {}).get("parser_status", "") or context.get("parser_status", ""),
            "response_shape_hint": (pack or {}).get("response_shape_hint", "") or context.get("response_shape_hint", ""),
            "sanitized_source_url": (pack or {}).get("sanitized_source_url", "") or context.get("source_url", ""),
            "attempted_targets": (pack or {}).get("attempted_targets", []),
            "citation_verification_status": ((pack or {}).get("citation_verification") or context.get("citation_verification") or {}).get("status", ""),
            "law_grounding_status": (pack or {}).get("law_grounding_status"),
            "source_confidence_level": (pack or {}).get("source_confidence_level"),
            "answer_quality_mode": (pack or {}).get("answer_quality_mode"),
            "law_grounding_error": (pack or {}).get("law_grounding_error", ""),
            "legal_analysis": (pack or {}).get("legal_analysis"),
            "analysis_mode": (pack or {}).get("analysis_mode"),
            "main_issue": (pack or {}).get("main_issue"),
            "risk_posture": ((pack or {}).get("legal_analysis") or {}).get("risk_posture"),
            "confidence": ((pack or {}).get("legal_analysis") or {}).get("confidence"),
            "decisive_facts": ((pack or {}).get("legal_analysis") or {}).get("decisive_facts", []),
            "official_confirmation_questions": ((pack or {}).get("legal_analysis") or {}).get("official_confirmation_questions", []),
            "official_confirmation_questions_localized": (pack or {}).get("official_confirmation_questions_localized", []),
            "source_types_attempted": (pack or {}).get("source_types_attempted", []),
            "source_types_returned": (pack or {}).get("source_types_returned", []),
            "source_families_planned": (pack or {}).get("source_families_planned", []),
            "source_families_attempted": (pack or {}).get("source_families_attempted", []),
            "source_family_statuses": (pack or {}).get("source_family_statuses", {}),
            "source_family_result_counts": (pack or {}).get("source_family_result_counts", {}),
            "response_shape_hint_by_family": (pack or {}).get("response_shape_hint_by_family", {}),
            "parser_status_by_family": (pack or {}).get("parser_status_by_family", {}),
            "law_error_type_by_family": (pack or {}).get("law_error_type_by_family", {}),
            "sanitized_source_urls": (pack or {}).get("sanitized_source_urls", []),
            "normalized_evidence_count": (pack or {}).get("normalized_evidence_count", (pack or {}).get("law_evidence_count", 0)),
            "legal_analysis_confidence": ((pack or {}).get("legal_analysis") or {}).get("confidence"),
            "source_panel_state": (pack or {}).get("source_panel_state", ""),
            "direct_evidence_count": (pack or {}).get("direct_evidence_count", 0),
            "related_evidence_count": (pack or {}).get("related_evidence_count", 0),
            "analogical_evidence_count": (pack or {}).get("analogical_evidence_count", 0),
            "background_evidence_count": (pack or {}).get("background_evidence_count", 0),
            "missing_direct_authority": (pack or {}).get("missing_direct_authority", True),
            "source_state": (pack or {}).get("analysis_mode") or (pack or {}).get("law_grounding_status"),
            "answer_first_sentence": "",
            "first_sentence_quality_warning": "",
            "raw_code_default_ui_leak": False,
            # Source URLs are sanitized (OC removed) at the tool boundary before
            # they ever reach a caller; the debug view never reconstructs the OC.
            "source_urls_sanitized": True,
        }
        return context
    return router
