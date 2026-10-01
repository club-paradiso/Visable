"""Contract tests for the shared AI runtime.

Covers the provider failure matrix (§25 of the architecture brief): every HTTP
status and transport failure a provider can produce, the fallback decisions
each one triggers, the cooldown circuit breaker, task-role model resolution,
and the result contract.

Fully offline: the runtime performs no HTTP itself, so the adapter is a plain
async function that raises whatever the test wants.
"""

from __future__ import annotations

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services import ai_runtime as rt  # noqa: E402


def run(coro):
    return asyncio.run(coro)


def adapter_always(text: str):
    async def _adapter(prompt, model, max_tokens):
        return text
    return _adapter


def adapter_raises(*errors: rt.AIError):
    """Raise the given errors in order, then succeed."""
    queue = list(errors)

    async def _adapter(prompt, model, max_tokens):
        if queue:
            raise queue.pop(0)
        return "ok answer"
    return _adapter


class ErrorClassificationTests(unittest.TestCase):
    """Each status must land on the taxonomy entry that drives the right action."""

    def test_429_is_rate_limited_and_retryable(self):
        e = rt.classify_provider_error(429, "Rate limit exceeded")
        self.assertEqual(e, rt.AIErrorType.RATE_LIMITED)
        self.assertTrue(rt.is_retryable(e))

    def test_429_inside_a_larger_number_is_not_a_rate_limit(self):
        # A 400 that mentions "4290 tokens" must stay a request error; reading
        # it as a rate limit put a healthy model on cooldown for later users.
        e = rt.classify_provider_error(400, "This request needs 14290 tokens; context length exceeded")
        self.assertEqual(e, rt.AIErrorType.INVALID_REQUEST)
        self.assertFalse(rt.is_retryable(e))
        self.assertEqual(
            rt.classify_provider_error(None, "upstream returned 429"),
            rt.AIErrorType.RATE_LIMITED,
        )

    def test_401_is_credentials_and_never_retried(self):
        e = rt.classify_provider_error(401, "No auth credentials found")
        self.assertEqual(e, rt.AIErrorType.INVALID_PROVIDER_CREDENTIALS)
        self.assertFalse(rt.is_retryable(e))
        self.assertTrue(rt.is_fatal(e))

    def test_403_is_credentials_not_a_transient_outage(self):
        # Regression guard: a 403 falling into the generic 5xx/retry bucket
        # would burn the whole candidate chain against a broken account.
        self.assertEqual(
            rt.classify_provider_error(403, "Forbidden"),
            rt.AIErrorType.INVALID_PROVIDER_CREDENTIALS,
        )

    def test_404_is_an_invalid_model_and_skips_that_candidate_only(self):
        e = rt.classify_provider_error(404, "model not found")
        self.assertEqual(e, rt.AIErrorType.INVALID_MODEL)
        self.assertTrue(rt.should_skip_model(e))
        self.assertFalse(rt.is_fatal(e))

    def test_no_endpoints_is_model_unavailable_not_a_dead_provider(self):
        e = rt.classify_provider_error(200, "No endpoints found for this model")
        self.assertEqual(e, rt.AIErrorType.MODEL_UNAVAILABLE)
        self.assertTrue(rt.should_skip_model(e))

    def test_500_502_503_are_overloaded_and_retryable(self):
        for status in (500, 502, 503):
            with self.subTest(status=status):
                e = rt.classify_provider_error(status, "")
                self.assertEqual(e, rt.AIErrorType.PROVIDER_OVERLOADED)
                self.assertTrue(rt.is_retryable(e))

    def test_no_healthy_upstream_is_overloaded(self):
        self.assertEqual(
            rt.classify_provider_error(503, "no healthy upstream"),
            rt.AIErrorType.PROVIDER_OVERLOADED,
        )

    def test_504_and_timeout_text_are_timeout(self):
        self.assertEqual(rt.classify_provider_error(504, ""), rt.AIErrorType.TIMEOUT)
        self.assertEqual(
            rt.classify_provider_error(None, "request timed out after 60s"),
            rt.AIErrorType.TIMEOUT,
        )
        self.assertTrue(rt.is_retryable(rt.AIErrorType.TIMEOUT))

    def test_network_failure_is_distinct_from_timeout(self):
        e = rt.classify_provider_error(None, "connect error: DNS resolution failed")
        self.assertEqual(e, rt.AIErrorType.NETWORK_FAILURE)
        self.assertTrue(rt.is_retryable(e))

    def test_malformed_json_is_a_provider_failure_not_a_crash(self):
        e = rt.classify_provider_error(200, "", "openrouter_bad_response")
        self.assertEqual(e, rt.AIErrorType.MALFORMED_PROVIDER_RESPONSE)
        self.assertTrue(rt.is_retryable(e))

    def test_empty_completion_is_its_own_state(self):
        e = rt.classify_provider_error(200, "", "openrouter_empty_completion")
        self.assertEqual(e, rt.AIErrorType.EMPTY_COMPLETION)
        self.assertTrue(rt.is_retryable(e))

    def test_safety_rejection_is_never_reported_as_provider_offline(self):
        e = rt.classify_provider_error(451, "flagged by content policy")
        self.assertEqual(e, rt.AIErrorType.SAFETY_REJECTION)
        self.assertFalse(rt.is_retryable(e))
        self.assertTrue(rt.is_fatal(e))

    def test_400_is_an_invalid_request_and_stops_the_chain(self):
        e = rt.classify_provider_error(400, "invalid request")
        self.assertEqual(e, rt.AIErrorType.INVALID_REQUEST)
        self.assertTrue(rt.is_fatal(e))

    def test_not_configured_is_distinct_from_unavailable(self):
        # "We never had a provider" and "the provider failed" are different
        # operator problems and must never be collapsed.
        self.assertEqual(
            rt.classify_provider_error(503, "", "openrouter_not_configured"),
            rt.AIErrorType.PROVIDER_NOT_CONFIGURED,
        )

    def test_an_unrecognized_failure_is_labelled_unknown_not_guessed(self):
        self.assertEqual(
            rt.classify_provider_error(None, "something odd happened"),
            rt.AIErrorType.UNKNOWN_PROVIDER_ERROR,
        )


