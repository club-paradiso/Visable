"""Reverse of important_pass.py (ADR-014 addendum 2): given visual states that FAIL after the pass,
find the minimal set of lines whose removed `!important` must be restored for them to match the
pristine baselines. Delta-debugging over the lines the pass changed (BEFORE vs AFTER commits).

Run it against an isolated worktree checked out at AFTER (so the main tree keeps serving its own
tests), with the current spec/config and the `local` baselines copied in:
  BISECT_WT=<worktree> BISECT_BEFORE=f3f82e1 BISECT_AFTER=ad3eefd \
  python3 scripts/rebuild/restore_bisect.py "<-g pattern>" assets/css/a.css assets/css/b.css ...
Prints the needed lines and writes <BISECT_OUT>/needed.json; the worktree is left with them restored."""
import subprocess, sys, os, re, json, time
WT = os.environ['BISECT_WT']
OUT = os.environ.get('BISECT_OUT', os.path.join(WT, 'test-results', 'restore-bisect'))
BEFORE = os.environ.get('BISECT_BEFORE', 'f3f82e1'); AFTER = os.environ.get('BISECT_AFTER', 'ad3eefd')
GREP = sys.argv[1]; FILES = sys.argv[2:]
PORT = os.environ.get('BISECT_PORT', '4335')
os.makedirs(OUT, exist_ok=True)
def git_show(rev, f): return subprocess.run(['git','-C',WT,'show',f'{rev}:{f}'],capture_output=True,text=True,check=True).stdout.split('\n')
cands = []  # (file, lineno)
old = {}; new = {}
for f in FILES:
    o = git_show(BEFORE, f); n = git_show(AFTER, f)
    assert len(o) == len(n), (f, len(o), len(n))
    old[f] = o; new[f] = n
    for i,(a,b) in enumerate(zip(o,n)):
        if a != b:
            assert a.count('!important') > b.count('!important'), (f,i)
            cands.append((f,i))
print(f'candidates: {len(cands)} lines in {len(FILES)} files', flush=True)
runs = 0
def write(subset):
    s = set(subset)
    for f in FILES:
        lines = [old[f][i] if (f,i) in s else new[f][i] for i in range(len(new[f]))]
        open(os.path.join(WT,f),'w',encoding='utf-8').write('\n'.join(lines))
def test(subset, label):
    global runs; runs += 1
    write(subset)
    for attempt in (1,2):
        r = subprocess.run(['npx','playwright','test','-c','playwright.golden.config.mjs','--project=visual-mobile','--project=visual-desktop','-g',GREP,'--output',f'{OUT}/{runs}','--retries','0'],
            cwd=WT, capture_output=True, text=True, env={**os.environ,'GOLDEN_PORT':PORT,'PARADISO_PW_EXECUTABLE':'/opt/pw-browsers/chromium'})
        out = r.stdout + r.stderr
        m = re.search(r'^\s+(\d+) passed', out, re.M); fm = re.search(r'^\s+(\d+) failed', out, re.M)
        passed = r.returncode == 0 and m and not fm
        if passed or 'pixels' in out or 'Expected an image' in out: break
        print(f'    run {runs} attempt {attempt}: non-pixel failure, retrying', flush=True)
    print(f'  run {runs} [{label}] restore {len(subset)} -> {"PASS" if passed else "fail"}', flush=True)
    return passed
def reduce(S, fixed):
    """minimal subset M of S such that test(fixed ∪ M) passes, given test(fixed ∪ S) passes."""
    if len(S) <= 1: return list(S)
    h = len(S)//2; A, B = S[:h], S[h:]
    if test(fixed + A, f'A of {len(S)}'): return reduce(A, fixed)
    if test(fixed + B, f'B of {len(S)}'): return reduce(B, fixed)
    mA = reduce(A, fixed + B)
    mB = reduce(B, fixed + mA)
    return mA + mB
t0 = time.time()
if not test(cands, 'all candidates'):
    print('restoring every candidate does NOT make the states pass: cause is outside these files'); write([]); sys.exit(2)
if test([], 'none'):
    print('already passes with nothing restored'); sys.exit(0)
need = reduce(cands, [])
write(need)
print(f'NEEDED ({len(need)} lines, {runs} runs, {int(time.time()-t0)}s):')
for f,i in need: print(f'  {f}:{i+1}: {old[f][i].strip()[:160]}')
json.dump(need, open(f'{OUT}/needed.json','w'))
