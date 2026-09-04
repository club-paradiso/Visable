from pathlib import Path

path = Path('backend/tests/test_ai_runtime.py')
text = path.read_text()
old = '''    def test_enforcement_structured_role_uses_fast_chain_then_verifier(self):
        plan = rt.resolve_task_models(rt.TaskRole.ENFORCEMENT_STRUCTURED)
        fast = rt.resolve_task_models(rt.TaskRole.FAST_FINAL_ANSWER)["candidates"]
        verifier = rt.resolve_task_models(rt.TaskRole.VERIFIER)["candidates"][0]
        self.assertEqual(plan["task_role"], "enforcement_structured")
        self.assertEqual(plan["candidates"][:len(fast)], fast)
        self.assertIn(verifier, plan["candidates"])
'''
new = '''    def test_enforcement_structured_role_uses_dedicated_bounded_chain(self):
        plan = rt.resolve_task_models(rt.TaskRole.ENFORCEMENT_STRUCTURED)
        fast = rt.resolve_task_models(rt.TaskRole.FAST_FINAL_ANSWER)["candidates"]
        verifier = rt.resolve_task_models(rt.TaskRole.VERIFIER)["candidates"][0]
        self.assertEqual(plan["task_role"], "enforcement_structured")
        self.assertEqual(
            plan["candidates"],
            ["google/gemma-4-26b-a4b-it:free", "openai/gpt-oss-20b:free"],
        )
        self.assertEqual(len(plan["candidates"]), 2)
        self.assertNotEqual(plan["candidates"], fast)
        self.assertNotIn(verifier, plan["candidates"])
'''
if text.count(old) != 1:
    raise SystemExit('expected stale enforcement role test exactly once')
path.write_text(text.replace(old, new, 1))