class CooldownTests(unittest.TestCase):
    def test_a_marked_model_is_cooling_down(self):
        reg = rt.ModelCooldownRegistry(300.0)
        reg.mark("a/b", now=1000.0)
        self.assertIn("a/b", reg.cooling_down(now=1100.0))

    def test_cooldown_expires(self):
        reg = rt.ModelCooldownRegistry(300.0)
        reg.mark("a/b", now=1000.0)
        self.assertNotIn("a/b", reg.cooling_down(now=1400.0))

    def test_zero_seconds_disables_the_breaker_entirely(self):
        reg = rt.ModelCooldownRegistry(0.0)
        reg.mark("a/b")
        self.assertFalse(reg.enabled)
        self.assertEqual(reg.cooling_down(), [])

    def test_metadata_is_non_secret_and_serializable(self):
        reg = rt.ModelCooldownRegistry(60.0)
        meta = reg.metadata()
        self.assertEqual(set(meta), {
            "cooling_down_models", "model_cooldown_seconds", "cooldown_enabled",
            "free_tier_quota_window", "free_tier_quota_retry_after_seconds"})


class FreeTierQuotaTests(unittest.TestCase):
    """OpenRouter's free-models-per-min / -per-day 429 is shared by every :free id."""

    DAY = "Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day"

    def test_window_is_read_from_the_provider_message(self):
        self.assertEqual(rt.free_tier_quota_window(self.DAY), "day")
        self.assertEqual(rt.free_tier_quota_window("Rate limit exceeded: free-models-per-day-high-balance."), "day")
        self.assertEqual(rt.free_tier_quota_window('{"error":{"message":"Rate limit exceeded: free-models-per-min."}}'), "minute")
        self.assertIsNone(rt.free_tier_quota_window("google/gemma:free is temporarily rate-limited upstream"))
        self.assertIsNone(rt.free_tier_quota_window(None))

    def test_block_covers_every_free_id_and_nothing_else(self):
        reg = rt.ModelCooldownRegistry(300.0, free_tier_day_seconds=3600.0)
        reg.mark_free_tier_quota("day", now=1000.0)
        self.assertTrue(reg.is_cooling("x/any:free", now=1001.0))
        self.assertFalse(reg.is_cooling("x/paid", now=1001.0))
        self.assertEqual(reg.partition(["a:free", "b", "c:free"], now=1001.0), (["b"], ["a:free", "c:free"]))
        self.assertFalse(reg.is_cooling("x/any:free", now=1000.0 + 3600.0))

    def test_minute_window_is_short_and_never_shortens_a_daily_block(self):
        reg = rt.ModelCooldownRegistry(300.0)
        reg.mark_free_tier_quota("minute", now=1000.0)
        self.assertTrue(reg.free_tier_blocked(now=1059.0))
        self.assertFalse(reg.free_tier_blocked(now=1060.0))
        reg.mark_free_tier_quota("day", now=2000.0)
        reg.mark_free_tier_quota("minute", now=2001.0)
        self.assertTrue(reg.free_tier_blocked(now=2100.0))

    def test_disabled_breaker_never_blocks(self):
        reg = rt.ModelCooldownRegistry(0.0)
        reg.mark_free_tier_quota("day")
        self.assertFalse(reg.is_cooling("a:free"))

    def test_runtime_skips_remaining_free_candidates_after_a_shared_quota_429(self):
        calls = []

        async def adapter(prompt, model, max_tokens):
            calls.append(model)
            if model.endswith(":free"):
                raise rt.AIError(rt.AIErrorType.RATE_LIMITED, self.DAY, status=429)
            return "paid answer"

        runtime = rt.AIRuntime(adapter=adapter, cooldowns=rt.ModelCooldownRegistry(300.0))
        r = run(runtime.complete("q", candidates=["a:free", "b:free", "c/paid"]))
        self.assertTrue(r.ok)
        self.assertEqual(calls, ["a:free", "c/paid"])
        self.assertEqual(r.skipped_models_due_to_cooldown, ["b:free"])
        # The next request does not touch any free id while the block lasts.
        calls.clear()
        r2 = run(runtime.complete("q", candidates=["d:free", "e:free"]))
        self.assertFalse(r2.ok)
        self.assertEqual(calls, [])
        self.assertEqual(r2.error_type, rt.AIErrorType.ALL_CANDIDATES_COOLING_DOWN.value)

    def test_a_per_model_429_keeps_trying_other_free_candidates(self):
        calls = []

        async def adapter(prompt, model, max_tokens):
            calls.append(model)
            if model == "a:free":
                raise rt.AIError(rt.AIErrorType.RATE_LIMITED, "a:free is temporarily rate-limited upstream", status=429)
            return "ok"

        runtime = rt.AIRuntime(adapter=adapter, cooldowns=rt.ModelCooldownRegistry(300.0))
        r = run(runtime.complete("q", candidates=["a:free", "b:free"]))
        self.assertTrue(r.ok)
        self.assertEqual(calls, ["a:free", "b:free"])
        self.assertFalse(runtime.cooldowns.free_tier_blocked())


