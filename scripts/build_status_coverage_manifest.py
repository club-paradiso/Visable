#!/usr/bin/env python3
"""Build the September 2026 status coverage manifest and the compiled guidance bundle.

Inputs (read only):
  data/guidance-rules-202609.json            authored rules (scripts/status_guidance/author_rules.py)
  data/manual-corpus/*.json                  PDF page corpora of the two September manuals
  docs/source-manuals/.../full_text/*.txt    HWP text layers (line provenance, tables)
  visa_data.json                             legacy structured data (conflict detection only — never modified)
  data/i18n/visa-names.json                  parent-status display names

Outputs:
  data/status-coverage-202609.json           coverage manifest (every chapter / status / substatus / program)
  data/status-guidance-202609.json           compiled runtime bundle (rules + resolved provenance + code index)
  reports/data-coverage/status-coverage-202609.{json,md}

  --check   verify the committed outputs are up to date (CI)
Anchors that cannot be found in the manual fail the build.
"""
import argparse
import collections
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RULES = os.path.join(ROOT, 'data', 'guidance-rules-202609.json')
MANIFEST_OUT = os.path.join(ROOT, 'data', 'status-coverage-202609.json')
BUNDLE_OUT = os.path.join(ROOT, 'data', 'status-guidance-202609.json')
REPORT_JSON = os.path.join(ROOT, 'reports', 'data-coverage', 'status-coverage-202609.json')
REPORT_MD = os.path.join(ROOT, 'reports', 'data-coverage', 'status-coverage-202609.md')

SOURCES = {
    'stay_manual_2026_09_18': {
        'id': 'stay_manual_2026_09_18', 'domain': 'stay', 'title_ko': '외국인체류 안내매뉴얼', 'title_en': 'Foreigner Stay/Residence Guide Manual',
        'edition': '2026.9', 'date': '2026-09-18', 'authority': '법무부 출입국·외국인정책본부',
        'pdf': 'docs/source-manuals/2026-09/stay_manual_260918.pdf', 'corpus': 'data/manual-corpus/stay_manual_2026_09_18_pdf.json', 'corpus_source_id': 'stay_manual_2026_09_18_pdf',
        'hwp': 'docs/source-manuals/2026-09/stay_manual_260918.hwp', 'text': 'docs/source-manuals/2026-09/extracted/full_text/stay_manual_260918.txt',
        'review_state': 'needs_review', 'official_url': 'https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&BBS_GB_CD=BS10&NTCCTT_SEQ=1062&page=1',
    },
    'visa_manual_2026_09_01': {
        'id': 'visa_manual_2026_09_01', 'domain': 'visa', 'title_ko': '사증발급 안내매뉴얼', 'title_en': 'Visa Issuance Guide Manual',
        'edition': '2026.9', 'date': '2026-09-01', 'authority': '법무부 출입국·외국인정책본부',
        'pdf': 'docs/source-manuals/2026-09/visa_manual_260901.pdf', 'corpus': 'data/manual-corpus/visa_manual_2026_09_01_pdf.json', 'corpus_source_id': 'visa_manual_2026_09_01_pdf',
        'hwp': 'docs/source-manuals/2026-09-01/visa_manual_260901.hwp', 'text': 'docs/source-manuals/2026-09-01/extracted/full_text/visa_manual_260901.txt',
        'review_state': 'needs_review', 'official_url': 'https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&BBS_GB_CD=BS10&NTCCTT_SEQ=1062&page=1',
    },
}

# Chapter registries transcribed from each manual's 目次 (order = manual order).
STAY_CHAPTERS = [
    ('preamble-notes', None, '각종 체류허가 신청 시 유의사항', 'Notes for every stay permit application', 'preamble'),
    ('preamble-common', None, '공통사항 (체류 일반)', 'Common rules (general stay)', 'preamble'),
    ('A-1', 'A-1', '외교(A-1)', 'Diplomat (A-1)', 'status'), ('A-2', 'A-2', '공무(A-2)', 'Government official (A-2)', 'status'), ('A-3', 'A-3', '협정(A-3)', 'Agreement (A-3)', 'status'),
    ('B-1', 'B-1', '사증면제(B-1)', 'Visa waiver (B-1)', 'status'), ('B-2', 'B-2', '관광통과(B-2)', 'Tourist / transit (B-2)', 'status'),
    ('C-1', 'C-1', '일시취재(C-1)', 'Temporary journalism (C-1)', 'status'), ('C-3', 'C-3', '단기방문(C-3)', 'Short-term visit (C-3)', 'status'), ('C-4', 'C-4', '단기취업(C-4)', 'Short-term employment (C-4)', 'status'),
    ('D-1', 'D-1', '문화예술(D-1)', 'Culture and arts (D-1)', 'status'), ('D-2', 'D-2', '유학(D-2)', 'Study (D-2)', 'status'), ('D-3', 'D-3', '기술연수(D-3)', 'Technical training (D-3)', 'status'), ('D-4', 'D-4', '일반연수(D-4)', 'General training (D-4)', 'status'),
    ('D-5', 'D-5', '취재(D-5)', 'Journalism (D-5)', 'status'), ('D-6', 'D-6', '종교(D-6)', 'Religion (D-6)', 'status'), ('D-7', 'D-7', '주재(D-7)', 'Intra-company transfer (D-7)', 'status'), ('D-8', 'D-8', '기업투자(D-8)', 'Corporate investment (D-8)', 'status'),
    ('D-9', 'D-9', '무역경영(D-9)', 'Trade management (D-9)', 'status'), ('D-10', 'D-10', '구직(D-10)', 'Job seeking (D-10)', 'status'),
    ('E-1', 'E-1', '교수(E-1)', 'Professor (E-1)', 'status'), ('E-2', 'E-2', '회화지도(E-2)', 'Foreign language instructor (E-2)', 'status'), ('E-3', 'E-3', '연구(E-3)', 'Research (E-3)', 'status'), ('E-4', 'E-4', '기술지도(E-4)', 'Technical instruction (E-4)', 'status'),
    ('E-5', 'E-5', '전문직업(E-5)', 'Professional (E-5)', 'status'), ('E-6', 'E-6', '예술흥행(E-6)', 'Arts and entertainment (E-6)', 'status'), ('E-7', 'E-7', '특정활동(E-7)', 'Specific activities (E-7)', 'status'), ('E-8', 'E-8', '계절근로(E-8)', 'Seasonal work (E-8)', 'status'),
    ('E-9', 'E-9', '비전문취업(E-9)', 'Non-professional employment (E-9)', 'status'), ('E-10', 'E-10', '선원취업(E-10)', 'Crew employment (E-10)', 'status'),
    ('F-1', 'F-1', '방문동거(F-1)', 'Visiting / family stay (F-1)', 'status'), ('F-2', 'F-2', '거주(F-2)', 'Residence (F-2)', 'status'), ('F-3', 'F-3', '동반(F-3)', 'Dependant (F-3)', 'status'),
    ('F-5', 'F-5', '영주(F-5):동포,난민제외', 'Permanent residence (F-5), excluding compatriots and refugees', 'status'), ('F-6', 'F-6', '결혼이민(F-6)', 'Marriage migrant (F-6)', 'status'),
    ('G-1', 'G-1', '기타(G-1)', 'Miscellaneous (G-1)', 'status'), ('H-1', 'H-1', '관광취업(H-1)', 'Working holiday (H-1)', 'status'),
    ('DONGPO', None, '외국국적동포 관련 (C-3-8, F-1, H-2, F-4, F-5)', 'Overseas Koreans (C-3-8, F-1, H-2, F-4, F-5)', 'program'),
    ('REGION', None, '지역특화형비자', 'Regional specialised visa', 'program'), ('YOUTH', None, '국내 성장 기반 외국인 청소년 취업‧정주 체류제도', 'Domestically raised foreign youth scheme', 'program'),
    ('TOPTIER', None, '톱티어(Top-Tier) 비자(D-10-T, E-7-T, F-2-T, F-5-T)', 'Top-Tier visa', 'program'), ('METRO', None, '광역형 비자 시범사업', 'Metropolitan / provincial visa pilot', 'program'), ('KSTAR', None, 'K-STAR 비자트랙 제도', 'K-STAR visa track', 'program'),
]
VISA_CHAPTERS = [
    ('preamble-notes', None, '유의사항', 'Notes', 'preamble'), ('preamble-common', None, '공통사항 (외국인 결핵진단서 제출 의무)', 'Common rules (TB certificate)', 'preamble'),
    ('A-1', 'A-1', '외교(A-1)', 'Diplomat (A-1)', 'status'), ('A-2', 'A-2', '공무(A-2)', 'Government official (A-2)', 'status'), ('A-3', 'A-3', '협정(A-3)', 'Agreement (A-3)', 'status'),
    ('B-1', 'B-1', '사증면제(B-1)', 'Visa waiver (B-1)', 'status'), ('B-2', 'B-2', '관광통과(B-2)', 'Tourist / transit (B-2)', 'status'),
    ('C-1', 'C-1', '일시취재(C-1)', 'Temporary journalism (C-1)', 'status'), ('C-3', 'C-3', '단기방문(C-3)', 'Short-term visit (C-3)', 'status'), ('C-4', 'C-4', '단기취업(C-4)', 'Short-term employment (C-4)', 'status'),
    ('D-1', 'D-1', '문화예술(D-1)', 'Culture and arts (D-1)', 'status'), ('D-2', 'D-2', '유학(D-2)', 'Study (D-2)', 'status'), ('D-3', 'D-3', '기술연수(D-3)', 'Technical training (D-3)', 'status'), ('D-4', 'D-4', '일반연수(D-4)', 'General training (D-4)', 'status'),
    ('D-5', 'D-5', '취재(D-5)', 'Journalism (D-5)', 'status'), ('D-6', 'D-6', '종교(D-6)', 'Religion (D-6)', 'status'), ('D-7', 'D-7', '주재(D-7)', 'Intra-company transfer (D-7)', 'status'), ('D-8', 'D-8', '기업투자(D-8)', 'Corporate investment (D-8)', 'status'),
    ('D-9', 'D-9', '무역경영(D-9)', 'Trade management (D-9)', 'status'), ('D-10', 'D-10', '구직(D-10)', 'Job seeking (D-10)', 'status'),
    ('E-1', 'E-1', '교수(E-1)', 'Professor (E-1)', 'status'), ('E-2', 'E-2', '회화지도(E-2)', 'Foreign language instructor (E-2)', 'status'), ('E-3', 'E-3', '연구(E-3)', 'Research (E-3)', 'status'), ('E-4', 'E-4', '기술지도(E-4)', 'Technical instruction (E-4)', 'status'),
    ('E-5', 'E-5', '전문직업(E-5)', 'Professional (E-5)', 'status'), ('E-6', 'E-6', '예술흥행(E-6)', 'Arts and entertainment (E-6)', 'status'), ('E-7', 'E-7', '특정활동(E-7)', 'Specific activities (E-7)', 'status'), ('E-8', 'E-8', '계절근로(E-8)', 'Seasonal work (E-8)', 'status'),
    ('E-9', 'E-9', '비전문취업(E-9)', 'Non-professional employment (E-9)', 'status'), ('E-10', 'E-10', '선원취업(E-10)', 'Crew employment (E-10)', 'status'),
    ('F-1', 'F-1', '방문동거(F-1)', 'Visiting / family stay (F-1)', 'status'), ('F-2', 'F-2', '거주(F-2)', 'Residence (F-2)', 'status'), ('F-3', 'F-3', '동반(F-3)', 'Dependant (F-3)', 'status'),
    ('F-4', 'F-4', '재외동포(F-4) ※ 38.번 참조', 'Overseas Korean (F-4) — see ch. 38', 'status'), ('F-5', 'F-5', '영주(F-5) ※ 동포는 38.번 참조', 'Permanent residence (F-5) — compatriots see ch. 38', 'status'), ('F-6', 'F-6', '결혼이민(F-6)', 'Marriage migrant (F-6)', 'status'),
    ('G-1', 'G-1', '기타(G-1)', 'Miscellaneous (G-1)', 'status'), ('H-1', 'H-1', '관광취업(H-1)', 'Working holiday (H-1)', 'status'), ('H-2', 'H-2', '방문취업(H-2) ※ 38.번 참조', 'Visiting employment (H-2) — see ch. 38', 'status'),
    ('DONGPO', None, '알기쉬운 외국국적동포 업무매뉴얼', 'Overseas-Korean manual', 'program'), ('TOPTIER', None, '톱티어 비자(D-10-T, E-7-T, F-2-T, F-5-T)', 'Top-Tier visa', 'program'), ('KSTAR', None, 'K-STAR 비자트랙 제도', 'K-STAR visa track', 'program'),
]

