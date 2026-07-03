from __future__ import annotations
import os, sys, unittest
from pathlib import Path
from unittest.mock import patch
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from services.providers.nvidia_nim import *  # noqa: E402,F403

class NvidiaNimProviderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls=[]
        async def transport(url, headers, payload, timeout):
            self.calls.append((url,headers,payload,timeout)); return 200,{"choices":[{"message":{"content":"mock answer"}}]}
        self.transport=transport
    async def invoke(self, config, mode="research", classification=PUBLIC_NON_PERSONAL):
        return await NvidiaNimProvider(config,transport=self.transport).chat_completion([{"role":"user","content":"synthetic"}],request_mode=mode,data_classification=classification)
    async def test_disabled_no_call(self):
        with self.assertRaises(NvidiaNimBlocked): await self.invoke(NvidiaNimConfig(api_key="x",enabled=False))
        self.assertFalse(self.calls)
    async def test_mode_gate_no_call(self):
        with self.assertRaises(NvidiaNimBlocked) as e: await self.invoke(NvidiaNimConfig(api_key="x",enabled=True),"production")
        self.assertEqual(e.exception.code,"nvidia_nim_mode_not_allowed"); self.assertFalse(self.calls)
    async def test_unknown_fails_closed(self):
        with self.assertRaises(NvidiaNimBlocked) as e: await self.invoke(NvidiaNimConfig(api_key="x",enabled=True),classification=UNKNOWN)
        self.assertEqual(e.exception.code,"nvidia_nim_data_classification_required")
    async def test_sensitive_blocked(self):
        with self.assertRaises(NvidiaNimBlocked) as e: await self.invoke(NvidiaNimConfig(api_key="x",enabled=True),classification=PERSONAL_OR_SENSITIVE)
        self.assertEqual(e.exception.code,"nvidia_nim_personal_data_not_allowed"); self.assertFalse(self.calls)
    async def test_mock_openai_shape(self):
        self.assertEqual(await self.invoke(NvidiaNimConfig(api_key="x",enabled=True)),"mock answer")
        self.assertEqual(self.calls[0][0],DEFAULT_BASE_URL+"/chat/completions"); self.assertFalse(self.calls[0][2]["stream"])
    def test_metadata_and_redaction(self):
        p=NvidiaNimProvider(NvidiaNimConfig(api_key="secret",enabled=False)); blob=repr(p.health_check())
        self.assertNotIn("secret",blob); self.assertFalse(p.metadata()["production_ready"]); self.assertFalse(p.metadata()["wired_to_api_ask"])
        self.assertNotIn("secret",p.sanitize_error("Bearer secret"))

class HealthTests(unittest.TestCase):
    def test_structured_health_is_secret_free(self):
        import paradiso_backend as pb
        from fastapi.testclient import TestClient
        env={"NVIDIA_API_KEY":"nv-secret","ENABLE_NVIDIA_NIM_EXPERIMENTAL":"false","NVIDIA_NIM_ALLOW_PERSONAL_DATA":"false","LAW_GROUNDING_MODE":"audit"}
        with patch.dict(os.environ,env),patch.object(pb,"OPENROUTER_API_KEY","or-secret"),patch.object(pb,"GROQ_API_KEY","g-secret"),patch.object(pb,"ALLOW_GROQ_FALLBACK",False):
            r=TestClient(pb.app).get("/health")
        s=r.json()["provider_status"]; self.assertTrue(s["openrouter"]["enabled"]); self.assertFalse(s["groq"]["fallback_allowed"])
        self.assertTrue(s["nvidia_nim"]["configured"]); self.assertFalse(s["nvidia_nim"]["enabled"]); self.assertFalse(s["nvidia_nim"]["production_ready"])
        self.assertNotIn("secret",r.text)