class RuntimeFallbackTests(unittest.TestCase):
    def _runtime(self, adapter, cooldown=300.0):
        return rt.AIRuntime(adapter=adapter, cooldowns=rt.ModelCooldownRegistry(cooldown))

    def test_a_successful_first_candidate_reports_no_fallback(self):
        r = run(self._runtime(adapter_always("hello")).complete(
            "q", candidates=["m/1", "m/2"]))
        self.assertTrue(r.ok)
        self.assertEqual(r.answer, "hello")
        self.assertEqual(r.final_model, "m/1")
        self.assertFalse(r.model_fallback_used)

    def test_a_rate_limited_model_falls_through_to_the_next_candidate(self):
        adapter = adapter_raises(rt.AIError(rt.AIErrorType.RATE_LIMITED, status=429))
        r = run(self._runtime(adapter).complete("q", candidates=["m/1", "m/2"]))
        self.assertTrue(r.ok)
        self.assertEqual(r.final_model, "m/2")
        self.assertTrue(r.model_fallback_used)
        self.assertEqual(r.attempted_models, ["m/1", "m/2"])

    def test_a_rate_limited_model_is_put_on_cooldown(self):
        adapter = adapter_raises(rt.AIError(rt.AIErrorType.RATE_LIMITED, status=429))
        runtime = self._runtime(adapter)
        run(runtime.complete("q", candidates=["m/1", "m/2"]))
        self.assertIn("m/1", runtime.cooldowns.cooling_down())

    def test_an_invalid_model_skips_that_candidate_without_a_cooldown(self):
        adapter = adapter_raises(rt.AIError(rt.AIErrorType.INVALID_MODEL, status=404))
        runtime = self._runtime(adapter)
        r = run(runtime.complete("q", candidates=["bad/slug", "m/2"]))
        self.assertTrue(r.ok)
        self.assertEqual(r.final_model, "m/2")
        # A wrong slug is not transient; a cooldown would be meaningless.
        self.assertNotIn("bad/slug", runtime.cooldowns.cooling_down())

    def test_bad_credentials_stop_the_chain_immediately(self):
        """The whole point of the fatal class: don't burn every candidate."""
        adapter = adapter_raises(
            rt.AIError(rt.AIErrorType.INVALID_PROVIDER_CREDENTIALS, status=401))
        r = run(self._runtime(adapter).complete("q", candidates=["m/1", "m/2", "m/3"]))
        self.assertFalse(r.ok)
        self.assertEqual(r.attempted_models, ["m/1"])
        self.assertEqual(r.error_type, "invalid_provider_credentials")
        self.assertFalse(r.retryable)

    def test_a_safety_rejection_stops_the_chain_and_keeps_its_own_label(self):
        adapter = adapter_raises(rt.AIError(rt.AIErrorType.SAFETY_REJECTION, status=451))
        r = run(self._runtime(adapter).complete("q", candidates=["m/1", "m/2"]))
        self.assertFalse(r.ok)
        self.assertEqual(r.error_type, "safety_rejection")
        self.assertEqual(len(r.attempted_models), 1)

    def test_an_empty_completion_falls_through_rather_than_returning_nothing(self):
        adapter = adapter_raises(rt.AIError(rt.AIErrorType.EMPTY_COMPLETION))
        r = run(self._runtime(adapter).complete("q", candidates=["m/1", "m/2"]))
        self.assertTrue(r.ok)
        self.assertEqual(r.final_model, "m/2")

    def test_a_malformed_response_falls_through_rather_than_crashing(self):
        adapter = adapter_raises(rt.AIError(rt.AIErrorType.MALFORMED_PROVIDER_RESPONSE))
        r = run(self._runtime(adapter).complete("q", candidates=["m/1", "m/2"]))
        self.assertTrue(r.ok)

    def test_every_candidate_failing_reports_all_candidates_failed(self):
        async def always_429(prompt, model, max_tokens):
            raise rt.AIError(rt.AIErrorType.RATE_LIMITED, status=429)

        r = run(self._runtime(always_429).complete("q", candidates=["m/1", "m/2"]))
        self.assertFalse(r.ok)
        self.assertTrue(r.all_candidates_failed)
        self.assertTrue(r.retryable)
        self.assertEqual(r.upstream_statuses, [429, 429])

    def test_all_candidates_cooling_down_does_not_hammer_the_provider(self):
        calls = []

        async def counting(prompt, model, max_tokens):
            calls.append(model)
            return "x"

        runtime = self._runtime(counting)
        runtime.cooldowns.mark("m/1")
        runtime.cooldowns.mark("m/2")
        r = run(runtime.complete("q", candidates=["m/1", "m/2"]))
        self.assertFalse(r.ok)
        self.assertEqual(r.error_type, "all_candidates_cooling_down")
        self.assertEqual(calls, [], "a cooling-down chain must issue zero requests")
        self.assertTrue(r.retryable)

    def test_a_requested_model_is_tried_first_without_dropping_the_chain(self):
        r = run(self._runtime(adapter_always("x")).complete(
            "q", candidates=["m/1", "m/2"], requested_model="m/9"))
        self.assertEqual(r.final_model, "m/9")
        self.assertEqual(r.model_candidates, ["m/9", "m/1", "m/2"])

    def test_an_empty_chain_is_reported_as_not_configured(self):
        r = run(self._runtime(adapter_always("x")).complete("q", candidates=[]))
        self.assertFalse(r.ok)
        self.assertEqual(r.error_type, "provider_not_configured")