# Heading text used to detect where each chapter starts in the PDF corpus / HWP text.
CHAPTER_HEADINGS = {
    'A-1': ['외교(A-1)'], 'A-2': ['공무(A-2)'], 'A-3': ['협정(A-3)'], 'B-1': ['사증면제(B-1)'], 'B-2': ['관광통과(B-2)'], 'C-1': ['일시취재(C-1)'], 'C-3': ['단기방문(C-3)'], 'C-4': ['단기취업(C-4)'],
    'D-1': ['문화예술(D-1)'], 'D-2': ['유학(D-2)'], 'D-3': ['기술연수(D-3)'], 'D-4': ['일반연수(D-4)'], 'D-5': ['취재(D-5)'], 'D-6': ['종교(D-6)'], 'D-7': ['주재(D-7)'], 'D-8': ['기업투자(D-8)'], 'D-9': ['무역경영(D-9)'], 'D-10': ['구직(D-10)'],
    'E-1': ['교수(E-1)'], 'E-2': ['회화지도(E-2)'], 'E-3': ['연구(E-3)'], 'E-4': ['기술지도(E-4)'], 'E-5': ['전문직업(E-5)'], 'E-6': ['예술흥행(E-6)'], 'E-7': ['특정활동(E-7)'], 'E-8': ['계절근로(E-8)'], 'E-9': ['비전문취업(E-9)'], 'E-10': ['선원취업(E-10)'],
    'F-1': ['방문동거(F-1)'], 'F-2': ['거주(F-2)'], 'F-3': ['동반(F-3)'], 'F-4': ['재외동포(F-4)'], 'F-5': ['영주(F-5)'], 'F-6': ['결혼이민(F-6)'], 'G-1': ['기타(G-1)'], 'H-1': ['관광취업(H-1)'], 'H-2': ['방문취업(H-2)'],
    'DONGPO': ['알기쉬운 외국국적동포 업무 매뉴얼', '알기쉬운 외국국적동포 업무매뉴얼'], 'REGION': ['지역특화형비자 체류제도 주요내용 알림', '지역특화형비자'], 'YOUTH': ['국내 성장 기반 외국인 청소년 취업·정주 체류제도 알림', '국내 성장 기반 외국인 청소년'],
    'TOPTIER': ['톱티어(Top-Tier) 사증발급 및 체류관리 지침', '톱티어'], 'METRO': ['광역형 비자 시범사업'], 'KSTAR': ['K-STAR 비자트랙', 'K-STAR'],
    'preamble-notes': ['유의사항'], 'preamble-common': ['공통사항'],
}

PROCEDURE_SECTION_LABELS = {  # stay manual section headings per procedure
    'extension': ['체류기간 연장허가', '체류기간연장'], 'status_change': ['체류자격 변경허가', '체류자격변경'], 'registration': ['외국인등록'], 'reentry': ['재입국허가', '재입국'],
    'activities_outside_status': ['체류자격외 활동'], 'part_time_work': ['시간제취업 활동 허가', '시간제 취업'], 'workplace_change': ['근무처의 변경․추가', '근무처 변경'], 'status_grant': ['체류자격 부여', '체류자격\n부    여'],
    'registration_info_report': ['등록사항 변경신고', '외국인등록사항 변경신고'], 'residence_report': ['체류지 변경'], 'card_reissue': ['재발급'], 'workplace_report': ['취업개시 신고', '고용주 신고'],
    'program_condition_change': ['허가조건'],
}
VISA_PROCEDURES = ['visa_issuance', 'visa_issuance_confirmation', 'electronic_visa']
STAY_PROCEDURES = ['status_grant', 'status_change', 'extension', 'registration', 'card_reissue', 'activities_outside_status', 'part_time_work', 'workplace_change', 'workplace_report', 'reentry', 'residence_report', 'registration_info_report', 'program_condition_change']

CODE_RE = re.compile(r'\b([A-H]-\d{1,2}(?:-[0-9A-Z]{1,6})?)\b')
SUB_RE = re.compile(r'^\s*([A-H]-\d{1,2}-[0-9A-Z]{1,6})\s*$')
MENTION_RE = re.compile(r'([가-힣A-Za-z0-9·‧,()\s]{2,40}?)\(([A-H]-\d{1,2}-[0-9A-Z]{1,6})\)')

DOT_CHARS = '․·‧ㆍ∙‥'
DASH_CHARS = '‐‑‒–—−－'
STRIP_CHARS = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳❍○◦▪‣□■•▣※*㉮㉯㉰㉱㉲㉳㉴㉵㉶㉷㉸㉹㉺㉻➀➁➂➃➄➅➆➇➈➉ⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ'


def norm(text):
    text = unicodedata.normalize('NFKC', text or '')
    text = text.translate(str.maketrans({c: '·' for c in DOT_CHARS}))
    text = text.translate(str.maketrans({c: '-' for c in DASH_CHARS}))
    text = text.translate(str.maketrans({c: '' for c in STRIP_CHARS}))
    text = text.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"').replace('｢', '「').replace('｣', '」').replace('（', '(').replace('）', ')').replace('∼', '~').replace('～', '~')
    text = re.sub(r'\s+', '', text)
    return text.lower()


