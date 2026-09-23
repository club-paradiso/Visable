#!/usr/bin/env python3
"""Build the official immigration form inventory + Form Helper coverage report.

Sources (all local, offline):
  * 출입국관리법 시행규칙 (법무부령 제1106호, 2026-01-23) — every 별지 서식 marker in
    docs/source-manuals/law/rule_1106_full.txt (title + revision tag + page of the
    official PDF docs/source-manuals/law/immigration_control_act_enforcement_rule_moj_01106_2026_01_23.pdf);
  * 재외동포의 출입국과 법적 지위에 관한 법률 시행규칙 — the two annexes held in
    docs/forms_official/law (F04 별지 제1호, F05 별지 제1호의2); the rest of that
    annex list is not verifiable offline and is recorded as UNKNOWN;
  * HiKorea 민원서식 — 거주/숙소제공확인서 held locally; 421 download links were
    counted on 2026-06-12 (docs/forms_official/FORM_VERSION_AUDIT.md) and are
    recorded as UNKNOWN because hikorea.go.kr is unreachable from the build sandbox;
  * Visable support records — data/form_schemas.json (`forms.*.template` +
    `support`) and data/form_definitions.json.

Classification (per form):
  applicant_facing   a form an applicant / inviter / employer fills in (in scope)
  official_use       심사인·허가서·통지서·대장·명령서·결정서·보고서·통계 etc. (not fillable by the public)
  excluded_departure 출국기한유예 forms — explicitly excluded from auto-fill
  excluded_refugee   난민 forms — explicitly excluded from auto-fill
  enforcement        보호·강제퇴거·송환·과태료 proceedings — applicant may sign, but not a civil-petition form
  deleted            annex deleted by amendment

Status for applicant-facing forms: SUPPORTED / PARTIAL / BLOCKED / SUPERSEDED / EXCLUDED
(EXCLUDED only for the two excluded categories). Every in-scope form gets exactly one.

  python3 scripts/forms/build_forms_inventory.py            # write data/forms_inventory.json + coverage report
  python3 scripts/forms/build_forms_inventory.py --check    # fail if the committed files are stale
"""
import argparse, hashlib, json, os, re, sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RULE_TXT = os.path.join(ROOT, 'docs/source-manuals/law/rule_1106_full.txt')
RULE_PDF = 'docs/source-manuals/law/immigration_control_act_enforcement_rule_moj_01106_2026_01_23.pdf'
SCHEMAS = os.path.join(ROOT, 'data/form_schemas.json')
DEFS = os.path.join(ROOT, 'data/form_definitions.json')
OUT_JSON = os.path.join(ROOT, 'data/forms_inventory.json')
OUT_MD = os.path.join(ROOT, 'docs/forms_official/FORM_HELPER_COVERAGE_20260923.md')
REPORT_DATE = '2026-09-23'

MARK = re.compile(r'\[별지 제(\d+)호(?:의(\d+))?\s*서식\]\s*(?:<([^>]*)>)?')

# ---- printed titles where the text dump puts a number/label line first -------
TITLE_OVERRIDES = {
    '30의4': '난민임시상륙허가서', '126의12': '난민여행증명서 (앞표지)', '126의13': '난민여행증명서 (속지)', '126의15': '난민여행증명서 반납명령서',
}

