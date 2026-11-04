#!/usr/bin/env python3
"""Phase 6 tool (already applied; kept as the record of the method): move FastAPI route handlers out of
backend/paradiso_backend.py into router modules. Re-running --apply on the split module finds no
`@app` handlers and writes nothing. Run from the repo root with backend/ on sys.path (it imports
paradiso_backend to learn the module globals): cd backend && python3 ../scripts/rebuild/extract_routers.py --dry-run

Each handler keeps its source text; every identifier that resolves to a module global of
paradiso_backend is qualified as `pb.<name>` (pb = the facade module, passed into the router
factory), so tests that monkeypatch `paradiso_backend.<name>` keep working. Names from a small
import whitelist (typing / fastapi symbols used in signatures and decorators) are imported by
the router module instead. Usage:
  extract_routers.py --dry-run            report handlers, globals, blockers
  extract_routers.py --apply GROUPS.json  write backend/routers/*.py and rewrite paradiso_backend.py (groups: scripts/rebuild/router_groups.json)
"""
import ast, builtins, json, sys, symtable, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[2]; SRC = ROOT / 'backend' / 'paradiso_backend.py'
WHITELIST = {  # imported directly by the router modules (never monkeypatched by tests)
    'Any', 'Dict', 'List', 'Optional', 'Sequence', 'Tuple', 'Union', 'Iterable', 'Callable', 'Set',
    'Depends', 'Request', 'HTTPException', 'Response', 'StreamingResponse', 'JSONResponse',
}
TYPING = {'Any', 'Dict', 'List', 'Optional', 'Sequence', 'Tuple', 'Union', 'Iterable', 'Callable', 'Set'}
FASTAPI = {'Depends', 'Request', 'HTTPException'}
RESPONSES = {'Response', 'StreamingResponse', 'JSONResponse'}

def module_globals(src: str):
    sys.path.insert(0, str(ROOT / 'backend'))
    import paradiso_backend as pb  # noqa
    names = set(vars(pb).keys())
    tree = ast.parse(src)
    for node in tree.body:
        for n in ast.walk(node) if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)) else []:
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store): names.add(n.id)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): names.add(node.name)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names: names.add((a.asname or a.name).split('.')[0])
    return names - set(dir(builtins))

def handlers(tree):
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in node.decorator_list:
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and isinstance(d.func.value, ast.Name) and d.func.value.id == 'app':
                    path = d.args[0].value if d.args and isinstance(d.args[0], ast.Constant) else None
                    out.append({'node': node, 'name': node.name, 'method': d.func.attr, 'path': path,
                                'start': min(x.lineno for x in node.decorator_list), 'end': node.end_lineno})
    return out

def scope_tables(src):
    top = symtable.symtable(src, str(SRC), 'exec')
    index = {}
    def walk(t):
        for c in t.get_children():
            index[(c.get_name(), c.get_lineno())] = c; walk(c)
    walk(top); return top, index

def qualify(src_lines, h, globs, tables_index):
    """Return the handler's text with globals qualified, plus the set of globals used and blockers."""
    node = h['node']; used = set(); blockers = []; edits = []  # (lineno, col, len, replacement)
    # map each Name to its innermost enclosing function scope
    scopes = []  # (node, table)
    def visit(fn, table):
        for child in ast.walk(fn):
            pass
    def resolve(name_node, enclosing):
        # enclosing: list of (function node, table) from outer to inner
        for fnode, table in reversed(enclosing):
            try: sym = table.lookup(name_node.id)
            except KeyError: continue
            if sym.is_declared_global(): return 'declared_global'
            if sym.is_global(): return 'global'
            if sym.is_local() or sym.is_parameter(): return 'local'
            if sym.is_free(): continue  # defined in an enclosing function scope → keep walking outward
        return 'global'
    def walk(n, enclosing):
        if isinstance(n, ast.Name):  # a bare-Name annotation / decorator argument / return annotation
            if n.id in globs and n.id not in WHITELIST and (resolve(n, enclosing) if enclosing else 'global') == 'global':
                used.add(n.id); edits.append((n.lineno, n.col_offset, len(n.id), 'pb.' + n.id))
            return
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            key_name = n.name if not isinstance(n, ast.Lambda) else 'lambda'
            table = tables_index.get((key_name, n.lineno))
            if table is None: blockers.append(f'no symtable for {key_name}@{n.lineno}'); return
            enclosing = enclosing + [(n, table)]
            if any(isinstance(s, ast.Global) for s in ast.walk(n)): blockers.append(f'global statement in {key_name}@{n.lineno}')
            # decorators and defaults/annotations of nested defs are evaluated in the outer scope; handled below for the handler itself
        for child in ast.iter_child_nodes(n):
            walk(child, enclosing)
    # the handler's own decorators/annotations/defaults belong to the module scope: evaluate with enclosing=[] 
    for d in node.decorator_list:
        # the decorator call target `app.<method>` is rewritten to `router.<method>` below; its other names are module-scope
        for arg in (d.args + [k.value for k in d.keywords]) if isinstance(d, ast.Call) else [d]: walk(arg, [])
    for a in node.args.args + node.args.kwonlyargs + node.args.posonlyargs + ([node.args.vararg] if node.args.vararg else []) + ([node.args.kwarg] if node.args.kwarg else []):
        if a.annotation: walk(a.annotation, [])
    for dflt in node.args.defaults + [x for x in node.args.kw_defaults if x]: walk(dflt, [])
    if node.returns: walk(node.returns, [])
    table = tables_index.get((node.name, node.lineno)); enclosing = [(node, table)]
    if any(isinstance(s, ast.Global) for s in ast.walk(node)): blockers.append(f'global statement in {node.name}')
    for stmt in node.body: walk(stmt, enclosing)
    lines = src_lines[h['start']-1:h['end']]
    # apply edits from the end
    for lineno, col, ln, rep in sorted(edits, key=lambda e: (-e[0], -e[1])):
        i = lineno - h['start']; line = lines[i]
        assert line[col:col+ln] == rep[3:], (lineno, col, line[col:col+ln], rep)
        lines[i] = line[:col] + rep + line[col+ln:]
    # decorator: app.X( -> router.X(
    first = lines[0]; assert first.startswith('@app.'), first
    lines[0] = '@router.' + first[len('@app.'):]
    return lines, used, blockers