def load_json(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return json.load(fh)


DUP_RE = re.compile(r'(.{2,25}?)\1')


SIDEBAR_FRAGMENTS = [norm(x) for x in ['󰁾 목차', '목차', '체류자격외 활동', '근무처의 변경․추가', '근무처의변경', '체류자격 변경허가', '체류기간 연장허가', '체류자격변경', '체류기간연장', '재입국허가', '외국인등록', '체류자격 부여', '활동범위', '자격 해당자 및 활동범위', '해당자', '제출서류', '체류기간', '연장허가', '변경허가', '체류자격', '부여', '재입국', '자격외활동', '근무처', '변경·추가', '1회에 부여할 수 있는 상한', '상한']]
SIDEBAR_FRAGMENTS.sort(key=len, reverse=True)
PAGE_NO_RE = re.compile(r'-\d{1,3}-')


def loose(text):
    for f in SIDEBAR_FRAGMENTS:
        text = text.replace(f, '')
    return dedup(PAGE_NO_RE.sub('', text))


def dedup(text):
    """Collapse the duplicate-paint artifacts left in the PDF text layer ("서류서류(요청시(요청시제출)")."""
    prev = None
    while prev != text:
        prev = text
        text = DUP_RE.sub(r'\1', text)
    return text


class Manual:
    def __init__(self, meta):
        self.meta = meta
        self.pages = load_json(meta['corpus'])
        self.page_text = {p['page']: norm(p['text']) for p in self.pages}
        self.page_text_dedup = {pg: dedup(t) for pg, t in self.page_text.items()}
        self.page_text_loose = {pg: loose(t) for pg, t in self.page_text.items()}
        self.page_heading = {p['page']: p.get('heading', '') for p in self.pages}
        self.page_codes = {p['page']: set(p.get('status_codes_detected', []) + p.get('subcodes_detected', [])) for p in self.pages}
        with open(os.path.join(ROOT, meta['text']), encoding='utf-8') as fh:
            self.lines = fh.read().split('\n')
        self.norm_lines = [norm(l) for l in self.lines]
        self.max_page = max(self.page_text)

    def _spans(self, index, pg, a):
        """True only when `a` straddles the boundary between pg and pg+1 (not fully inside either)."""
        nxt = index.get(pg + 1)
        if nxt is None:
            return False
        cur = index.get(pg, '')
        return a not in cur and a not in nxt and a in cur + nxt

    def page_has(self, pg, a, al=None, span=True):
        if a in self.page_text.get(pg, '') or a in self.page_text_dedup.get(pg, ''):
            return True
        if span and (self._spans(self.page_text, pg, a) or self._spans(self.page_text_dedup, pg, a)):
            return True
        if al and len(al) >= 6:
            if al in self.page_text_loose.get(pg, ''):
                return True
            if span and self._spans(self.page_text_loose, pg, al):
                return True
        return False

    def find_pages(self, anchor, lo=1, hi=None):
        a = dedup(norm(anchor))
        al = loose(norm(anchor))
        hi = hi or self.max_page
        exact = [pg for pg in range(max(1, lo), hi + 1) if self.page_has(pg, a)]
        if exact:
            return exact
        return [pg for pg in range(max(1, lo), hi + 1) if self.page_has(pg, a, al)]

    def find_lines(self, anchor, lo=0, hi=None):
        a = norm(anchor)
        hi = min(hi or len(self.lines), len(self.lines))
        hits = [i + 1 for i in range(lo, hi) if a in self.norm_lines[i]]
        if hits:
            return hits
        return [i + 1 for i in range(lo, max(lo, hi - 2)) if a in ''.join(self.norm_lines[i:i + 3])]

    def find_line(self, anchor, lo=0, hi=None):
        hits = self.find_lines(anchor, lo, hi)
        return hits[0] if hits else None


def detect_chapters(manual, registry):
    """Return {key: {pdf_start, pdf_end, hwp_start, hwp_end, detection}} in manual order.

    Detection order per chapter: (1) the PDF page heading starts with the chapter title,
    (2) the title appears in the first 400 characters of a page after the previous chapter,
    (3) a window fallback on detected status codes. Chapters whose 目次 entry points at
    another chapter ("※ 38.번 참조") are REFERENCE chapters: they take the target's range
    and never advance the cursor.
    """
    out = collections.OrderedDict()
    prev_page, prev_line = 2, 10
    references = {}
    for key, code, title_ko, title_en, kind in registry:
        heads = CHAPTER_HEADINGS.get(key, [title_ko])
        if '※' in title_ko and '참조' in title_ko:
            references[key] = 'DONGPO'
            out[key] = {'key': key, 'code': code, 'title_ko': title_ko, 'title_en': title_en, 'kind': 'reference', 'pdf_start': None, 'hwp_start': None, 'detection': 'reference:DONGPO'}
            continue
        page, detection = None, 'heading'
        for h in heads:
            hn = norm(h)
            for pg in range(prev_page + 1, manual.max_page + 1):
                heading = norm(manual.page_heading.get(pg, ''))
                if heading.startswith(hn) or (kind == 'program' and hn in heading and len(heading) < 80):
                    page = pg
                    break
            if page:
                break
        # HWP heading line (needed for content-anchored PDF detection below)
        line = None
        for h in heads:
            hn = norm(h)
            for i in range(prev_line, len(manual.lines)):
                nl = manual.norm_lines[i]
                if nl == hn or (kind == 'program' and nl.startswith(hn) and len(nl) < 60):
                    line = i + 1
                    break
            if line:
                break
        if not page and line:
            detection = 'content'
            generic = {norm(x) for x in ['1회에 부여할 수 있는 체류기간 상한', '자격 해당자 및 활동범위', '활동범위', '해당자', '체류자격외 활동', '재입국허가', '외국인등록']}
            probes = [manual.norm_lines[j] for j in range(line, min(line + 10, len(manual.lines))) if len(manual.norm_lines[j]) >= 18 and manual.norm_lines[j] not in generic]
            for probe in probes[:3]:
                for pg in range(prev_page + 1, min(manual.max_page, prev_page + 160) + 1):
                    if code and code not in manual.page_codes.get(pg, set()):
                        continue
                    if manual.page_has(pg, probe[:40], loose(probe[:40])):
                        page = pg
                        break
                if page:
                    break
        if not page:
            detection = 'text-head'
            for h in heads:
                hn = norm(h)
                for pg in range(prev_page + 1, manual.max_page + 1):
                    if 0 <= manual.page_text.get(pg, '').find(hn) < 60:
                        page = pg
                        break
                if page:
                    break
        if not page and code:
            detection = 'window'
            for pg in range(prev_page + 1, manual.max_page + 1):
                if code in manual.page_codes.get(pg, set()):
                    page = pg
                    break
        out[key] = {'key': key, 'code': code, 'title_ko': title_ko, 'title_en': title_en, 'kind': kind, 'pdf_start': page, 'hwp_start': line, 'detection': detection if page else 'missing'}
        if page:
            prev_page = page
        if line:
            prev_line = line
    keys = [k for k in out if out[k]['kind'] != 'reference']
    for i, k in enumerate(keys):
        nxt_pages = [out[j]['pdf_start'] for j in keys[i + 1:] if out[j]['pdf_start']]
        nxt_lines = [out[j]['hwp_start'] for j in keys[i + 1:] if out[j]['hwp_start']]
        out[k]['pdf_end'] = (nxt_pages[0] - 1) if nxt_pages else manual.max_page
        out[k]['hwp_end'] = (nxt_lines[0] - 1) if nxt_lines else len(manual.lines)
    for k, target in references.items():
        t = out.get(target) or {}
        out[k].update({'pdf_start': t.get('pdf_start'), 'pdf_end': t.get('pdf_end'), 'hwp_start': t.get('hwp_start'), 'hwp_end': t.get('hwp_end')})
    return out


SECTION_HEADINGS = ['체류자격외 활동', '근무처의 변경․추가', '체류자격 변경허가', '체류기간 연장허가', '재입국허가', '외국인등록', '체류자격']


def section_line_range(manual, ch, procedure):
    """(start, end) HWP line range of a procedure section inside a chapter, or None."""
    if not ch or not ch.get('hwp_start'):
        return None
    labels = [norm(l) for l in PROCEDURE_SECTION_LABELS.get(procedure, [])]
    heads = [norm(h) for h in SECTION_HEADINGS]
    lo, hi = ch['hwp_start'] - 1, ch.get('hwp_end') or len(manual.lines)
    start = None
    for i in range(lo, hi):
        nl = manual.norm_lines[i]
        if start is None and nl in labels:
            start = i
            continue
        if start is not None and nl in heads and nl not in labels and i - start > 3:
            return (start, i)
    return (start, hi) if start is not None else None


def parent_of(code):
    parts = code.split('-')
    return '-'.join(parts[:2]) if len(parts) >= 2 else code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    rules = load_json('data/guidance-rules-202609.json')
    legacy = load_json('visa_data.json')
    names = load_json('data/i18n/visa-names.json')['names']
    manuals = {k: Manual(v) for k, v in SOURCES.items()}
    stay, visa = manuals['stay_manual_2026_09_18'], manuals['visa_manual_2026_09_01']
    chapters = {'stay_manual_2026_09_18': detect_chapters(stay, STAY_CHAPTERS), 'visa_manual_2026_09_01': detect_chapters(visa, VISA_CHAPTERS)}
    errors = []
    for mid, ch in chapters.items():
        for k, c in ch.items():
            if not c['pdf_start']:
                errors.append(f'{mid}: chapter {k} ({c["title_ko"]}) not found in PDF corpus')
            if not c['hwp_start']:
                errors.append(f'{mid}: chapter {k} ({c["title_ko"]}) not found in HWP text')

    CHAPTER_ALIAS = {'F-4': 'DONGPO', 'H-2': 'DONGPO', 'C-3-8': 'DONGPO'}

    def chapter_for(manual_id, code):
        ch = chapters[manual_id]
        key = code if code in ch else parent_of(code)
        if key not in ch or ch[key].get('kind') == 'reference':
            key = CHAPTER_ALIAS.get(code, CHAPTER_ALIAS.get(parent_of(code), key))
        return ch.get(key)

    # ------------------------------------------------------------ subcodes
    def scan_subcodes(manual):
        cells, mentions = {}, collections.defaultdict(collections.Counter)
        for i, l in enumerate(manual.lines):
            m = SUB_RE.match(l)
            if m:
                j = i + 1
                while j < len(manual.lines) and not manual.lines[j].strip():
                    j += 1
                label = manual.lines[j].strip() if j < len(manual.lines) else ''
                if not SUB_RE.match(label) and 1 < len(label) < 70:
                    cells.setdefault(m.group(1), (i + 1, label))
            for mm in MENTION_RE.finditer(l):
                name = mm.group(1).strip()
                name = re.sub(r'^.*?[:：·,]\s*', '', name).strip()
                if 1 < len(name) < 40:
                    mentions[mm.group(2)][name] += 1
        return cells, mentions

    stay_cells, stay_mentions = scan_subcodes(stay)
    visa_cells, visa_mentions = scan_subcodes(visa)
    all_text = {'stay': '\n'.join(stay.norm_lines), 'visa': '\n'.join(visa.norm_lines)}

    def code_in_manual(code, dom):
        pat = re.compile(re.escape(norm(code)) + r'(?![0-9a-z])')
        return bool(pat.search(all_text[dom]))

    legacy_by_code = {r['code']: r for r in legacy}
    legacy_subs = {}
    for r in legacy:
        for s in (r.get('subcodes') or []):
            legacy_subs.setdefault(s['code'], (r['code'], s))

    # Universe of subcodes: manual tables + manual mentions + guidance targets + legacy subcodes
    guidance_targets = set()
    for g in rules['guidance']:
        t = g['target'].split('~')[0]
        guidance_targets.add(t)
    family_targets = set()
    for fam, spec in rules['families'].items():
        for d in spec['dimensions']:
            for o in d['options']:
                for t in o['targets']:
                    family_targets.add(t.split('#')[0].split('~')[0])
    program_codes = set()
    for p in rules['programs']:
        program_codes.update(p['codes'])
        program_codes.update(p.get('applies_to_parents') or [])
    universe = set(stay_cells) | set(visa_cells) | set(stay_mentions) | set(visa_mentions) | {c for c in guidance_targets if c.count('-') >= 2} | {c for c in family_targets if c.count('-') >= 2} | {c for c in program_codes if c.count('-') >= 2} | set(legacy_subs)
    universe = {c for c in universe if re.match(r'^[A-H]-\d{1,2}-[0-9A-Z]{1,6}$', c)}

    # temporal / legacy markers read from the text
    LEGACY_RULES = {
        'H-2': {'new_application_allowed': False, 'existing_holder_only': True, 'effective_to': '2026-02-12', 'superseded_by': 'F-4', 'anchor': '‘26. 2. 12.자로 방문취업(H-2) 사증의 신규 발급이 중단됩니다', 'manual': 'stay_manual_2026_09_18', 'note_ko': '2026-02-12부터 신규 사증 발급 중단(동포 체류자격 F-4 통합). 기존 소지자 체류관리는 계속됩니다.', 'note_en': 'New visas stopped 2026-02-12 (merged into F-4); existing holders continue to be managed.'},
        'D-3-1': {'new_application_allowed': False, 'existing_holder_only': True, 'effective_to': '2006-12-31', 'superseded_by': 'D-3-11', 'anchor': '‘06.12.31.까지 D-3-1 자격 등록자', 'manual': 'stay_manual_2026_09_18', 'note_ko': '2006-12-31까지 등록자에게만 남아 있는 구 약호입니다.', 'note_en': 'Legacy subcode kept only for holders registered by 2006-12-31.'},
        'E-7-91': {'legacy_alias': 'T6', 'anchor': 'T6(구약호)', 'manual': 'stay_manual_2026_09_18', 'note_ko': '구약호 T6에서 이어지는 FTA 독립전문가 약호입니다.', 'note_en': 'FTA independent professional subcode continuing legacy code T6.'},
        'F-2-6': {'new_application_allowed': False, 'existing_holder_only': False, 'effective_to': '2019-10-01', 'superseded_by': 'F-2-99', 'anchor': '숙련생산기능 거주인력 체류자격은 ‘19. 10. 1.부로 폐지되었기에', 'manual': 'stay_manual_2026_09_18', 'note_ko': '2019-10-01 폐지, 기존 허가자는 기타 장기체류자(F-2-99)로 직권 정정되었습니다.', 'note_en': 'Abolished 2019-10-01; existing holders were converted to F-2-99.'},
        'F-1-1': {'legacy_holder_rule': True, 'superseded_by': 'F-2-2', 'anchor': '기존 방문동거(F-1-1)자격으로 체류하고 있는 국민의 미성년 외국인 자녀에 대해서는 확인즉시 수수료 없이 거주(F-2-2)자격 변경', 'manual': 'stay_manual_2026_09_18', 'note_ko': '기존 F-1-1로 체류 중인 국민의 미성년 외국인 자녀는 확인 즉시 수수료 없이 F-2-2로 변경됩니다.', 'note_en': 'Legacy F-1-1 minor children of nationals are converted to F-2-2 without fee.'},
        'F-2-1': {'legacy_alias': 'F-6', 'anchor': '결혼이민(F-6, 기존 F-2-1, F-2-10 포함)', 'manual': 'stay_manual_2026_09_18', 'note_ko': '결혼이민(F-6)의 구 약호입니다.', 'note_en': 'Legacy code now covered by F-6.'},
        'F-2-10': {'legacy_alias': 'F-6', 'anchor': '결혼이민(F-6, 기존 F-2-1, F-2-10 포함)', 'manual': 'stay_manual_2026_09_18', 'note_ko': '결혼이민(F-6)의 구 약호입니다.', 'note_en': 'Legacy code now covered by F-6.'},
    }
    for code, rule in LEGACY_RULES.items():
        m = manuals[rule['manual']]
        pages = m.find_pages(rule['anchor'])
        if not pages:
            errors.append(f'legacy anchor not found for {code}: {rule["anchor"]}')
        rule['pdf_page'] = pages[0] if pages else None
        rule['hwp_line'] = m.find_line(rule['anchor'])

    # ------------------------------------------------------- resolve anchors
    def locate(manual_id, anchor, ch=None, procedure=None, near_page=None, window=2):
        """Resolve an anchor to (pages, hwp_line). Section-aware: when the same title occurs in
        several procedure sections of a chapter (변경 vs 연장), the occurrence inside the requested
        procedure section is chosen in the HWP text and the PDF occurrence with the same ordinal
        is used when the counts agree; otherwise the PDF page nearest to the section is used."""
        m = manuals[manual_id]
        lo_page = ch['pdf_start'] if ch and ch.get('pdf_start') else 1
        hi_page = ch['pdf_end'] if ch and ch.get('pdf_end') else m.max_page
        lo_line = (ch['hwp_start'] - 1) if ch and ch.get('hwp_start') else 0
        hi_line = ch['hwp_end'] if ch and ch.get('hwp_end') else len(m.lines)
        if near_page:
            pages = m.find_pages(anchor, near_page - 1, near_page + window)
            lines = m.find_lines(anchor, lo_line, hi_line) or m.find_lines(anchor)
            return pages, (lines[0] if lines else None)
        lines = m.find_lines(anchor, lo_line, hi_line)
        pages = m.find_pages(anchor, lo_page, hi_page)
        if not lines or not pages:
            lines = lines or m.find_lines(anchor)
            pages = pages or m.find_pages(anchor)
            return pages, (lines[0] if lines else None)
        idx = 0
        rng = section_line_range(m, ch, procedure) if procedure else None
        if rng:
            inside = [i for i, ln in enumerate(lines) if rng[0] < ln - 1 < rng[1]]
            if inside:
                idx = inside[0]
        if len(pages) == len(lines) and idx < len(pages):
            return [pages[idx]] + [p for p in pages if p != pages[idx]], lines[idx]
        if rng and len(pages) > 1:
            # estimate the PDF page where the procedure section starts, then take the first anchor page at or after it
            sec_page = None
            for j in range(rng[0] + 1, min(rng[0] + 25, len(m.lines))):
                probe = m.norm_lines[j]
                if len(probe) >= 18 and probe not in {norm(x) for x in PROCEDURE_SECTION_LABELS.get(procedure, [])}:
                    hit = m.find_pages(m.lines[j].strip()[:60], lo_page, hi_page)
                    if hit:
                        sec_page = hit[0]
                        break
            if sec_page:
                after = [pg for pg in pages if pg >= sec_page - 1]
                if after:
                    return after + [p for p in pages if p not in after], lines[idx]
        if rng and len(pages) > 1:
            # choose the PDF page whose text also carries the section's first content line
            ctx = None
            for j in range(rng[0] + 1, min(rng[0] + 12, len(m.lines))):
                if len(m.norm_lines[j]) > 12:
                    ctx = m.norm_lines[j][:40]
                    break
            if ctx:
                for pg in pages:
                    if m.page_has(pg, ctx) or m.page_has(pg, dedup(ctx)):
                        return [pg] + [p for p in pages if p != pg], lines[idx]
        return pages, lines[idx]

    guidance_out = []
    doc_defs = {d['id']: d for d in rules['document_definitions']}
    for g in rules['guidance']:
        entry = json.loads(json.dumps(g))
        src = entry['source']
        mid = src['manual']
        base_code = entry['target'].split('~')[0]
        ch = chapter_for(mid, base_code)
        pages, line = locate(mid, src['anchor'], ch, entry['procedure'])
        if not pages:
            errors.append(f'guidance {entry["target"]}|{entry["procedure"]}: section anchor not found: {src["anchor"][:60]}')
            continue
        # Self-correcting choice among candidate pages: prefer the page whose window resolves the most document anchors.
        if len(pages) > 1 and entry['documents']:
            win = src.get('doc_page_window', 2)
            scored = []
            for cand in pages[:6]:
                hits = sum(1 for d in entry['documents'] if manuals[mid].find_pages(d.get('anchor') or src['anchor'], cand - 1, cand + win))
                scored.append((hits, -pages.index(cand), cand))
            best = max(scored)
            pages = [best[2]] + [p for p in pages if p != best[2]]
        src['pdf_page'] = pages[0]
        src['pdf_pages'] = pages[:4]
        src['hwp_line'] = line
        src['file'] = SOURCES[mid]['pdf']
        src['edition'] = SOURCES[mid]['edition']
        src['date'] = SOURCES[mid]['date']
        src['chapter'] = ch['key'] if ch else None
        src['chapter_title_ko'] = ch['title_ko'] if ch else None
        src['review_state'] = SOURCES[mid]['review_state']
        for d in entry['documents']:
            dd = doc_defs[d['ref']]
            d['name_ko'] = dd['name_ko']
            d['name_en'] = dd['name_en']
            d.setdefault('applicant_role', dd['default_role'])
            d.setdefault('where_to_obtain', dd['where_to_obtain'])
            a = d.get('anchor') or src['anchor']
            dpages, dline = locate(mid, a, ch, entry['procedure'], near_page=pages[0], window=src.get('doc_page_window', 2))
            if not dpages:
                errors.append(f'guidance {entry["target"]}|{entry["procedure"]}: document anchor not found near p.{pages[0]}: {a[:60]}')
                continue
            if line and dline and abs(dline - line) > 400:
                dl = [l for l in manuals[mid].find_lines(a) if abs(l - line) <= 400]
                dline = dl[0] if dl else dline
            d['source'] = {'manual': mid, 'pdf_page': dpages[0], 'hwp_line': dline, 'anchor': a, 'section': src['section'], 'file': src['file'], 'edition': src['edition'], 'review_state': src['review_state']}
            d['review_state'] = 'SEPT_2026_ORIGINAL_UNREVIEWED'
        guidance_out.append(entry)

    def resolve(manual_id, anchor, lo=None, hi=None, section_page=None, window=2, extra_lo_line=None, extra_hi_line=None):
        m = manuals[manual_id]
        if section_page:
            pages = m.find_pages(anchor, max(1, section_page - 1), min(m.max_page, section_page + window))
        else:
            pages = m.find_pages(anchor, lo or 1, hi)
        line = m.find_line(anchor, extra_lo_line or 0, extra_hi_line)
        return pages, line

    def resolve_simple(obj, anchor_key='anchor', manual_key='manual', code_for_chapter=None, label=''):
        mid = obj.get(manual_key, 'stay_manual_2026_09_18')
        ch = chapter_for(mid, code_for_chapter) if code_for_chapter else None
        lo = ch['pdf_start'] if ch and ch['pdf_start'] else 1
        hi = ch['pdf_end'] if ch and ch['pdf_end'] else None
        pages, line = resolve(mid, obj[anchor_key], lo, hi, extra_lo_line=(ch['hwp_start'] - 1) if ch and ch['hwp_start'] else 0, extra_hi_line=ch['hwp_end'] if ch else None)
        if not pages and code_for_chapter:
            pages, line = resolve(mid, obj[anchor_key])
        if not pages:
            errors.append(f'{label}: anchor not found: {obj[anchor_key][:70]}')
            return
        obj['pdf_page'] = pages[0]
        obj['hwp_line'] = line
        obj['file'] = SOURCES[mid]['pdf']
        obj['edition'] = SOURCES[mid]['edition']

    overrides = json.loads(json.dumps(rules['state_overrides']))
    for o in overrides:
        # generic anchors ("해당사항 없음") must sit on a page of the code's chapter that also carries the procedure label
        mid = o['manual']
        ch = chapter_for(mid, o['target'])
        m = manuals[mid]
        labels = PROCEDURE_SECTION_LABELS.get(o['procedure'], [])
        found = None
        if ch and ch['pdf_start']:
            for pg in range(ch['pdf_start'], (ch['pdf_end'] or m.max_page) + 1):
                t = m.page_text.get(pg, '')
                if norm(o['anchor']) in t and any(norm(l) in t for l in labels):
                    found = pg
                    break
            if not found:
                for pg in range(ch['pdf_start'], (ch['pdf_end'] or m.max_page) + 1):
                    if norm(o['anchor']) in m.page_text.get(pg, ''):
                        found = pg
                        break
        if not found:
            errors.append(f'state override {o["target"]}|{o["procedure"]}: anchor not found in chapter: {o["anchor"][:60]}')
            continue
        o['pdf_page'] = found
        o['hwp_line'] = m.find_line(o['anchor'], (ch['hwp_start'] - 1) if ch and ch['hwp_start'] else 0, ch['hwp_end'] if ch else None)
        o['file'] = SOURCES[mid]['pdf']
        o['edition'] = SOURCES[mid]['edition']

    overlays = json.loads(json.dumps(rules['overlays']))
    for ov in overlays:
        resolve_simple(ov, label=f'overlay {ov["id"]}')
    transitions = json.loads(json.dumps(rules['transitions']))
    for tr in transitions:
        resolve_simple(tr, code_for_chapter=tr['to'], label=f'transition {tr["id"]}')
        for ex in tr.get('exclusions', []):
            resolve_simple({**ex, 'manual': tr['manual']}, code_for_chapter=tr['to'], label=f'transition {tr["id"]} exclusion {ex["class"]}')
            pages, line = resolve(tr['manual'], ex['anchor'])
            ex['pdf_page'] = pages[0] if pages else None
            ex['hwp_line'] = line
            for e2 in ex.get('exceptions', []):
                pages2, line2 = resolve(tr['manual'], e2['anchor'])
                if not pages2:
                    errors.append(f'transition {tr["id"]} exception anchor not found: {e2["anchor"][:60]}')
                e2['pdf_page'] = pages2[0] if pages2 else None
                e2['hwp_line'] = line2
    programs = json.loads(json.dumps(rules['programs']))
    for p in programs:
        ch = chapters[p['manual']].get(p['chapter_key'])
        resolve_simple(p, label=f'program {p["id"]}')
        p['chapter'] = {'stay': ch, 'visa': chapters['visa_manual_2026_09_01'].get(p['chapter_key']) if p.get('visa_manual_chapter') else None}

    if errors:
        print('BUILD FAILED — anchors or chapters could not be resolved:', file=sys.stderr)
        for e in errors:
            print('  -', e, file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------ manifest records
    proc_ids = [p['id'] for p in rules['procedures']]
    guidance_index = collections.defaultdict(list)
    for g in guidance_out:
        guidance_index[(g['target'].split('~')[0], g['procedure'])].append(g)
        if g['target'].count('~'):
            guidance_index[(g['target'], g['procedure'])].append(g)
        for c in g.get('covers') or []:
            # the manual states the same rule for this code (e.g. 점수제 우수인재(F-2-7, F-2-7S)); the entry serves it directly
            guidance_index[(c, g['procedure'])].append(g)
    override_index = {(o['target'], o['procedure']): o for o in overrides}

    def section_page(manual, ch, procedure):
        """First page inside the chapter whose text carries the procedure's section label."""
        if not ch or not ch['pdf_start']:
            return None
        for label in PROCEDURE_SECTION_LABELS.get(procedure, []):
            ln = norm(label)
            for pg in range(ch['pdf_start'], (ch['pdf_end'] or manual.max_page) + 1):
                if ln in manual.page_text.get(pg, ''):
                    return pg
        return None

    def procedure_states(code, parent):
        states = {}
        stay_ch = chapter_for('stay_manual_2026_09_18', code)
        visa_ch = chapter_for('visa_manual_2026_09_01', code)
        for pid in proc_ids:
            entries = guidance_index.get((code, pid)) or []
            inherited = False
            if not entries and code != parent:
                entries = guidance_index.get((parent, pid)) or []
                inherited = bool(entries)
            ov = override_index.get((code, pid)) or override_index.get((parent, pid))
            rec = {'state': 'UNVERIFIED', 'document_guidance': 'UNVERIFIED', 'source': None, 'inherited_from_parent': False}
            if entries:
                best = sorted(entries, key=lambda e: ['SUPPORTED', 'CONDITIONAL', 'EXCEPTION_ONLY', 'GENERALLY_NOT_PERMITTED', 'NOT_APPLICABLE', 'LEGACY_ONLY', 'SOURCE_ONLY', 'UNVERIFIED'].index(e['state']))[0]
                rec['state'] = best['state']
                comps = [e['completeness'] for e in entries]
                rec['document_guidance'] = 'FULLY_STRUCTURED' if 'FULLY_STRUCTURED' in comps else ('PARTIALLY_STRUCTURED' if 'PARTIALLY_STRUCTURED' in comps else comps[0])
                rec['source'] = {'manual': best['source']['manual'], 'pdf_page': best['source']['pdf_page'], 'section': best['source']['section']}
                rec['inherited_from_parent'] = inherited
                rec['scenarios'] = len(entries)
            elif ov:
                rec['state'] = ov['state']
                rec['document_guidance'] = 'NOT_APPLICABLE' if ov['state'] in ('NOT_APPLICABLE',) else 'SOURCE_ONLY'
                rec['source'] = {'manual': ov['manual'], 'pdf_page': ov['pdf_page'], 'section': ov['anchor'][:60]}
                rec['inherited_from_parent'] = ov['target'] != code
            elif pid in VISA_PROCEDURES:
                if visa_ch and visa_ch['pdf_start'] and (code_in_manual(code, 'visa') or code == parent):
                    rec['state'] = 'SOURCE_ONLY'
                    rec['document_guidance'] = 'SOURCE_ONLY'
                    rec['source'] = {'manual': 'visa_manual_2026_09_01', 'pdf_page': visa_ch['pdf_start'], 'section': visa_ch['title_ko']}
                else:
                    rec['state'] = 'NOT_APPLICABLE' if parent in ('F-5',) or not visa_ch else 'UNVERIFIED'
            else:
                pg = section_page(stay, stay_ch, pid)
                if pg:
                    rec['state'] = 'SOURCE_ONLY'
                    rec['document_guidance'] = 'SOURCE_ONLY'
                    rec['source'] = {'manual': 'stay_manual_2026_09_18', 'pdf_page': pg, 'section': PROCEDURE_SECTION_LABELS[pid][0]}
                elif stay_ch and stay_ch['pdf_start'] and pid in ('card_reissue', 'residence_report', 'workplace_report', 'program_condition_change', 'part_time_work', 'registration_info_report'):
                    rec['state'] = 'UNVERIFIED'
                elif not stay_ch:
                    rec['state'] = 'NOT_APPLICABLE'
            states[pid] = rec
        return states

    def coverage_state(code, parent, in_stay, in_visa, legacy_rule, states):
        if legacy_rule and legacy_rule.get('new_application_allowed') is False and not legacy_rule.get('existing_holder_only'):
            return 'LEGACY_ONLY'
        if not in_stay and not in_visa:
            return 'UNVERIFIED'
        own = [s for (c, p), lst in guidance_index.items() if c == code for s in lst]
        if any(e['state'] in ('SUPPORTED',) and e['completeness'] == 'FULLY_STRUCTURED' for e in own):
            return 'SUPPORTED'
        if own or any(not v['inherited_from_parent'] and v['state'] in ('SUPPORTED', 'CONDITIONAL', 'EXCEPTION_ONLY', 'GENERALLY_NOT_PERMITTED', 'NOT_APPLICABLE') and v['source'] for v in states.values()):
            return 'PARTIAL'
        return 'SOURCE_ONLY'

    subcode_names = rules.get('subcode_names', {})

    def display_names(code, parent):
        """(ko, en, quality): authored label > manual table cell > legacy name > mention context."""
        if code in subcode_names:
            return subcode_names[code]['ko'], subcode_names[code]['en'], 'authored'
        cell = stay_cells.get(code) or visa_cells.get(code)
        if cell and not cell[1].startswith('-'):
            return cell[1], None, 'table'
        if code in legacy_subs and legacy_subs[code][1].get('name'):
            return legacy_subs[code][1]['name'], None, 'legacy'
        if code in stay_mentions:
            return stay_mentions[code].most_common(1)[0][0], None, 'mention'
        if code in visa_mentions:
            return visa_mentions[code].most_common(1)[0][0], None, 'mention'
        return code, None, 'none'

    records = []
    ordered_parents = [c for c, *_ in STAY_CHAPTERS if c and c not in ('preamble-notes', 'preamble-common') and _[0] and STAY_CHAPTERS] 
    parent_codes = [k for k, code, *_ in STAY_CHAPTERS if code] + ['F-4', 'H-2']
    for parent in parent_codes:
        stay_ch = chapters['stay_manual_2026_09_18'].get(parent) or (chapters['stay_manual_2026_09_18']['DONGPO'] if parent in ('F-4', 'H-2') else None)
        visa_ch = chapters['visa_manual_2026_09_01'].get(parent)
        in_stay, in_visa = code_in_manual(parent, 'stay'), code_in_manual(parent, 'visa')
        states = procedure_states(parent, parent)
        lr = LEGACY_RULES.get(parent)
        lg = legacy_by_code.get(parent)
        rec = {
            'kind': 'status', 'code': parent, 'parent': None, 'substatus': None,
            'name_ko': (lg or {}).get('name') or next((t for k, c, t, *_ in STAY_CHAPTERS if c == parent), parent), 'name_en': (names.get(parent) or {}).get('en'),
            'description_ko': None, 'description_en': None,
            'source': {'stay': {'manual': 'stay_manual_2026_09_18', 'edition': '2026.9', 'chapter': stay_ch['key'] if stay_ch else None, 'chapter_title_ko': stay_ch['title_ko'] if stay_ch else None, 'pdf_page_start': stay_ch['pdf_start'] if stay_ch else None, 'pdf_page_end': stay_ch['pdf_end'] if stay_ch else None, 'hwp_line_start': stay_ch['hwp_start'] if stay_ch else None, 'page_detection': stay_ch['detection'] if stay_ch else 'missing'} if in_stay else None,
                       'visa': {'manual': 'visa_manual_2026_09_01', 'edition': '2026.9', 'chapter': visa_ch['key'] if visa_ch else None, 'chapter_title_ko': visa_ch['title_ko'] if visa_ch else None, 'pdf_page_start': visa_ch['pdf_start'] if visa_ch else None, 'pdf_page_end': visa_ch['pdf_end'] if visa_ch else None, 'hwp_line_start': visa_ch['hwp_start'] if visa_ch else None, 'page_detection': visa_ch['detection'] if visa_ch else 'missing'} if in_visa else None},
            'temporal': {'effective_from': None, 'effective_to': (lr or {}).get('effective_to'), 'new_application_allowed': (lr or {}).get('new_application_allowed', True), 'existing_holder_only': (lr or {}).get('existing_holder_only', False), 'legacy_holder_rule': (lr or {}).get('note_ko'), 'supersedes': None, 'superseded_by': (lr or {}).get('superseded_by'), 'pilot_program': False, 'sunset_rule': None, 'source_edition': '2026.9', 'legacy_source': {'pdf_page': lr.get('pdf_page'), 'hwp_line': lr.get('hwp_line'), 'anchor': lr.get('anchor')} if lr else None},
            'lifecycle': 'legacy_holders_only' if (lr and lr.get('existing_holder_only')) else 'active',
            'procedures': states,
            'clarification_dimensions': [d['id'] for d in rules['families'].get(parent, {}).get('dimensions', [])],
            'has_resolver': parent in rules['families'],
            'structured_guidance': any(v['state'] in ('SUPPORTED', 'CONDITIONAL', 'EXCEPTION_ONLY') and v['source'] and v['document_guidance'] not in ('SOURCE_ONLY', 'UNVERIFIED') for v in states.values()),
            'document_guidance': 'FULLY_STRUCTURED' if any(v['document_guidance'] == 'FULLY_STRUCTURED' for v in states.values()) else ('PARTIALLY_STRUCTURED' if any(v['document_guidance'] == 'PARTIALLY_STRUCTURED' for v in states.values()) else 'SOURCE_ONLY'),
            'source_verification': 'SEPT_2026_ORIGINAL_UNREVIEWED' if (in_stay or in_visa) else 'NOT_IN_SEPT_2026_MANUALS',
            'coverage_state': None,
            'programs': [p['id'] for p in programs if parent in p['codes']],
            'related_programs': [p['id'] for p in programs if parent in (p.get('applies_to_parents') or [])],
            'legacy_record': {'present': parent in legacy_by_code, 'source_edition': (((lg or {}).get('sourceManualStatus') or {}).get('stayManualVersion')) if lg else None},
        }
        rec['coverage_state'] = coverage_state(parent, parent, in_stay, in_visa, lr, states)
        if rec['lifecycle'] == 'legacy_holders_only' and rec['coverage_state'] in ('SOURCE_ONLY', 'PARTIAL', 'SUPPORTED'):
            rec['coverage_state_note'] = 'existing holders only'
        records.append(rec)
    parent_records = {r['code']: r for r in records}
    for code in sorted(universe, key=lambda c: (parent_of(c), len(c), c)):
        parent = parent_of(code)
        if parent not in parent_codes:
            continue
        in_stay, in_visa = code_in_manual(code, 'stay'), code_in_manual(code, 'visa')
        stay_ch = chapter_for('stay_manual_2026_09_18', code)
        visa_ch = chapter_for('visa_manual_2026_09_01', code)
        states = procedure_states(code, parent)
        lr = LEGACY_RULES.get(code)
        ko, en, name_quality = display_names(code, parent)
        stay_pages = [p['page'] for p in stay.pages if code in p.get('subcodes_detected', []) or code in p.get('status_codes_detected', [])][:6]
        visa_pages = [p['page'] for p in visa.pages if code in p.get('subcodes_detected', []) or code in p.get('status_codes_detected', [])][:6]
        if not stay_pages and in_stay:
            stay_pages = stay.find_pages(code)[:6]
        if not visa_pages and in_visa:
            visa_pages = visa.find_pages(code)[:6]
        cell = stay_cells.get(code) or visa_cells.get(code)
        rec = {
            'kind': 'substatus', 'code': code, 'parent': parent, 'substatus': code.split('-', 2)[2],
            'name_ko': ko, 'name_en': en, 'name_en_state': 'AVAILABLE' if en else 'NOT_AVAILABLE', 'name_quality': name_quality,
            'description_ko': None, 'description_en': None,
            'source': {'stay': {'manual': 'stay_manual_2026_09_18', 'edition': '2026.9', 'chapter': stay_ch['key'] if stay_ch else None, 'pdf_pages': stay_pages, 'table_cell_line': stay_cells[code][0] if code in stay_cells else None} if in_stay else None,
                       'visa': {'manual': 'visa_manual_2026_09_01', 'edition': '2026.9', 'chapter': visa_ch['key'] if visa_ch else None, 'pdf_pages': visa_pages, 'table_cell_line': visa_cells[code][0] if code in visa_cells else None} if in_visa else None},
            'taxonomy_evidence': 'table' if cell else ('mention' if (code in stay_mentions or code in visa_mentions or in_stay or in_visa) else 'legacy_only'),
            'temporal': {'effective_from': None, 'effective_to': (lr or {}).get('effective_to'), 'new_application_allowed': (lr or {}).get('new_application_allowed', True), 'existing_holder_only': (lr or {}).get('existing_holder_only', False), 'legacy_holder_rule': (lr or {}).get('note_ko'), 'supersedes': None, 'superseded_by': (lr or {}).get('superseded_by'), 'legacy_alias': (lr or {}).get('legacy_alias'), 'pilot_program': any(p.get('pilot_program') and code in p['codes'] for p in programs), 'sunset_rule': None, 'source_edition': '2026.9', 'legacy_source': {'pdf_page': lr.get('pdf_page'), 'hwp_line': lr.get('hwp_line'), 'anchor': lr.get('anchor')} if lr else None},
            'lifecycle': 'abolished' if (lr and lr.get('new_application_allowed') is False and not lr.get('existing_holder_only')) else ('legacy_holders_only' if (lr and lr.get('existing_holder_only')) else ('unverified' if not (in_stay or in_visa) else 'active')),
            'procedures': states,
            'clarification_dimensions': [],
            'has_resolver': parent in rules['families'],
            'structured_guidance': any(v['state'] in ('SUPPORTED', 'CONDITIONAL', 'EXCEPTION_ONLY') and not v['inherited_from_parent'] and v['document_guidance'] not in ('SOURCE_ONLY', 'UNVERIFIED') for v in states.values()),
            'document_guidance': 'FULLY_STRUCTURED' if any(v['document_guidance'] == 'FULLY_STRUCTURED' and not v['inherited_from_parent'] for v in states.values()) else ('PARTIALLY_STRUCTURED' if any(v['document_guidance'] == 'PARTIALLY_STRUCTURED' and not v['inherited_from_parent'] for v in states.values()) else ('INHERITS_PARENT' if any(v['document_guidance'] in ('FULLY_STRUCTURED', 'PARTIALLY_STRUCTURED') for v in states.values()) else 'SOURCE_ONLY')),
            'source_verification': 'SEPT_2026_ORIGINAL_UNREVIEWED' if (in_stay or in_visa) else 'NOT_IN_SEPT_2026_MANUALS',
            'coverage_state': None,
            'programs': [p['id'] for p in programs if code in p['codes']],
            'related_programs': [p['id'] for p in programs if code in (p.get('applies_to_parents') or [])],
            'legacy_record': {'present': code in legacy_subs, 'legacy_name': legacy_subs[code][1].get('name') if code in legacy_subs else None},
        }
        rec['coverage_state'] = coverage_state(code, parent, in_stay, in_visa, lr, states)
        if rec['coverage_state'] == 'SOURCE_ONLY' and rec['programs']:
            rec['coverage_state'] = 'PARTIAL'
        records.append(rec)
        # A parent whose own procedure is only SOURCE_ONLY/UNVERIFIED but whose subtypes carry
        # structured guidance is CONDITIONAL at parent level: the resolver must pick the subtype first.
        pr = parent_records.get(parent)
        if pr and (in_stay or in_visa):
            for pid, st in rec['procedures'].items():
                if st['inherited_from_parent']:
                    continue
                if st['state'] in ('SUPPORTED', 'CONDITIONAL', 'EXCEPTION_ONLY') and pr['procedures'][pid]['state'] in ('SOURCE_ONLY', 'UNVERIFIED'):
                    pr['procedures'][pid] = {'state': 'CONDITIONAL', 'document_guidance': 'REQUIRES_CLARIFICATION', 'source': st['source'], 'inherited_from_parent': False, 'resolved_by_subtype': True}
                    if pr['coverage_state'] == 'SOURCE_ONLY':
                        pr['coverage_state'] = 'PARTIAL'
                    if rec['coverage_state'] == 'SUPPORTED' and pr['coverage_state'] != 'SUPPORTED':
                        pr['coverage_state'] = 'SUPPORTED'
    for pr in [r for r in records if r['kind'] == 'status']:
        if pr['coverage_state'] == 'SOURCE_ONLY' and pr['programs']:
            pr['coverage_state'] = 'PARTIAL'
    # scenario records (guidance targets without an explicit 세부약호)
    for g in guidance_out:
        if '~' in g['target']:
            parent, scen = g['target'].split('~')
            if any(r['kind'] == 'scenario' and r['code'] == g['target'] for r in records):
                continue
            records.append({'kind': 'scenario', 'code': g['target'], 'parent': parent, 'substatus': None, 'scenario': scen, 'name_ko': g['source']['section'].split(' — ')[0], 'name_en': None, 'name_en_state': 'NOT_AVAILABLE',
                            'source': {'stay': {'manual': g['source']['manual'], 'edition': g['source']['edition'], 'chapter': g['source']['chapter'], 'pdf_pages': [g['source']['pdf_page']]}, 'visa': None},
                            'taxonomy_evidence': 'section', 'temporal': {'source_edition': '2026.9', 'new_application_allowed': True, 'existing_holder_only': False}, 'lifecycle': 'active',
                            'procedures': {g['procedure']: {'state': g['state'], 'document_guidance': g['completeness'], 'source': {'manual': g['source']['manual'], 'pdf_page': g['source']['pdf_page'], 'section': g['source']['section']}, 'inherited_from_parent': False}},
                            'clarification_dimensions': [], 'has_resolver': True, 'structured_guidance': g['completeness'] == 'FULLY_STRUCTURED', 'document_guidance': g['completeness'], 'source_verification': 'SEPT_2026_ORIGINAL_UNREVIEWED',
                            'coverage_state': 'SUPPORTED' if g['completeness'] == 'FULLY_STRUCTURED' and g['state'] == 'SUPPORTED' else 'PARTIAL', 'programs': [], 'legacy_record': {'present': False}})
    for p in programs:
        records.append({'kind': 'program', 'code': 'PROGRAM:' + p['id'], 'parent': None, 'substatus': None, 'name_ko': p['name_ko'], 'name_en': p['name_en'], 'description_ko': p['summary_ko'], 'description_en': p['summary_en'],
                        'source': {'stay': {'manual': p['manual'], 'edition': '2026.9', 'chapter': p['chapter_key'], 'pdf_pages': [p['pdf_page']], 'pdf_page_start': (p['chapter']['stay'] or {}).get('pdf_start'), 'pdf_page_end': (p['chapter']['stay'] or {}).get('pdf_end')}, 'visa': {'manual': 'visa_manual_2026_09_01', 'edition': '2026.9', 'chapter': p['chapter_key'], 'pdf_page_start': (p['chapter']['visa'] or {}).get('pdf_start'), 'pdf_page_end': (p['chapter']['visa'] or {}).get('pdf_end')} if p['chapter']['visa'] else None},
                        'codes': p['codes'], 'temporal': {'effective_from': p.get('effective_from'), 'pilot_program': bool(p.get('pilot_program')), 'source_edition': '2026.9', 'new_application_allowed': True, 'existing_holder_only': False}, 'lifecycle': 'active',
                        'procedures': {}, 'clarification_dimensions': p['dimensions_ko'], 'has_resolver': False, 'structured_guidance': True, 'document_guidance': 'SOURCE_ONLY', 'source_verification': 'SEPT_2026_ORIGINAL_UNREVIEWED',
                        'coverage_state': 'PARTIAL', 'programs': [p['id']], 'legacy_record': {'present': p['id'] in ('regional', 'k-star', 'youth')}})

    # -------------------------------------------------------- conflicts
    conflicts = []
    for r in legacy:
        sms = r.get('sourceManualStatus') or {}
        if r['code'] in parent_codes and sms.get('stayManualVersion') and sms.get('stayManualVersion') != '2026.9':
            conflicts.append({'status': r['code'], 'procedure': 'all', 'kind': 'edition_lag', 'structured_value': f"{sms.get('stayManualVersion')} / {sms.get('sourceDate')}", 'manual_value': '2026.9 (stay 2026-09-18, visa 2026-09-01)', 'impact': 'legacy card may disagree with the September text', 'resolution': 'new guidance layer cites 2026.9 pages; legacy card labelled with its own edition'})
    for code, (parent, s) in sorted(legacy_subs.items()):
        if not code_in_manual(code, 'stay') and not code_in_manual(code, 'visa'):
            conflicts.append({'status': code, 'procedure': 'taxonomy', 'kind': 'code_not_in_manuals', 'structured_value': s.get('name'), 'manual_value': 'not found in either September manual', 'impact': 'cannot be resolved from source', 'resolution': 'manifest marks UNVERIFIED; resolver never targets it'})
    for code in sorted(universe):
        if code not in legacy_subs and (code_in_manual(code, 'stay') or code_in_manual(code, 'visa')) and (code in stay_cells or code in visa_cells or code in guidance_targets or code in family_targets):
            conflicts.append({'status': code, 'procedure': 'taxonomy', 'kind': 'code_missing_from_legacy', 'structured_value': 'absent from visa_data.json', 'manual_value': 'present in September manual', 'impact': 'legacy search cannot land on it', 'resolution': 'manifest + resolver carry it (SOURCE_ONLY or SUPPORTED)'})
    e7 = legacy_by_code.get('E-7') or {}
    e7_text = json.dumps(e7, ensure_ascii=False)
    if '2,500만원' in e7_text or '2500만원' in e7_text:
        conflicts.append({'status': 'E-7-4', 'procedure': 'status_change', 'kind': 'value_changed', 'structured_value': '소득요건 2,500만원 (2026.6 text)', 'manual_value': '2,589만원 (2026.9)', 'impact': 'legacy summary understates the income threshold', 'resolution': 'not edited (protected file); flagged for manual review'})
    if 'F-2-6' in legacy_subs:
        conflicts.append({'status': 'F-2-6', 'procedure': 'taxonomy', 'kind': 'abolished_code', 'structured_value': legacy_subs['F-2-6'][1].get('name'), 'manual_value': '2019-10-01 폐지, F-2-99로 직권 정정', 'impact': 'legacy lists an abolished code without a legacy marker', 'resolution': 'manifest marks LEGACY_ONLY / superseded_by F-2-99'})

    # -------------------------------------------------------- summary
    def count(kind=None):
        rs = [r for r in records if kind is None or r['kind'] == kind]
        return collections.Counter(r['coverage_state'] for r in rs)
    summary = {
        'total_manual_chapters': {'stay': len(STAY_CHAPTERS), 'visa': len(VISA_CHAPTERS)},
        'numbered_chapters': {'stay': sum(1 for c in STAY_CHAPTERS if c[4] != 'preamble'), 'visa': sum(1 for c in VISA_CHAPTERS if c[4] != 'preamble')},
        'chapters_detected': {mid: sum(1 for c in ch.values() if c['pdf_start']) for mid, ch in chapters.items()},
        'total_status_records': sum(1 for r in records if r['kind'] == 'status'),
        'total_substatus_records': sum(1 for r in records if r['kind'] == 'substatus'),
        'total_scenario_records': sum(1 for r in records if r['kind'] == 'scenario'),
        'total_special_program_records': sum(1 for r in records if r['kind'] == 'program'),
        'coverage_states_all': dict(count()), 'coverage_states_status': dict(count('status')), 'coverage_states_substatus': dict(count('substatus')),
        'guidance_entries': len(guidance_out), 'document_items': sum(len(g['documents']) for g in guidance_out),
        'document_completeness': dict(collections.Counter(g['completeness'] for g in guidance_out)),
        'procedure_states': dict(collections.Counter(v['state'] for r in records if r['kind'] in ('status', 'substatus') for v in r['procedures'].values())),
        'conflicts': len(conflicts),
        'errors': errors,
    }
    manifest = {'schema_version': 1, 'generated_by': 'scripts/build_status_coverage_manifest.py', 'generated_from': {'rules': 'data/guidance-rules-202609.json', 'sources': SOURCES}, 'coverage_states': rules['enums']['coverage_states'], 'procedure_states': rules['enums']['procedure_states'],
                'chapters': {mid: list(ch.values()) for mid, ch in chapters.items()}, 'records': records, 'conflicts': conflicts, 'summary': summary}
    def slim_guidance(entry):
        e = json.loads(json.dumps(entry))
        src = e['source']
        e['source'] = {'manual': src['manual'], 'section': src['section'], 'pdf_page': src['pdf_page'], 'hwp_line': src['hwp_line'], 'file': src['file'], 'edition': src['edition'], 'date': src['date'], 'chapter': src['chapter'], 'review_state': src['review_state']}
        for d in e['documents']:
            d.pop('anchor', None)
            ds = d.get('source') or {}
            d['source'] = {'pdf_page': ds.get('pdf_page'), 'hwp_line': ds.get('hwp_line')}
        for k in ('extra_sources',):
            e.pop(k, None)
        return e

    bundle = {'schema_version': 1, 'generated_by': 'scripts/build_status_coverage_manifest.py', 'sources': SOURCES, 'procedures': rules['procedures'], 'enums': rules['enums'],
              'guidance': [slim_guidance(g) for g in guidance_out], 'state_overrides': overrides, 'overlays': overlays, 'transitions': transitions, 'families': rules['families'], 'current_status_question': rules['current_status_question'], 'aliases': rules['aliases'], 'programs': programs, 'officer_note': rules['officer_note'],
              'codes': {r['code']: {'kind': r['kind'], 'parent': r['parent'], 'name_ko': r['name_ko'], 'name_en': r.get('name_en'), 'coverage_state': r['coverage_state'], 'lifecycle': r['lifecycle'],
                                    'temporal': {k: v for k, v in r['temporal'].items() if v not in (None, False) and k not in ('source_edition',)} or {}, 'programs': r['programs'], 'related_programs': r.get('related_programs', []),
                                    'procedures': {k: {'s': v['state'], 'd': v['document_guidance'], 'p': (v['source'] or {}).get('pdf_page'), 'm': 'visa' if ((v['source'] or {}).get('manual') or '').startswith('visa') else 'stay', 'i': v.get('inherited_from_parent', False), 't': v.get('resolved_by_subtype', False)} for k, v in r['procedures'].items() if v['state'] != 'UNVERIFIED'},
                                    'has_resolver': r['has_resolver'], 'chapter': (r['source'].get('stay') or r['source'].get('visa') or {}).get('chapter') if r.get('source') else None} for r in records},
              'chapters': {mid: {k: {'key': v['key'], 'code': v['code'], 'title_ko': v['title_ko'], 'title_en': v['title_en'], 'pdf_start': v['pdf_start'], 'pdf_end': v['pdf_end']} for k, v in ch.items()} for mid, ch in chapters.items()}}

    if errors:
        print('BUILD FAILED — anchors or chapters could not be resolved:', file=sys.stderr)
        for e in errors:
            print('  -', e, file=sys.stderr)
        sys.exit(1)

    def dump(obj):
        return json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False) + '\n'
    report_md = render_report(summary, records, chapters, conflicts)
    outputs = {MANIFEST_OUT: dump(manifest), BUNDLE_OUT: dump(bundle), REPORT_JSON: dump({'summary': summary, 'records': [{'code': r['code'], 'kind': r['kind'], 'coverage_state': r['coverage_state'], 'lifecycle': r['lifecycle']} for r in records]}), REPORT_MD: report_md}
    if args.check:
        stale = []
        for path, content in outputs.items():
            try:
                with open(path, encoding='utf-8') as fh:
                    if fh.read() != content:
                        stale.append(path)
            except FileNotFoundError:
                stale.append(path)
        if stale:
            print('STALE outputs (re-run python3 scripts/build_status_coverage_manifest.py):', *stale, sep='\n  ', file=sys.stderr)
            sys.exit(1)
        print('status coverage manifest is current:', json.dumps({k: v for k, v in summary.items() if k != 'errors'}, ensure_ascii=False))
        return
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    for path, content in outputs.items():
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(content)
    print(json.dumps({k: v for k, v in summary.items() if k != 'errors'}, ensure_ascii=False, indent=1))


def render_report(summary, records, chapters, conflicts):
    lines = ['# Status coverage report — September 2026 manuals', '',
             'Generated by `scripts/build_status_coverage_manifest.py` from `data/guidance-rules-202609.json` and the two September 2026 manual corpora. Every figure below is computed; nothing is hand-counted.', '',
             '| Metric | Value |', '| --- | --- |',
             f"| TOTAL MANUAL CHAPTERS | stay {summary['total_manual_chapters']['stay']} (detected {summary['chapters_detected']['stay_manual_2026_09_18']}) · visa {summary['total_manual_chapters']['visa']} (detected {summary['chapters_detected']['visa_manual_2026_09_01']}) |",
             f"| TOTAL STATUS RECORDS | {summary['total_status_records']} |", f"| TOTAL SUBSTATUS RECORDS | {summary['total_substatus_records']} |", f"| TOTAL SCENARIO RECORDS | {summary['total_scenario_records']} |", f"| TOTAL SPECIAL PROGRAM RECORDS | {summary['total_special_program_records']} |", '']
    lines += ['## Coverage states (all records)', '', '| State | Count |', '| --- | --- |']
    for st in ['SUPPORTED', 'PARTIAL', 'SOURCE_ONLY', 'UNVERIFIED', 'NOT_APPLICABLE', 'LEGACY_ONLY']:
        lines.append(f"| {st} | {summary['coverage_states_all'].get(st, 0)} |")
    lines += ['', '## Coverage states by kind', '', '| Kind | ' + ' | '.join(['SUPPORTED', 'PARTIAL', 'SOURCE_ONLY', 'UNVERIFIED', 'NOT_APPLICABLE', 'LEGACY_ONLY']) + ' |', '| --- |' + ' --- |' * 6]
    for kind, key in (('status', 'coverage_states_status'), ('substatus', 'coverage_states_substatus')):
        lines.append(f'| {kind} | ' + ' | '.join(str(summary[key].get(s, 0)) for s in ['SUPPORTED', 'PARTIAL', 'SOURCE_ONLY', 'UNVERIFIED', 'NOT_APPLICABLE', 'LEGACY_ONLY']) + ' |')
    lines += ['', f"Guidance entries: {summary['guidance_entries']} · document items: {summary['document_items']} · completeness: {json.dumps(summary['document_completeness'], ensure_ascii=False)}", '',
              f"Procedure states across status/substatus records: {json.dumps(summary['procedure_states'], ensure_ascii=False)}", '', '## Chapters', '']
    for mid, ch in chapters.items():
        lines += [f'### {mid}', '', '| # | Chapter | Code | PDF pages | HWP line | Detection |', '| --- | --- | --- | --- | --- | --- |']
        for i, c in enumerate(ch.values(), 1):
            lines.append(f"| {i} | {c['title_ko']} | {c['code'] or '—'} | {c['pdf_start']}–{c['pdf_end']} | {c['hwp_start']} | {c['detection']} |")
        lines.append('')
    lines += ['## Status records', '', '| Code | Name | Coverage | Lifecycle | Resolver | Document guidance | Programs |', '| --- | --- | --- | --- | --- | --- | --- |']
    for r in records:
        if r['kind'] == 'status':
            lines.append(f"| {r['code']} | {r['name_ko']} | {r['coverage_state']} | {r['lifecycle']} | {'yes' if r['has_resolver'] else 'no'} | {r['document_guidance']} | {', '.join(r['programs']) or '—'} |")
    lines += ['', '## Substatus records', '', '| Code | Name (KO) | EN | Coverage | Lifecycle | Evidence | Document guidance |', '| --- | --- | --- | --- | --- | --- | --- |']
    for r in records:
        if r['kind'] == 'substatus':
            lines.append(f"| {r['code']} | {r['name_ko'] or '—'} | {r.get('name_en') or '—'} | {r['coverage_state']} | {r['lifecycle']} | {r['taxonomy_evidence']} | {r['document_guidance']} |")
    lines += ['', '## Scenario and program records', '', '| Code | Name | Coverage |', '| --- | --- | --- |']
    for r in records:
        if r['kind'] in ('scenario', 'program'):
            lines.append(f"| {r['code']} | {r['name_ko']} | {r['coverage_state']} |")
    lines += ['', f'## Conflicts with legacy structured data ({len(conflicts)})', '', '| Status | Procedure | Kind | Structured | Manual | Resolution |', '| --- | --- | --- | --- | --- | --- |']
    for c in conflicts:
        lines.append(f"| {c['status']} | {c['procedure']} | {c['kind']} | {c['structured_value']} | {c['manual_value']} | {c['resolution']} |")
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    main()