class ResultContractTests(unittest.TestCase):
    def test_an_ai_result_cannot_be_unpacked_like_a_tuple(self):
        """The exact defect this runtime was built after.

        A 16-key dict unpacks to its KEYS and raises ValueError, which a broad
        `except Exception` can swallow into a fake outage. A dataclass raises
        TypeError, which no reasonable handler mistakes for a provider failure.
        """
        result = rt.AIResult(ok=True, answer="hi")
        with self.assertRaises(TypeError):
            a, b = result  # noqa: F841

    def test_legacy_round_trip_preserves_every_field(self):
        original = rt.AIResult(
            ok=True, answer="a", provider="openrouter", primary_model="m/1",
            final_model="m/2", model_candidates=["m/1", "m/2"],
            attempted_models=["m/1", "m/2"], model_fallback_used=True,
            upstream_statuses=[429],
        )
        restored = rt.AIResult.from_legacy_dict(original.to_legacy_dict(), provider="openrouter")
        self.assertEqual(restored.answer, "a")
        self.assertEqual(restored.final_model, "m/2")
        self.assertTrue(restored.model_fallback_used)
        self.assertEqual(restored.upstream_statuses, [429])

    def test_telemetry_never_carries_the_prompt_or_a_credential(self):
        result = rt.AIResult(ok=True, answer="secret answer text", provider="openrouter",
                             final_model="m/1")
        blob = str(result.telemetry())
        self.assertNotIn("secret answer text", blob)
        self.assertNotIn("Bearer", blob)
        self.assertNotIn("api_key", blob.lower())

    def test_text_is_always_a_string_even_on_failure(self):
        self.assertEqual(rt.AIResult(ok=False).text, "")