def main():
    src = SRC.read_text(encoding='utf-8'); src_lines = src.split('\n')
    tree = ast.parse(src); globs = module_globals(src); top, index = scope_tables(src)
    hs = handlers(tree)
    if sys.argv[1] == '--dry-run':
        for h in hs:
            lines, used, blockers = qualify(src_lines, h, globs, index)
            print(f"{h['start']:5}-{h['end']:5} {h['method']:4} {h['path']:50} {h['name']:40} globals={len(used)} {'BLOCKERS: '+'; '.join(blockers) if blockers else ''}")
        return
    groups = json.loads(pathlib.Path(sys.argv[2]).read_text())  # [{"module": "health", "routes": ["root", "health", ...]}]
    by_name = {h['name']: h for h in hs}
    removed = []  # (start, end)
    for g in groups:
        body = []; needs = set()
        for name in g['routes']:
            h = by_name[name]; lines, used, blockers = qualify(src_lines, h, globs, index)
            assert not blockers, (name, blockers)
            body.extend(['    ' + l if l.strip() else '' for l in lines] + ['', ''])
            removed.append((h['start'], h['end']))
            for n in WHITELIST:
                pass
            text = '\n'.join(lines)
            needs |= {n for n in WHITELIST if re.search(r'\b' + n + r'\b', text)}
        typing_imports = sorted(needs & TYPING); fastapi_imports = sorted((needs & FASTAPI) | {'APIRouter'}); resp_imports = sorted(needs & RESPONSES)
        head = [f'"""{g["doc"]}', '', 'Moved from backend/paradiso_backend.py in Phase 6 of the rebuild (docs/rebuild/DECISIONS.md ADR-013).',
                'The handler bodies are the original text; identifiers that resolve to module globals of',
                'paradiso_backend are qualified as ``pb.<name>`` so the facade stays the single owner of state,',
                'configuration and helpers, and tests that monkeypatch ``paradiso_backend.<name>`` keep working.',
                'No ``from __future__ import annotations`` here on purpose: FastAPI must see the real annotation',
                'objects (``pb.X`` is a closure variable of the factory, not a module global).', '"""']
        imports = []
        if typing_imports: imports.append('from typing import ' + ', '.join(typing_imports))
        imports.append('from fastapi import ' + ', '.join(fastapi_imports))
        if resp_imports: imports.append('from fastapi.responses import ' + ', '.join(resp_imports))
        out = head + [''] + imports + ['', '', 'def build_router(pb) -> APIRouter:', '    """Routes of this group, registered in their original order. ``pb`` is the paradiso_backend module."""', '    router = APIRouter()', ''] + body
        while out and out[-1] == '': out.pop()
        out += ['    return router', '']
        (ROOT / 'backend' / 'routers' / (g['module'] + '.py')).write_text('\n'.join(out), encoding='utf-8')
        print('wrote', g['module'], len(g['routes']), 'routes')
    # rewrite paradiso_backend.py: remove handler spans (and one following blank line pair), add includes before the knowledge router include
    keep = [True] * len(src_lines)
    for s, e in removed:
        for i in range(s-1, e): keep[i] = False
        # swallow up to two trailing blank lines
        j = e
        while j < len(src_lines) and j < e + 2 and src_lines[j].strip() == '': keep[j] = False; j += 1
    new_lines = [l for l, k in zip(src_lines, keep) if k]
    text = '\n'.join(new_lines)
    anchor = 'app.include_router(build_knowledge_router('
    assert text.count(anchor) == 1
    include_block = ['# ---------------------------------------------------------------------------',
                     '# Route handlers live in backend/routers/ (Phase 6 of the rebuild, ADR-013). They are',
                     '# registered here, in the order their decorators used to appear in this file, so the',
                     '# route table is unchanged (backend/tests/test_api_contract_snapshot.py proves it).',
                     '# Each factory receives this module so handlers resolve state/config/helpers at call time.',
                     '# ---------------------------------------------------------------------------',
                     'import sys as _sys  # noqa: E402', '']
    for g in groups:
        include_block.append(f'from routers.{g["module"]} import build_router as _build_{g["module"]}_router  # noqa: E402')
    include_block.append('')
    for g in groups:
        include_block.append(f'app.include_router(_build_{g["module"]}_router(_sys.modules[__name__]))')
    include_block += ['', '']
    # place the include block right before the knowledge-router banner comment
    banner = '# ---------------------------------------------------------------------------\n# Waymaker Knowledge Platform HTTP surface'
    assert text.count(banner) == 1
    text = text.replace(banner, '\n'.join(include_block) + banner, 1)
    SRC.write_text(text, encoding='utf-8')
    print('rewrote', SRC, 'lines', len(text.split('\n')))

if __name__ == '__main__': main()
