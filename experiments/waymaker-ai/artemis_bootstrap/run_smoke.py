"""Artemis bootstrap: load a Gemma 4 MLX conversion and run the fictional smoke cases.

What this proves and what it does not: a run shows that this machine can load
the named conversion, that the chat template works, and how the model behaves
on five made-up questions (grounded answer, abstention, conflict, planted
instruction, partial answer). It says nothing about Korean immigration law and
is not a benchmark. Benchmark v0 is never read here, so its adversarial_holdout
is not looked at.

Why the size class is recorded from the weights and not from a flag: an E2B
pipeline check must never be reported as an E4B result. The record carries the
repository id, its pinned revision, and the text model's layer count read from
the downloaded config (E4B has 42 layers, E2B 35).

The run is offline: HF_HUB_OFFLINE is set before huggingface_hub is imported,
so the weights must already be in the cache (see README). There is no server
and no port; generation happens in this process. MLX is imported only inside
``run``, so ``--help`` and the tests work without it.

Usage, from experiments/waymaker-ai/artemis_bootstrap::

    HF_HOME=~/.cache/waymaker-artemis/hf .venv/bin/python run_smoke.py \\
        --model mlx-community/gemma-4-e4b-it-4bit \\
        --revision 475b9088d29754a3379866cf5aeb6b41acd313c2 \\
        --out runs/2026-10-26-e4b-4bit
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smoke_grader  # noqa: E402  (also puts experiments/waymaker-ai on sys.path for waymaker_ai)
import trust_gate  # noqa: E402
import manual_ledger  # noqa: E402
import procedure_route  # noqa: E402

LAYERS_TO_SIZE_CLASS = {42: "E4B", 35: "E2B"}
PACKAGES = ("mlx", "mlx-metal", "mlx-lm", "transformers", "huggingface-hub", "tokenizers")


def size_class(config: Dict[str, Any]) -> str:
    layers = (config.get("text_config") or config).get("num_hidden_layers")
    return LAYERS_TO_SIZE_CLASS.get(layers, f"UNKNOWN(num_hidden_layers={layers})")


def prepare_out_dir(out: Path) -> None:
    """Refuse to reuse a run directory: earlier records are never overwritten."""
    if out.exists():
        raise SystemExit(f"refusing to overwrite existing run directory: {out}")
    out.mkdir(parents=True)


def _sh(*cmd: str) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def machine() -> Dict[str, Any]:
    return {
        "model": _sh("sysctl", "-n", "hw.model"),
        "chip": _sh("sysctl", "-n", "machdep.cpu.brand_string"),
        "memory_bytes": int(_sh("sysctl", "-n", "hw.memsize") or 0),
        "macos": _sh("sw_vers", "-productVersion"),
        "python": platform.python_version(),
    }


def swap_usage() -> str:
    return _sh("sysctl", "-n", "vm.swapusage")


def free_disk_gb() -> float:
    """Free space where swap and the model cache live. On an 8 GB Mac a 4 GB
    model pushes other apps into swap, and swap files grow on this disk."""
    return round(shutil.disk_usage(Path.home()).free / 1e9, 2)


def start_disk_guard(
    record: Dict[str, Any],
    save: Callable[[], None],
    floor_gb: float,
    interval: float = 2.0,
    free_fn: Callable[[], float] = free_disk_gb,
    exit_fn: Callable[[int], None] = os._exit,
) -> threading.Event:
    """Abort the run, with a saved record, before swap fills the disk.

    Why a thread: the first attempt on the owner's Mac (2026-10-26) grew swap by
    about 3 GB while ``load`` was still running, and an outside watchdog had to
    kill the process before any record existed. Loading is one blocking call, so
    the check has to run beside it. Returns an event that stops the guard."""
    stop = threading.Event()

    def watch() -> None:
        while not stop.wait(interval):
            free = free_fn()
            if free < floor_gb:
                record["status"] = "aborted_low_disk"
                record["error"] = f"free disk {free} GB fell below {floor_gb} GB during stage {record.get('stage')}"
                record["free_disk_gb_at_abort"] = free
                record["swap_at_abort"] = swap_usage()
                record["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                save()
                exit_fn(3)
                return

    threading.Thread(target=watch, daemon=True).start()
    return stop


def versions() -> Dict[str, Optional[str]]:
    out: Dict[str, Optional[str]] = {}
    for name in PACKAGES:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = None
    return out


def base_model_of(snapshot: Path) -> Dict[str, Optional[str]]:
    """base_model and source revision as the conversion's model card states them."""
    card = snapshot / "README.md"
    text = card.read_text(encoding="utf-8") if card.exists() else ""
    info: Dict[str, Optional[str]] = {"base_model": None, "source_revision": None, "license_in_card": None}
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("base_model:"):
            info["base_model"] = s.split(":", 1)[1].strip()
        elif s.startswith("license:"):
            info["license_in_card"] = s.split(":", 1)[1].strip()
        elif "Source revision:" in s:
            info["source_revision"] = s.split("Source revision:", 1)[1].strip(" `")
    return info