# ---- explicit classification overrides (annex number → class, reason) -------
OVERRIDES = {
    '44': ('excluded_departure', '출국기한유예신청서 — auto-fill explicitly out of scope'),
    '44의2': ('excluded_departure', '출국기한유예 불허결정 통지서 — out of scope (official notice, departure-deadline family)'),
    '30의3': ('excluded_refugee', '난민임시상륙허가(기간연장) 신청서 — refugee family, out of scope'),
    '30의4': ('excluded_refugee', '난민임시상륙허가서 — refugee family, out of scope'),
    '30의5': ('excluded_refugee', '난민임시상륙허가서 발급대장 — refugee family, out of scope'),
    '126의10': ('excluded_refugee', '난민여행증명서 (재)발급신청서 (deleted number retained in index) — refugee family'),
    '126의11': ('excluded_refugee', '난민여행증명서 (재)발급신청서 — refugee family, out of scope'),
    '126의12': ('excluded_refugee', '난민여행증명서 (표지) — refugee family'),
    '126의13': ('excluded_refugee', '난민여행증명서 발급대장 — refugee family'),
    '126의14': ('excluded_refugee', '난민여행증명서 유효기간 연장허가 신청서 — refugee family, out of scope'),
    '126의15': ('excluded_refugee', '난민여행증명서 연장허가 (번호) — refugee family'),
    # enforcement / detention proceedings: signed by the person concerned but not a civil-petition form
    '105': ('enforcement', '보호명령에 대한 이의신청서 — detention proceedings'),
    '111': ('enforcement', '강제퇴거명령에 대한 이의신청서 — removal proceedings'),
    '118': ('enforcement', '보호 일시해제 신청서 — detention proceedings'),
    '120의6': ('enforcement', '구술심리 신청서 — detention review'),
    '116의2': ('enforcement', '보호기간 연장승인 신청서 — official request in detention proceedings'),
    '126의3': ('enforcement', '송환기한 연기 신청서 — removal proceedings'),
    '126의4': ('enforcement', '송환대기장소 변경 신청서 — removal proceedings'),
    '143': ('enforcement', '임시납부신청서 — penalty proceedings'),
    '169': ('enforcement', '과태료처분에 대한 이의제기서 (deleted number)'),
    '170': ('enforcement', '과태료처분에 대한 이의제기서 — penalty proceedings'),
    '11': ('enforcement', '출국금지결정 등 이의신청서 — 출국금지 proceedings'),
    '56의6': ('enforcement', '출국정지결정 등 이의신청서 — 출국정지 proceedings'),
    # applicant-facing forms that the keyword rules would otherwise miss or mis-file
    '19의2': ('applicant_facing', '외국인 배우자 초청장 — inviter-filled (F-6)'),
    '19의3': ('applicant_facing', '외국인 배우자의 결혼배경 진술서 — applicant-filled (F-6)'),
    '21의3': ('applicant_facing', '회화지도(E-2) 자격사증신청자 건강확인서 — applicant-filled'),
    '129': ('applicant_facing', '신원보증서 — guarantor-filled'),
    '34': ('applicant_facing', '통합신청서(신고서)'),
    '34의2': ('applicant_facing', '통합신청서(신고서) 한자 병기'),
    '34의3': ('applicant_facing', '통합신청서(신고서) 중문 병기'),
    '1의4': ('applicant_facing', '자동출입국심사 등록신청서'),
    '1의6': ('applicant_facing', '자동출입국심사 등록 해지신청서'),
    '1의7': ('applicant_facing', '자동출입국심사 등록정보 정정신청서'),
    '24의5': ('applicant_facing', '자동출입국심사 등록신청서 (외국인용, 한자)'),
    '24의6': ('applicant_facing', '자동출입국심사 등록해지 신청서 (외국인용, 한자)'),
    '24의2': ('applicant_facing', '입국허가 신청서 (at the port of entry)'),
    '17의2': ('applicant_facing', '단체사증발급신청서 (group visa, agency-filled)'),
    '21의2': ('applicant_facing', '사증발급인정서 발급대상자 명단 (inviter-filled list)'),
    '22': ('applicant_facing', '단체사증 발급대상자 명단 (agency-filled)'),
    '125': ('applicant_facing', '승선·출입국심사장 출입 허가신청서 (port access, business-filled)'),
    '126의16': ('applicant_facing', '대행기관 등록신청서 (agency-filled)'),
    '126의17': ('applicant_facing', '외국인 기본인적정보 제공 요청서 (third-party request)'),
    '138의2': ('applicant_facing', '사실증명 발급·열람 신청서'),
    '139의3': ('applicant_facing', '외국인체류확인서 열람 또는 교부 신청서'),
    '139의4': ('applicant_facing', '외국인체류확인서 열람 또는 교부 일괄 신청서 (institution-filled)'),
    '139의7': ('applicant_facing', '외국인등록증의 진위 확인 신청서 (institution-filled)'),
    '33의2': ('applicant_facing', '계절근로 전문기관 지정신청서 (institution-filled)'),
    '80': ('official_use', '사회통합 프로그램 운영기관 지정신청서 (deleted number retained)'),
    '81': ('applicant_facing', '사회통합 프로그램 운영기관 지정신청서 (institution-filled)'),
    '100의2': ('enforcement', '보호(일시보호)기간 연장허가서 발급신청서 — official request'),
    '61': ('applicant_facing', '재입국허가기간 연장허가 신청서'),
    '72': ('applicant_facing', '방문취업 동포 취업개시 등 신고서'),
    '32': ('applicant_facing', '고용·연수외국인 변동사유 발생 신고서 (employer-filled)'),
    '17': ('applicant_facing', '사증발급신청서'),
    '17의3': ('applicant_facing', '사증발급신청서 (variant)'),
    '21': ('applicant_facing', '사증발급인정신청서 (inviter-filled)'),
    '34의4': ('applicant_facing', '체류지 변경신고서 (시·군·구 제출용, 한·영)'),
    '34의5': ('applicant_facing', '체류지 변경신고서 (중문)'),
    '34의6': ('applicant_facing', '체류지 변경신고서 (베트남어)'),
    '34의7': ('applicant_facing', '체류지 변경신고서 (태국어)'),
    '34의8': ('applicant_facing', '체류지 변경신고서 (러시아어)'),
    '34의9': ('applicant_facing', '모바일외국인등록증 신규 발급 및 재발급 신청서'),
}
APPLICANT_WORDS = ('신청서', '신고서', '초청장', '진술서', '확인서', '보증서', '동의서', '명단', '요청서')
OFFICIAL_WORDS = ('심사인', '허가인', '확인인', '신고필인', '통지서', '명령서', '결정서', '보고서', '대장', '허가서', '통보서', '지시서', '인수증', '보관증', '고발서', '통고서', '고지서', '청구서', '기록표', '동향', '현황', '표시', '사증', '등록표', '등록증', '증명', '심사증', '의뢰서', '요청서', '취소서', '해제', '권고서', '검색', '사건부', '조서', '목록', '추천서', '이력서', '앞표지', '앞 쪽', '앞면', '삭제', 'NOTICE', 'DISAPPROVAL', 'REFUSAL', 'REVOCATION', 'DECISION', 'CONFIRMATION OF NOTICE', 'STATEMENT', 'LIST', '번호', 'No.', '문 서 번 호', '발급번호', '제       호', '제           호', '제         호', '법   무', '법     무', '법       무', '접수', '대상자', '한국인', '출입국관리사무소인', '주한미군', '조건부입국허가서')

