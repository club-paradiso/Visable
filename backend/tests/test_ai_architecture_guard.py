"""The architecture guard must actually catch what it claims to.

A guard that passes on a clean tree proves nothing; it has to be shown failing
on each violation it exists to prevent. Every test here writes a deliberately
bad file into a temporary tree, points the guard's rule at it, and asserts the
violation is reported.

The `completion-result-unpacked-as-tuple` rule matters most: that is the exact
line shape that kept two production endpoints broken for their entire lives
while CI stayed green.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD = REPO_ROOT / "scripts" / "check_ai_architecture.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("check_ai_architecture", GUARD)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


class _RuleHarness(unittest.TestCase):
    """Run one rule against a synthetic backend tree."""

    def run_rule(self, rule, relative_path: str, source: str):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding="utf-8")

            saved_root, saved_backend = guard.REPO_ROOT, guard.BACKEND
            guard.REPO_ROOT, guard.BACKEND = root, root / "backend"
            try:
                findings = []
                rule(findings)
                return [f.rule for f in findings]
            finally:
                guard.REPO_ROOT, guard.BACKEND = saved_root, saved_backend


class ProviderHostRuleTests(_RuleHarness):
    def test_a_new_feature_calling_openrouter_directly_is_caught(self):
        rules = self.run_rule(
            guard.check_provider_hosts,
            "backend/services/some_new_feature.py",
            'URL = "https://openrouter.ai/api/v1/chat/completions"\n',
        )
        self.assertIn("provider-host-outside-adapter", rules)

    def test_a_groq_call_from_a_service_is_caught(self):
        rules = self.run_rule(
            guard.check_provider_hosts,
            "backend/services/other.py",
            'r = await client.post("https://api.groq.com/openai/v1/chat/completions")\n',
        )
        self.assertIn("provider-host-outside-adapter", rules)

    def test_prose_about_a_provider_in_a_comment_is_not_a_violation(self):
        """Documentation must stay writable; only real calls are the problem."""
        rules = self.run_rule(
            guard.check_provider_hosts,
            "backend/services/other.py",
            "# Historically this called openrouter.ai directly; it no longer does.\n",
        )
        self.assertEqual(rules, [])


class CredentialRuleTests(_RuleHarness):
    def test_reading_a_provider_key_outside_the_runtime_is_caught(self):
        rules = self.run_rule(
            guard.check_credential_reads,
            "backend/services/rogue.py",
            'import os\nKEY = os.environ.get("OPENROUTER_API_KEY")\n',
        )
        self.assertIn("credential-read-outside-runtime", rules)

    def test_getenv_is_caught_too(self):
        rules = self.run_rule(
            guard.check_credential_reads,
            "backend/services/rogue.py",
            'import os\nKEY = os.getenv("GROQ_API_KEY")\n',
        )
        self.assertIn("credential-read-outside-runtime", rules)

    def test_a_non_credential_env_read_is_fine(self):
        rules = self.run_rule(
            guard.check_credential_reads,
            "backend/services/fine.py",
            'import os\nMODE = os.environ.get("LAW_GROUNDING_MODE")\n',
        )
        self.assertEqual(rules, [])


class ModelIdentifierRuleTests(_RuleHarness):
    def test_a_hardcoded_model_id_outside_the_policy_is_caught(self):
        rules = self.run_rule(
            guard.check_model_identifiers,
            "backend/services/feature.py",
            'MODEL = "google/gemma-4-31b-it:free"\n',
        )
        self.assertIn("model-id-outside-policy", rules)

    def test_an_ordinary_path_string_is_not_mistaken_for_a_model(self):
        rules = self.run_rule(
            guard.check_model_identifiers,
            "backend/services/feature.py",
            'PATH = "docs/source-manuals/2026-07-31"\nURL = "api/v1/search"\n',
        )
        self.assertEqual(rules, [])


class RandomRoutingRuleTests(_RuleHarness):
    def test_selecting_openrouter_auto_is_caught(self):
        rules = self.run_rule(
            guard.check_random_routing,
            "backend/services/feature.py",
            'MODEL = "openrouter/auto"\n',
        )
        self.assertIn("random-model-routing", rules)

    def test_declaring_the_denylist_is_not_itself_a_violation(self):
        """The code forbidding random routing must not be punished for naming it."""
        rules = self.run_rule(
            guard.check_random_routing,
            "backend/services/feature.py",
            '_RANDOM_ROUTING_TOKENS = {"openrouter/auto", "openrouter/free"}\n',
        )
        self.assertEqual(rules, [])


class ResultContractRuleTests(_RuleHarness):
    """The defect that broke AI Overview and employment interpretation."""

    def test_the_exact_shipped_defect_is_caught(self):
        rules = self.run_rule(
            guard.check_result_contract_misuse,
            "backend/services/feature.py",
            "    text, attempt_meta = await _openrouter_complete_with_candidates(prompt)\n",
        )
        self.assertIn("completion-result-unpacked-as-tuple", rules)

    def test_it_is_caught_regardless_of_the_variable_names(self):
        rules = self.run_rule(
            guard.check_result_contract_misuse,
            "backend/services/feature.py",
            "    raw, meta = await _openrouter_complete_with_candidates(p, max_tokens=800)\n",
        )
        self.assertIn("completion-result-unpacked-as-tuple", rules)

    def test_the_correct_single_assignment_is_not_flagged(self):
        rules = self.run_rule(
            guard.check_result_contract_misuse,
            "backend/services/feature.py",
            "    result = await _openrouter_complete_with_candidates(prompt)\n",
        )
        self.assertEqual(rules, [])


class CommittedSecretRuleTests(_RuleHarness):
    def test_a_committed_openrouter_key_is_caught(self):
        rules = self.run_rule(
            guard.check_committed_secrets,
            "backend/services/oops.py",
            'KEY = "sk-or-v1-abcdef0123456789abcdef0123456789"\n',
        )
        self.assertIn("committed-secret", rules)

    def test_a_documented_variable_name_is_not_a_secret(self):
        """`.env.example` must stay useful — names are not values."""
        rules = self.run_rule(
            guard.check_committed_secrets,
            "backend/services/fine.py",
            "# Set OPENROUTER_API_KEY in deploy configuration.\nKEY_NAME = \"OPENROUTER_API_KEY\"\n",
        )
        self.assertEqual(rules, [])


class FrontendRuleTests(_RuleHarness):
    def test_a_browser_call_to_a_provider_is_caught(self):
        rules = self.run_rule(
            guard.check_frontend_provider_calls,
            "assets/js/rogue.js",
            "fetch('https://openrouter.ai/api/v1/chat/completions', {});\n",
        )
        self.assertIn("frontend-calls-provider-directly", rules)


class BackendOriginRuleTests(_RuleHarness):
    """The origin was written out six times, each with its own localhost logic."""

    ORIGIN = "https://web-production-14f9a.up.railway.app"

    def test_a_new_file_hardcoding_the_backend_origin_is_caught(self):
        rules = self.run_rule(
            guard.check_backend_origin_is_single_sourced,
            "assets/js/new-feature.js",
            f"var API = '{self.ORIGIN}';\n",
        )
        self.assertIn("backend-origin-duplicated", rules)

    def test_an_allowlisted_fallback_that_never_consults_the_resolver_is_caught(self):
        """A fallback that is the only path is not a fallback."""
        rules = self.run_rule(
            guard.check_backend_origin_is_single_sourced,
            "assets/js/unified-search.js",
            f"var DEFAULT_API_BASE = '{self.ORIGIN}';\n",
        )
        self.assertIn("backend-origin-fallback-is-primary", rules)

    def test_an_allowlisted_fallback_behind_the_resolver_is_accepted(self):
        rules = self.run_rule(
            guard.check_backend_origin_is_single_sourced,
            "assets/js/unified-search.js",
            "var DEFAULT_API_BASE = (window.VisableBackend && "
            f"window.VisableBackend.productionOrigin) || '{self.ORIGIN}';\n",
        )
        self.assertEqual(rules, [])

    def test_the_owning_file_may_hold_the_literal(self):
        rules = self.run_rule(
            guard.check_backend_origin_is_single_sourced,
            "assets/js/backend-origin.js",
            f"var PRODUCTION_ORIGIN = '{self.ORIGIN}';\n",
        )
        self.assertEqual(rules, [])


class SharedRuntimeRuleTests(unittest.TestCase):
    def test_the_backend_still_uses_the_shared_runtime(self):
        findings = []
        guard.check_ai_consumers_use_shared_runtime(findings)
        self.assertEqual([f.rule for f in findings], [],
                         "provider semantics have been forked out of the shared runtime")


class GuardEndToEndTests(unittest.TestCase):
    def test_the_guard_passes_on_the_current_tree(self):
        proc = subprocess.run([sys.executable, str(GUARD)], cwd=REPO_ROOT,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_the_guard_needs_no_credentials_or_network(self):
        env = {k: v for k, v in os.environ.items()
               if k not in {"OPENROUTER_API_KEY", "GROQ_API_KEY", "NVIDIA_API_KEY"}}
        proc = subprocess.run([sys.executable, str(GUARD), "--json"], cwd=REPO_ROOT,
                              capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 0)
        self.assertIn('"ok": true', proc.stdout)

    def test_the_json_report_lists_every_rule_that_ran(self):
        import json
        proc = subprocess.run([sys.executable, str(GUARD), "--json"], cwd=REPO_ROOT,
                              capture_output=True, text=True)
        report = json.loads(proc.stdout)
        self.assertEqual(len(report["rules_run"]), len(guard.RULES))


if __name__ == "__main__":
    unittest.main()