class TaskRoleTests(unittest.TestCase):
    def test_every_role_resolves_to_a_non_empty_candidate_chain(self):
        for role in rt.TaskRole:
            with self.subTest(role=role):
                plan = rt.resolve_task_models(role)
                self.assertTrue(plan["candidates"], f"{role} has no candidates")
                self.assertEqual(plan["primary"], plan["candidates"][0])

    def test_enforcement_structured_role_uses_dedicated_bounded_chain(self):
        plan = rt.resolve_task_models(rt.TaskRole.ENFORCEMENT_STRUCTURED)
        fast = rt.resolve_task_models(rt.TaskRole.FAST_FINAL_ANSWER)["candidates"]
        verifier = rt.resolve_task_models(rt.TaskRole.VERIFIER)["candidates"][0]
        self.assertEqual(plan["task_role"], "enforcement_structured")
        self.assertEqual(
            plan["candidates"],
            ["google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-3-super-120b-a12b:free"],
        )
        self.assertEqual(len(plan["candidates"]), 2)
        self.assertNotEqual(plan["candidates"], fast)
        self.assertEqual(plan["candidates"][1], verifier)

    def test_an_unknown_role_falls_back_to_the_final_answer_chain(self):
        plan = rt.resolve_task_models("not-a-real-role")
        self.assertEqual(plan["task_role"], rt.TaskRole.FINAL_ANSWER.value)

    def test_a_short_extraction_task_leads_with_a_fast_model(self):
        fast = rt.resolve_task_models(rt.TaskRole.FAST_FINAL_ANSWER)["candidates"]
        extractor = rt.resolve_task_models(rt.TaskRole.FACT_EXTRACTOR)["candidates"]
        self.assertEqual(extractor[0], fast[0])

    def test_an_extraction_task_still_has_a_deeper_fallback(self):
        """A structured extraction that cannot run at all is the worst outcome."""
        fast = rt.resolve_task_models(rt.TaskRole.FAST_FINAL_ANSWER)["candidates"]
        extractor = rt.resolve_task_models(rt.TaskRole.FACT_EXTRACTOR)["candidates"]
        self.assertGreater(len(extractor), len(fast))

    def test_candidate_chains_never_contain_random_routing(self):
        for role in rt.TaskRole:
            for model in rt.resolve_task_models(role)["candidates"]:
                with self.subTest(role=role, model=model):
                    self.assertNotIn(model.lower(), {"openrouter/auto", "openrouter/free"})
                    self.assertFalse(model.lower().endswith("/auto"))

    def test_candidate_chains_have_no_duplicates(self):
        for role in rt.TaskRole:
            chain = rt.resolve_task_models(role)["candidates"]
            with self.subTest(role=role):
                self.assertEqual(len(chain), len(set(chain)))

    def test_a_final_answer_chain_is_deep_enough_to_survive_two_outages(self):
        chain = rt.resolve_task_models(rt.TaskRole.FINAL_ANSWER)["candidates"]
        self.assertGreaterEqual(len(chain), 3)


class ProviderConfigurationTests(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in
                       ("OPENROUTER_API_KEY", "GROQ_API_KEY", "ALLOW_GROQ_FALLBACK")}
        for key in self._saved:
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_no_provider_is_reported_as_none(self):
        self.assertEqual(rt.provider_configuration()["active_provider"], "none")

    def test_openrouter_takes_precedence_when_configured(self):
        os.environ["OPENROUTER_API_KEY"] = "x"
        os.environ["GROQ_API_KEY"] = "y"
        os.environ["ALLOW_GROQ_FALLBACK"] = "true"
        self.assertEqual(rt.provider_configuration()["active_provider"], "openrouter")

    def test_groq_answers_only_when_explicitly_allowed(self):
        os.environ["GROQ_API_KEY"] = "y"
        self.assertEqual(rt.provider_configuration()["active_provider"], "none")
        os.environ["ALLOW_GROQ_FALLBACK"] = "true"
        self.assertEqual(rt.provider_configuration()["active_provider"], "groq")

    def test_the_configuration_snapshot_contains_no_credential_values(self):
        os.environ["OPENROUTER_API_KEY"] = "sk-or-v1-super-secret-value"
        blob = str(rt.provider_configuration())
        self.assertNotIn("super-secret-value", blob)
        self.assertNotIn("sk-or-v1", blob)

    def test_every_task_role_is_reported_for_operators(self):
        roles = rt.provider_configuration()["task_roles"]
        self.assertEqual(set(roles), {r.value for r in rt.TaskRole})


if __name__ == "__main__":
    unittest.main()