VISA_ISSUANCE_NUMBERS = {'17', '17의2', '17의3', '19의2', '19의3', '21', '21의2', '21의3', '22'}


def load_rule_forms():
    lines = open(RULE_TXT, encoding='utf-8').read().split('\n')
    seen, out = set(), []
    for i, l in enumerate(lines):
        m = MARK.search(l)
        if not m:
            continue
        num = m.group(1) + ('의' + m.group(2) if m.group(2) else '')
        if num in seen:
            continue
        seen.add(num)
        rev = (m.group(3) or '').strip()
        title = ''
        for j in range(i + 1, min(i + 8, len(lines))):
            t = lines[j].strip()
            if not t or t.startswith('■') or t.startswith('≪') or re.match(r'^\(제\d+쪽', t) or ('mm' in t.lower() and '×' in t):
                continue
            title = t
            break
        title = TITLE_OVERRIDES.get(num, title)
        deleted = '삭제' in l or '삭제' in title
        out.append({'number': num, 'title': re.sub(r'\s+', ' ', title)[:80], 'revision': rev, 'line': i + 1, 'deleted': deleted})
    return out


def classify(entry):
    num, title = entry['number'], entry['title']
    if entry['deleted'] or title.startswith('[별지'):
        return 'deleted', 'annex deleted by amendment'
    if num in OVERRIDES:
        return OVERRIDES[num]
    if any(w in title for w in APPLICANT_WORDS) and not any(w in title for w in ('발급대장', '요청대장', '처리대장', '통지서', '결정서', '명령서', '허가서 발급', '요청서', '추천서', '이력서')):
        return 'applicant_facing', 'title is an application / report / statement form'
    return 'official_use', 'official-use document (stamp, permit, notice, register, order, report or statistics)'


