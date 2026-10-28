"""A second look by the model at answers that state a permission or a limit.

Why: rules caught 9 of 60 flipped permissions on held-out v12 ("제한 없이 받을 수
있습니다" where the page says "할 수 없음"); most flips use words no rule anticipates.
The rules still pick the candidates (an answer sentence about allowing, forbidding or a
limit) and the page passages closest to it; the model only answers one narrow question
per pair: does the answer say the same as the passage, the opposite, or something the
passage does not cover. One "opposite" marks the answer for review. It never rewrites
or withholds an answer.

``judge(answer, trusted_text, generate)`` takes ``generate(prompt) -> str`` so the tests
can use a stub; ``measure`` loads E4B once (the same model and settings as run_smoke).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import trust_gate

HERE = Path(__file__).resolve().parent
CACHE = HERE / "ledgers" / "flip_judge_cache.jsonl"

#: Sentences worth a look: they allow, forbid or bound something.
_CLAIM_RE = re.compile(r"수\s*있|수\s*없|가능|불가|허용|불허|인정|제한|한도|이내|까지|범위|없이|관계없이|상관없이|안\s*됩|됩니다|못")
PROMPT = (
    "아래 [근거]는 출입국 매뉴얼 원문이고, [답]은 이용자에게 준 설명입니다.\n"
    "[답]이 허용·금지·한도에 관해 [근거]와 같은 말을 하는지, 반대로 말하는지 판정하세요.\n"
    "반대란 근거가 금지하거나 제한한 것을 답이 허용하거나 제한이 없다고 하는 것, 또는 그 거꾸로입니다.\n"
    "[근거]가 그 내용을 다루지 않으면 unrelated입니다.\n"
    "JSON 한 줄로만 답하세요: {{\"verdict\": \"same\"}} 또는 {{\"verdict\": \"opposite\"}} 또는 {{\"verdict\": \"unrelated\"}}\n\n"
    "[근거]\n{passage}\n\n[답]\n{sentence}"
)


def candidates(answer: str, trusted_text: str, per_sentence: int = 2) -> List[Dict[str, str]]:
    """(answer sentence, page passage) pairs the model should look at."""
    lines = [ln for ln in trusted_text.splitlines() if ln.strip()]
    segments = list(dict.fromkeys([" ".join(lines[i:i + 2]) for i in range(len(lines))] + trust_gate._sentences(trusted_text)))
    seg_stems = [(seg, trust_gate._stems(seg)) for seg in segments]
    pairs = []
    for s in trust_gate._sentences(answer):
        if not _CLAIM_RE.search(s):
            continue
        mine = trust_gate._stems(s)
        if len(mine) < 2:
            continue
        ranked = sorted(((len(mine & st), seg) for seg, st in seg_stems if len(mine & st) >= 2), key=lambda x: -x[0])
        for _, seg in ranked[:per_sentence]:
            if _CLAIM_RE.search(seg):
                pairs.append({"sentence": s.strip(), "passage": seg.strip()[:400]})
    return pairs


def _verdict(text: str) -> str:
    m = re.search(r'"verdict"\s*:\s*"(same|opposite|unrelated)"', text or "")
    return m.group(1) if m else "unparsed"


class Cache:
    def __init__(self, path: Path = CACHE):
        self.path = path
        self.rows: Dict[str, str] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                self.rows[r["key"]] = r["verdict"]

    def get(self, prompt: str, generate: Optional[Callable[[str], str]]) -> str:
        key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if key not in self.rows:
            if generate is None:
                raise KeyError("prompt not judged yet and no model given")
            self.rows[key] = _verdict(generate(prompt))
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"key": key, "verdict": self.rows[key]}) + "\n")
        return self.rows[key]


_PASSAGE_ALLOWS_RE = re.compile(r"가능|허용|할\s*수\s*있|인정(?!하지)")


def polarity_disagrees(sentence: str, passage: str) -> bool:
    """The rules' own reading: the answer allows or lifts what the passage restricts, or
    forbids what the passage allows. Without it, an "opposite" from the model marked 15
    of 324 right answers of recorded real-manual runs (passages about something else)."""
    lifts = bool(trust_gate._LIFT_RE.search(sentence))
    allows = (bool(trust_gate._ALLOW_RE.search(sentence)) or lifts) and not trust_gate._DENY_RE.search(sentence)
    denies = bool(trust_gate._DENY_RE.search(sentence))
    restricts = bool(trust_gate._LIMIT_RE.search(passage) or trust_gate._HARD_NO_RE.search(passage))
    grants = bool(_PASSAGE_ALLOWS_RE.search(passage)) and not trust_gate._HARD_NO_RE.search(passage)
    return (allows and restricts) or (denies and grants and not restricts)


def judge(answer: str, trusted_text: str, generate: Optional[Callable[[str], str]] = None,
          cache: Optional[Cache] = None) -> List[Dict[str, str]]:
    """The pairs the model called "opposite" whose polarity the rules also see differ."""
    cache = cache or Cache()
    out = []
    for pair in candidates(answer, trusted_text):
        prompt = PROMPT.format(**pair)
        if cache.get(prompt, generate) == "opposite" and polarity_disagrees(pair["sentence"], pair["passage"]):
            out.append(pair)
    return out


def load_e4b() -> Callable[[str], str]:
    """E4B as run_smoke loads it: greedy, thinking off, a short answer."""
    import os
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from huggingface_hub import snapshot_download
    from mlx_lm import load, generate as mlx_generate
    from mlx_lm.sample_utils import make_sampler
    snapshot = snapshot_download("mlx-community/gemma-4-e4b-it-4bit", revision="475b9088d29754a3379866cf5aeb6b41acd313c2")
    model, tokenizer = load(snapshot)
    sampler = make_sampler(temp=0.0)

    def generate(prompt: str) -> str:
        text = tokenizer.apply_chat_template([{"role": "user", "content": prompt}], add_generation_prompt=True,
                                             tokenize=False, enable_thinking=False)
        return mlx_generate(model, tokenizer, text, max_tokens=24, sampler=sampler)
    return generate
