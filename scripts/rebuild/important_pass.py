#!/usr/bin/env python3
"""Design-led `!important` pass (owner decision 6), empirical and per file. Applied 2026-11-09 to the
index.html stylesheets (results in docs/rebuild/STATUS.md); kept as the record of the method.

For one stylesheet: strip every ` !important` from a candidate set of declarations, run the visual
golden suite (all states, both viewports) against the local baselines, and keep the removal only when
every shot is pixel-stable; otherwise bisect the candidate set (by rule order) until the failing
declarations are isolated. Nothing is kept on a failed comparison. The file is restored from git
between attempts, and the final accepted version is written once.

usage (repo root): python3 scripts/rebuild/important_pass.py <css-file> [--max-rounds N]
Needs the local baselines (tests/golden/__screenshots__/local) to be green on the untouched tree first;
logs go to test-results/important-pass/ (IMPORTANT_PASS_LOGS overrides). Each round runs the visual suite once.
"""
import re, subprocess, sys, pathlib, shutil, json, time, os
ROOT = pathlib.Path(__file__).resolve().parents[2]; S = pathlib.Path(os.environ.get('IMPORTANT_PASS_LOGS', ROOT / 'test-results' / 'important-pass'))
PORT = '4328'
IMPORTANT_RE = re.compile(r'\s*!\s*important')

def run_visual(tag):
    S.mkdir(parents=True, exist_ok=True); log = S / f'ipass-{tag}.log'
    import os
    env = {**os.environ, 'PARADISO_PW_EXECUTABLE': '/opt/pw-browsers/chromium', 'GOLDEN_PORT': PORT}
    r = subprocess.run(['npx', 'playwright', 'test', '-c', 'playwright.golden.config.mjs', '--project=visual-desktop', '--project=visual-mobile', '--output', str(S / f'tr-ipass-{tag}')], cwd=ROOT, env=env, capture_output=True, text=True)
    log.write_text(r.stdout + r.stderr)
    m = re.search(r'(\d+) passed', r.stdout); f = re.search(r'(\d+) failed', r.stdout)
    return (int(m.group(1)) if m else 0, int(f.group(1)) if f else 0)

def occurrences(text):
    return [m.span() for m in IMPORTANT_RE.finditer(text)]

def strip(text, spans):
    out = text
    for a, b in sorted(spans, reverse=True): out = out[:a] + out[b:]
    return out

def main():
    path = ROOT / sys.argv[1]; original = path.read_text(encoding='utf-8')
    spans = occurrences(original)
    print(f'{sys.argv[1]}: {len(spans)} !important')
    if not spans: return
    accepted = []  # spans that can go
    queue = [spans]; rounds = 0; max_rounds = int(sys.argv[sys.argv.index('--max-rounds') + 1]) if '--max-rounds' in sys.argv else 12
    try:
        while queue and rounds < max_rounds:
            cand = queue.pop(0); rounds += 1
            path.write_text(strip(original, accepted + cand), encoding='utf-8')
            passed, failed = run_visual(f'{path.stem}-r{rounds}')
            print(f'  round {rounds}: try {len(cand)} (accepted so far {len(accepted)}) -> {passed} passed, {failed} failed', flush=True)
            if failed == 0 and passed > 0:
                accepted += cand
            elif len(cand) > 1:
                mid = len(cand) // 2; queue += [cand[:mid], cand[mid:]]
            # a single failing span is dropped (it is needed)
        path.write_text(strip(original, accepted), encoding='utf-8')
        print(f'  kept removals: {len(accepted)} of {len(spans)}; rounds {rounds}; left in queue {sum(len(q) for q in queue)} untested (restored)')
        (S / f'ipass-{path.stem}.json').write_text(json.dumps({'file': sys.argv[1], 'total': len(spans), 'removed': len(accepted), 'rounds': rounds, 'untested': sum(len(q) for q in queue)}))
    except BaseException:
        path.write_text(original, encoding='utf-8'); raise

if __name__ == '__main__': main()