def rule_pdf_pages():
    """Map annex number → first page in the rule PDF (from the PDF text itself)."""
    try:
        import warnings; warnings.filterwarnings('ignore')
        import pymupdf
    except Exception:
        return {}
    cache = os.path.join(ROOT, 'data', '.rule_1106_pages.json')
    if os.path.exists(cache):
        return json.load(open(cache))
    doc = pymupdf.open(os.path.join(ROOT, RULE_PDF))
    found = {}
    for i in range(len(doc)):
        for m in MARK.finditer(doc[i].get_text()):
            num = m.group(1) + ('의' + m.group(2) if m.group(2) else '')
            found.setdefault(num, i + 1)
    return found


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--check', action='store_true'); a = ap.parse_args()
    schemas = json.load(open(SCHEMAS, encoding='utf-8'))
    defs = json.load(open(DEFS, encoding='utf-8')) if os.path.exists(DEFS) else {'forms': {}}
    rule = load_rule_forms()
    pages = rule_pdf_pages()
    for e in rule:
        e['pdf_page'] = pages.get(e['number'])
        e['class'], e['reason'] = classify(e)
        e['domain'] = 'visa_issuance' if e['number'] in VISA_ISSUANCE_NUMBERS else 'stay'

    # Visable support records keyed by (law, annex number)
    support = {}
    for fid, spec in schemas['forms'].items():
        d = defs['forms'].get(fid, {})
        tpl = spec.get('template', {})
        rec = {
            'form_id': fid, 'name_ko': spec.get('nameKo'), 'name_en': spec.get('nameEn'), 'legal_basis': spec.get('legalBasis'),
            'revision_on_form': spec.get('revisionDate'), 'pdf': spec.get('pdf'), 'pages': spec.get('pages'),
            'field_count': len(spec.get('overlay', {})), 'field_map_version': tpl.get('fieldMapVersion'),
            'template_edition': tpl.get('edition'), 'template_sha256': tpl.get('sha256'), 'edition_verification': tpl.get('verification'),
            'status': (spec.get('support') or {}).get('status', 'UNKNOWN'), 'status_reason': (spec.get('support') or {}).get('reason', ''),
            'qa': (spec.get('support') or {}).get('qa', 'NOT_RUN'), 'is_variant': bool(spec.get('isVariant')), 'base_form': spec.get('baseForm'),
            'annex': (spec.get('support') or {}).get('annex'), 'law': (spec.get('support') or {}).get('law', 'immigration_rule'),
            'pdf_sha256_actual': sha256(os.path.join(ROOT, spec['pdf'])) if spec.get('pdf') and os.path.exists(os.path.join(ROOT, spec['pdf'])) else None,
        }
        support[fid] = rec
    by_annex = {}
    for rec in support.values():
        if rec['annex'] and rec['law'] == 'immigration_rule':
            by_annex.setdefault(rec['annex'], []).append(rec['form_id'])

    inventory = []
    for e in rule:
        item = dict(e)
        item['source'] = 'immigration_rule_1106'
        item['visable_forms'] = by_annex.get(e['number'], [])
        if e['class'] == 'applicant_facing':
            ids = item['visable_forms']
            if ids:
                statuses = {support[i]['status'] for i in ids}
                item['status'] = 'SUPPORTED' if 'SUPPORTED' in statuses else ('PARTIAL' if 'PARTIAL' in statuses else sorted(statuses)[0])
                item['status_reason'] = '; '.join(f"{i}: {support[i]['status_reason']}" for i in ids if support[i]['status_reason'])
            else:
                item['status'] = 'BLOCKED'
                item['status_reason'] = 'no field map yet (template available in the rule PDF; not mapped or QA’d in this sprint)'
        elif e['class'] in ('excluded_departure', 'excluded_refugee'):
            item['status'] = 'EXCLUDED'
            item['status_reason'] = e['reason']
        else:
            item['status'] = 'NOT_APPLICABLE'
            item['status_reason'] = e['reason']
        inventory.append(item)

    # other sources
    other = [
        {'source': 'overseas_koreans_rule', 'number': '1', 'title': '재외동포(F-4) 통합신청서(신고서) · 국내거소신고서', 'revision': '개정 2022. 4. 12.', 'class': 'applicant_facing', 'domain': 'stay', 'visable_forms': [i for i, r in support.items() if r['annex'] == '1' and r['law'] == 'overseas_koreans_rule'], 'status': None},
        {'source': 'overseas_koreans_rule', 'number': '1의2', 'title': '재외동포(F-4) 통합신청서(신고서) 중문 병기', 'revision': '신설 2022. 4. 12.', 'class': 'applicant_facing', 'domain': 'stay', 'visable_forms': [i for i, r in support.items() if r['annex'] == '1의2' and r['law'] == 'overseas_koreans_rule'], 'status': None},
        {'source': 'overseas_koreans_rule', 'number': '(other annexes)', 'title': '재외동포법 시행규칙 그 밖의 별지 서식', 'revision': '', 'class': 'unknown', 'domain': 'stay', 'visable_forms': [], 'status': 'UNKNOWN', 'status_reason': 'annex list not verifiable offline (law.go.kr unreachable from the build sandbox)'},
        {'source': 'hikorea_forms', 'number': '거주숙소제공확인서', 'title': '거주/숙소제공확인서 (HiKorea 민원서식, 개정 2024. 5.)', 'revision': '개정 2024. 5.', 'class': 'applicant_facing', 'domain': 'stay', 'visable_forms': [i for i, r in support.items() if r['law'] == 'hikorea'], 'status': None},
        {'source': 'refugee_act_rule', 'number': '(all annexes)', 'title': '난민법 시행규칙 서식 전체 (난민인정 신청서, 난민인정증명서, 난민불인정결정 이의신청서 등)', 'revision': '', 'class': 'excluded_refugee', 'domain': 'refugee', 'visable_forms': [], 'status': 'EXCLUDED', 'status_reason': 'policy: refugee-status forms are out of scope for auto-fill; the Refugee Act rule is not among the local sources'},
        {'source': 'hikorea_forms', 'number': '(other forms)', 'title': 'HiKorea 민원서식 자료실 — 421 download links counted on 2026-06-12', 'revision': '', 'class': 'unknown', 'domain': 'mixed', 'visable_forms': [], 'status': 'UNKNOWN', 'status_reason': 'hikorea.go.kr unreachable from the build sandbox; only the accommodation confirmation is held locally'},
    ]
    for o in other:
        if o['status'] is None:
            ids = o['visable_forms']
            statuses = {support[i]['status'] for i in ids} if ids else set()
            o['status'] = 'SUPPORTED' if 'SUPPORTED' in statuses else ('PARTIAL' if 'PARTIAL' in statuses else ('BLOCKED' if not ids else sorted(statuses)[0]))
            o['status_reason'] = '; '.join(f"{i}: {support[i]['status_reason']}" for i in ids if support[i]['status_reason'])
        inventory.append(o)

    counts = {}
    for it in inventory:
        counts[it['status']] = counts.get(it['status'], 0) + 1
    classes = {}
    for it in inventory:
        classes[it['class']] = classes.get(it['class'], 0) + 1
    supported_forms = sorted(i for i, r in support.items() if r['status'] == 'SUPPORTED')
    partial_forms = sorted(i for i, r in support.items() if r['status'] == 'PARTIAL')
    before = ['F01', 'F03', 'F04', 'F05', 'F06', 'F07']
    out = {
        'generated': REPORT_DATE, 'generator': 'scripts/forms/build_forms_inventory.py',
        'sources': {
            'immigration_rule_1106': {'title': '출입국관리법 시행규칙 (법무부령 제1106호, 2026-01-23)', 'text': 'docs/source-manuals/law/rule_1106_full.txt', 'pdf': RULE_PDF, 'annex_count': len(rule), 'note': 'The rule was amended again with effect 2026-09-15 (law.go.kr MST 289833); annex revisions after 2026-01-23 could not be verified offline.'},
            'overseas_koreans_rule': {'title': '재외동포의 출입국과 법적 지위에 관한 법률 시행규칙', 'held_locally': ['별지 제1호', '별지 제1호의2']},
            'hikorea_forms': {'title': 'HiKorea 민원서식 자료실', 'held_locally': ['거주/숙소제공확인서'], 'counted_links_2026_06_12': 421},
        },
        'exclusions': {
            'departure_deadline': [it['number'] for it in inventory if it.get('class') == 'excluded_departure'],
            'refugee': [it['number'] for it in inventory if it.get('class') == 'excluded_refugee'],
        },
        'counts_by_status': counts, 'counts_by_class': classes,
        'visable_support': support, 'supported_before': before, 'supported_now': supported_forms, 'partial_now': partial_forms,
        'newly_supported': [f for f in supported_forms if f not in before],
        'inventory': inventory,
    }
    json_text = json.dumps(out, ensure_ascii=False, indent=1) + '\n'

    # ---- markdown report ----
    app = [it for it in inventory if it['class'] == 'applicant_facing']
    def row(it):
        ids = ', '.join(it.get('visable_forms') or []) or '—'
        return f"| {it['source']} | {it['number']} | {it['title']} | {it.get('revision') or '—'} | {it.get('pdf_page') or '—'} | {ids} | **{it['status']}** | {it.get('status_reason', '')} |"
    md = [f"# Form Helper coverage — {REPORT_DATE}", '',
          'Generated by `scripts/forms/build_forms_inventory.py` from the local official sources; machine-readable twin: `data/forms_inventory.json` (asserted by `scripts/check_form_helper.mjs`).', '',
          '**Support definition** (a blank PDF being downloadable is not support): official current source identified · correct PDF template · fields mapped · data entry, editing and preview work · text lands in the right cells · PDF export works · critical checkbox / date fields work · mobile workflow works · QA passes. Forms that meet every criterion except *edition verification against law.go.kr / HiKorea* (unreachable from the build sandbox) are **PARTIAL**, never SUPPORTED.', '',
          '## Totals', '',
          '| Metric | Count |', '| --- | ---: |',
          f"| TOTAL OFFICIAL FORMS INVENTORIED (rule annexes {len(rule)} + 재외동포 2 + HiKorea 1 + 2 unknown buckets) | {len(inventory)} |",
          f"| Applicant-facing (in scope for a Form Helper) | {len(app)} |",
          f"| SUPPORTED BEFORE (2026-09-22) | {len(before)} ({', '.join(before)}) |",
          f"| SUPPORTED NOW | {len(supported_forms)} ({', '.join(supported_forms) or '—'}) |",
          f"| NEWLY SUPPORTED | {len(out['newly_supported'])} ({', '.join(out['newly_supported']) or '—'}) |",
          f"| FULLY QA'D | {len([i for i in supported_forms if support[i]['qa'] == 'PASS'])} |",
          f"| PARTIAL | {len(partial_forms)} ({', '.join(partial_forms) or '—'}) |",
          f"| BLOCKED (applicant-facing, no field map) | {counts.get('BLOCKED', 0)} |",
          f"| EXCLUDED — DEPARTURE DEADLINE | {len(out['exclusions']['departure_deadline'])} ({', '.join(out['exclusions']['departure_deadline'])}) |",
          f"| EXCLUDED — REFUGEE | {len(out['exclusions']['refugee'])} ({', '.join(out['exclusions']['refugee'])}) |",
          f"| STALE / SUPERSEDED | {counts.get('SUPERSEDED', 0)} |",
          f"| UNKNOWN (sources not verifiable offline) | {counts.get('UNKNOWN', 0)} |",
          f"| NOT APPLICABLE (official-use / enforcement / deleted) | {counts.get('NOT_APPLICABLE', 0)} |",
          '', 'Visable does **not** claim “모든 서류 지원”: the numbers above are the claim.', '',
          '## Visable forms', '',
          '| id | Official name | Legal basis | Revision on form | Template edition | Edition check | Pages | Fields | Map ver. | Status | QA | Reason |', '| --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- |']
    for fid in sorted(support):
        r = support[fid]
        md.append(f"| {fid} | {r['name_ko']} | {r['legal_basis']} | {r['revision_on_form']} | {r['template_edition'] or '—'} | {r['edition_verification'] or '—'} | {r['pages']} | {r['field_count']} | {r['field_map_version'] or '—'} | **{r['status']}** | {r['qa']} | {r['status_reason']} |")
    md += ['', '## Applicant-facing official forms (in scope)', '',
           '| Source | Annex | Title | Revision | Rule PDF page | Visable | Status | Reason |', '| --- | --- | --- | --- | --- | --- | --- | --- |']
    md += [row(it) for it in app]
    md += ['', '## Excluded forms (never offered for auto-fill)', '',
           '| Source | Annex | Title | Class | Reason |', '| --- | --- | --- | --- | --- |']
    md += [f"| {it['source']} | {it['number']} | {it['title']} | {it['class']} | {it.get('status_reason', '')} |" for it in inventory if it['class'] in ('excluded_departure', 'excluded_refugee')]
    md += ['', '## Unknown buckets', '',
           '| Source | Bucket | Note |', '| --- | --- | --- |']
    md += [f"| {it['source']} | {it['number']} | {it.get('status_reason', '')} |" for it in inventory if it['status'] == 'UNKNOWN']
    md += ['', '## Not applicable (official-use, enforcement proceedings, deleted)', '',
           f"{counts.get('NOT_APPLICABLE', 0)} annexes: stamps (심사인·허가인), permits, notices, registers (대장), orders, decisions, detention / removal / penalty proceedings, statistics and deleted numbers. Full list in `data/forms_inventory.json` (`class` ≠ `applicant_facing`).", '',
           '## Source / version risks', '',
           '* Every template extracted from the 법무부령 제1106호 PDF carries the `<개정/신설 …>` date printed on the form itself; whether a later amendment (the rule was amended with effect 2026-09-15) changed that annex could not be verified offline. Such forms are PARTIAL until a law.go.kr check is recorded in `data/form_schemas.json` (`template.verification`).',
           '* F01 / F04 / F07 were verified against law.go.kr on 2026-06-12 (`docs/forms_official/FORM_VERSION_AUDIT.md`); the same 2026-09-15 amendment caveat applies to them.',
           '* `scripts/check_form_helper.mjs` pins each template’s sha256, page count and page size, so a replaced PDF fails CI instead of being filled with stale coordinates.', '']
    md_text = '\n'.join(md)

    if a.check:
        cur_json = open(OUT_JSON, encoding='utf-8').read() if os.path.exists(OUT_JSON) else ''
        cur_md = open(OUT_MD, encoding='utf-8').read() if os.path.exists(OUT_MD) else ''
        if cur_json != json_text or cur_md != md_text:
            print('[build_forms_inventory] STALE — run: python3 scripts/forms/build_forms_inventory.py', file=sys.stderr)
            sys.exit(1)
        print('[build_forms_inventory] OK — inventory and coverage report are current')
        return
    open(OUT_JSON, 'w', encoding='utf-8').write(json_text)
    open(OUT_MD, 'w', encoding='utf-8').write(md_text)
    print(f"[build_forms_inventory] wrote {OUT_JSON} ({len(inventory)} entries) and {OUT_MD}")
    print('counts_by_status', counts)
    print('counts_by_class', classes)


if __name__ == '__main__':
    main()