def run(args: argparse.Namespace) -> int:
    out = Path(args.out)
    if free_disk_gb() < args.min_free_disk_gb:
        raise SystemExit(f"refusing to start: {free_disk_gb()} GB free, need {args.min_free_disk_gb} GB for swap headroom")
    cases_path = Path(args.cases).resolve()
    cases = manual_ledger.resolve_cases(smoke_grader.load_cases(cases_path))
    if args.source_gate and not all(trust_gate.has_source_labels(c) for c in cases):
        raise SystemExit(f"--source-gate needs source labels on every evidence item; {cases_path.name} has none")
    if (args.cross_check or args.label_switch) and not args.always_ask:
        raise SystemExit("--cross-check and --label-switch need --always-ask")
    if args.always_ask and (args.route or args.clarify):
        raise SystemExit("--always-ask replaces --route/--clarify; use it alone")
    if args.clarify and not args.route:
        raise SystemExit("--clarify needs --route")
    if args.integrity and not any("approved_sha256" in (e.get("source") or {}) for c in cases for e in c["evidence"]):
        raise SystemExit(f"--integrity needs approval hashes (source.approved_sha256); {cases_path.name} has none")
    prepare_out_dir(out)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

    from huggingface_hub import snapshot_download
    import mlx.core as mx
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler

    record: Dict[str, Any] = {
        "kind": "artemis_bootstrap_smoke",
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "machine": machine(),
        "versions": versions(),
        "device": {k: v for k, v in mx.device_info().items() if isinstance(v, (int, float, str))},
        "swap_before": swap_usage(),
        "free_disk_gb_before": free_disk_gb(),
        "cases_file": cases_path.name,
        "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
        "detector_on_labelled_evidence": smoke_grader.detector_confusion(cases),
        "decoding": {"temperature": 0.0, "max_tokens": args.max_tokens, "enable_thinking": False},
        "evidence_guard": args.evidence_guard,
        "source_gate": args.source_gate,
        "integrity": args.integrity,
        "route": args.route,
        "clarify": args.clarify,
        "always_ask": args.always_ask,
        "cross_check": args.cross_check,
        "label_switch": args.label_switch,
        "post_check": "applied offline to every output when the cases carry source labels",
        "prompts_persisted": False,
        "status": "started",
        "stage": "resolve",
    }
    record_path = out / "run_record.json"
    save_lock = threading.Lock()

    def save() -> None:
        with save_lock:
            record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def on_sigterm(signum, frame):  # an outside kill still leaves a record (finally below)
        raise SystemExit(f"terminated by signal {signum}")

    signal.signal(signal.SIGTERM, on_sigterm)
    save()
    guard = start_disk_guard(record, save, args.abort_below_free_disk_gb)

    try:
        snapshot = Path(snapshot_download(args.model, revision=args.revision))
        config = json.loads((snapshot / "config.json").read_text(encoding="utf-8"))
        record["model"] = {
            "repo": args.model,
            "revision": args.revision,
            "size_class_from_weights": size_class(config),
            "quantization": config.get("quantization"),
            "loader": "mlx_lm.load (text tower only; vision/audio weights dropped by mlx_lm sanitize)",
            **base_model_of(snapshot),
        }
        record["stage"] = "load"
        save()
        t0 = time.perf_counter()
        model, tokenizer = load(str(snapshot))
        mx.eval(model.parameters())
        record["load_seconds"] = round(time.perf_counter() - t0, 2)
        record["memory_after_load_gb"] = round(mx.get_active_memory() / 1e9, 3)
        save()

        sampler = make_sampler(temp=0.0)
        results: List[Dict[str, Any]] = []
        for case in cases:
            record["stage"] = f"case:{case['id']}"
            prompt_case, gate_withheld = trust_gate.gate(case, args.integrity) if args.source_gate else (case, [])
            route_withheld, scopes, turns, clarified = [], [], 1, False
            gated_case = prompt_case
            events: List[str] = []
            choice: Optional[str] = None
            pending_confirm = False

            def select(chosen: Optional[str]):
                """The gated case restricted to the chosen button's manual."""
                sc = procedure_route.route_choice(chosen) if chosen else []
                if not sc:
                    return procedure_route.gate_to(gated_case, [])[0], [e["id"] for e in gated_case["evidence"]], sc
                label = procedure_route.CLARIFY_CHOICES[chosen][1]
                asked = {**gated_case, "question": procedure_route.with_reply(case["question"], label)}
                pc, wh = procedure_route.gate_to(asked, sc)
                return pc, wh, sc

            if args.always_ask:  # every question gets the two buttons; the pressed one is the route
                gated_case = prompt_case
                choice = case.get("user_choice") or case.get("clarification_choice")
                if choice and args.cross_check:
                    cc = procedure_route.cross_check(case["question"], choice)
                    if cc["disagrees"]:  # ask once; the user's answer stands, whatever it is
                        events.append(f"confirm_asked:{','.join(cc['detected'])}")
                        turns += 1
                        if case.get("confirm_choice"):
                            if case["confirm_choice"] != choice:
                                events.append("confirm_switched")
                            choice = case["confirm_choice"]
                        else:
                            pending_confirm = True
                prompt_case, route_withheld, scopes = select(choice)
                if choice:
                    turns += 1
                clarified = not scopes or pending_confirm
            elif args.route:
                prompt_case, route_withheld, scopes = procedure_route.route_gate(gated_case)
                if args.clarify and not scopes:
                    reply = case.get("clarification_reply")
                    choice = case.get("clarification_choice") or case.get("user_choice")
                    if choice:  # the user pressed one of the two buttons: the route is the button
                        turns = 2
                        label = dict(procedure_route.CLARIFY_CHOICES).get(choice, ("", choice))[1]
                        asked = {**gated_case, "question": procedure_route.with_reply(case["question"], label)}
                        scopes = procedure_route.route_choice(choice)
                        prompt_case, route_withheld = procedure_route.gate_to(asked, scopes)
                    elif reply:  # free-text answer to the clarifying question; route again
                        turns = 2
                        asked = {**gated_case, "question": procedure_route.with_reply(case["question"], reply)}
                        prompt_case, route_withheld, scopes = procedure_route.route_gate(asked)
                    clarified = not scopes
            flagged = smoke_grader.screen_evidence(prompt_case) if args.evidence_guard != "off" else {}
            text, last, prompt = "", None, ""
            t0 = time.perf_counter()
            def generate(pc):
                msgs = smoke_grader.build_messages(pc, guard=args.evidence_guard)
                pr_ = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False, enable_thinking=False)
                out, lst = "", None
                for resp in stream_generate(model, tokenizer, pr_, max_tokens=args.max_tokens, sampler=sampler):
                    out += resp.text
                    lst = resp
                return out, lst, pr_

            first_output = None
            if clarified:  # no route (or a confirmation still open): a fixed question goes back, no model call
                out = procedure_route.confirm_output(choice) if pending_confirm else procedure_route.clarify_output()
                text = json.dumps(out, ensure_ascii=False)
            else:
                text, last, prompt = generate(prompt_case)
                if args.label_switch and choice and case.get("on_label") == "switch":
                    # The answer was labelled with its manual; the user tapped the switch.
                    events.append("label_switched")
                    first_output = text
                    choice = procedure_route.other_choice(choice)
                    prompt_case, route_withheld, scopes = select(choice)
                    turns += 1
                    text, last, prompt = generate(prompt_case)
            wall = time.perf_counter() - t0
            graded = smoke_grader.grade(case, text)
            checked: Dict[str, Any] = {}
            if trust_gate.has_source_labels(case):
                trusted = [e for e in case["evidence"] if trust_gate.is_trusted(e, args.integrity)]
                if args.route or args.always_ask:  # the post-check trusts only what the route allowed
                    trusted = [e for e in trusted if e["id"] not in route_withheld]
                verdict = (
                    {"verdict": "clarify", "claims": [], "unsupported": [], "final": json.loads(text)}
                    if clarified else trust_gate.post_check(graded["parsed"], trusted)
                )
                if args.label_switch and choice and not clarified:
                    verdict["final"] = procedure_route.label_answer(verdict["final"], choice)
                final_grade = smoke_grader.grade(case, json.dumps(verdict["final"], ensure_ascii=False))
                checked = {
                    "final_output": verdict["final"],
                    "post_check": {k: v for k, v in verdict.items() if k != "final"},
                    "checked": final_grade,
                    "outcome_raw": smoke_grader.classify(graded),
                    "outcome_checked": smoke_grader.classify(final_grade),
                }
            results.append({
                "case": case["id"],
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "evidence_flags": {k: list(v) for k, v in flagged.items()},
                "evidence_withheld": sorted(flagged) if args.evidence_guard == "drop" else [],
                "source_gate_withheld": gate_withheld,
                "route_scopes": [list(s) for s in scopes],
                "route_withheld": route_withheld,
                "turns": turns,
                "clarified": clarified,
                "final_choice": choice,
                "events": events,
                "first_output": first_output,
                "final_output": checked.get("final_output"),
                "integrity_failed": [e["id"] for e in case["evidence"]
                                     if trust_gate.is_trusted(e) and not trust_gate.integrity_ok(e)]
                if args.integrity else [],
                "prompt_tokens": last.prompt_tokens if last else None,
                "prompt_tps": round(last.prompt_tps, 2) if last else None,
                "generation_tokens": last.generation_tokens if last else None,
                "generation_tps": round(last.generation_tps, 2) if last else None,
                "finish_reason": last.finish_reason if last else None,
                "wall_seconds": round(wall, 2),
                "output": text,
                **graded,
                **checked,
            })
            record["results"] = results
            save()
            mark = "PASS" if graded["passed"] else "FAIL " + ";".join(graded["failures"])
            if checked:
                mark += f"  | checked: {checked['outcome_checked']} ({checked['post_check']['verdict']})"
            print(f"[{case['id']}] {mark}  ({last.generation_tps if last else 0:.1f} tok/s)", flush=True)

        record["summary"] = smoke_grader.summarize(results)
        if any("checked" in r for r in results):
            record["summary"]["outcomes_raw"] = smoke_grader.count_outcomes(r["outcome_raw"] for r in results)
            record["summary"]["outcomes_checked"] = smoke_grader.count_outcomes(r["outcome_checked"] for r in results)
        record["status"] = "completed"
        record["stage"] = "done"
    except BaseException as exc:  # recorded, then re-raised: a failed load is a result too
        record["status"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        guard.set()
        record["peak_memory_gb"] = round(mx.get_peak_memory() / 1e9, 3)
        record["max_rss_gb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 3)
        record["swap_after"] = swap_usage()
        record["free_disk_gb_after"] = free_disk_gb()
        record["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        save()
    print(json.dumps(record["summary"], ensure_ascii=False))
    return 0 if record["summary"]["failed"] == 0 else 1


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--model", required=True, help="MLX conversion repo id, e.g. mlx-community/gemma-4-e4b-it-4bit")
    p.add_argument("--revision", required=True, help="40-character commit of that repo")
    p.add_argument("--out", required=True, help="new run directory; an existing one is refused")
    p.add_argument("--cases", default=str(smoke_grader.CASES_PATH),
                   help="case file (default smoke_cases.json); see heldout_injection_cases.json, expansion_cases.json")
    p.add_argument("--source-gate", action="store_true",
                   help="(가) show the model only evidence whose source.approval_state is approved")
    p.add_argument("--integrity", action="store_true",
                   help="(라) an approved item counts only if source.approved_sha256 matches its text (gate and post-check)")
    p.add_argument("--route", action="store_true",
                   help="show the model only pages from the manual the question's procedure belongs to")
    p.add_argument("--clarify", action="store_true",
                   help="with --route: when no manual can be chosen, ask which procedure; use the case's clarification_reply as turn 2")
    p.add_argument("--always-ask", action="store_true",
                   help="show the two buttons for every question; the pressed button (user_choice) is the only route")
    p.add_argument("--cross-check", action="store_true",
                   help="with --always-ask: ask once when the detector confidently disagrees with the pressed button")
    p.add_argument("--label-switch", action="store_true",
                   help="with --always-ask: label each answer with its manual; a case's on_label=switch taps the switch")
    p.add_argument("--max-tokens", type=int, default=400)
    p.add_argument("--evidence-guard", choices=smoke_grader.GUARD_MODES, default="off",
                   help="screen evidence with WLIE's injection detector: off, mark it untrusted, or drop it")
    p.add_argument("--min-free-disk-gb", type=float, default=2.0, help="refuse to start below this much free disk")
    p.add_argument("--abort-below-free-disk-gb", type=float, default=1.5,
                   help="stop the run, with a saved record, if free disk falls below this while it runs")
    args = p.parse_args(argv)
    if len(args.revision) != 40:
        p.error("--revision must be a pinned 40-character commit")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
