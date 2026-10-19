#!/usr/bin/env python3
"""Build the readable manual reader (manual.html) from the 2026.9 Markdown sources.

Sources (digest-pinned in data/manual-reader/catalog.json):
  docs/source-manuals/2026-09/markdown/visa_manual_260901.md  사증발급 안내매뉴얼 2026.9 (2026-09-01)
  docs/source-manuals/2026-09/markdown/stay_manual_260918.md  외국인체류 안내매뉴얼 2026.9 (2026-09-18)

What this does: split each manual into status chapters, turn the HWP layout tables
(label cell | content cell) into labelled sections, classify each <br>-line by its
original marker (1. 가. ① ❍ - ※ *) for indentation, and mark ①②③ lines that follow
a 제출서류/첨부서류 heading as a document checklist.

What this never does: rewrite, summarise, reorder or drop manual prose. The only
removed text is page-break noise (repeated row labels, "목차" back-links, a chapter's
own title line) and decorative cover/logo images. `--check` rebuilds in memory and
fails if (a) committed outputs differ, (b) any chapter loses more characters than
the duplicate labels account for, or (c) the Markdown no longer matches the
independently extracted PDF text of the same edition.

Requires: pip install markdown-it-py beautifulsoup4 html5lib Pillow
"""
import argparse, glob, hashlib, html as htmlmod, io, json, re, sys
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / 'docs/source-manuals/2026-09/markdown'
OUT_DIR = ROOT / 'data/manual-reader'
IMG_OUT = ROOT / 'assets/manual-reader/img'
SOURCES = {
    'v': {'id': 'visa_manual_2026_09_01_md', 'file': 'visa_manual_260901.md', 'images': 'images/260901',
          'title': '사증발급 안내매뉴얼', 'title_en': 'Visa Issuance Guide Manual', 'date': '2026-09-01', 'version': '2026.9',
          'pdf': 'docs/source-manuals/2026-09/visa_manual_260901.pdf', 'pdf_text': 'docs/source-manuals/2026-09/extracted/visa_manual_2026_09_01_pdf.txt'},
    's': {'id': 'stay_manual_2026_09_18_md', 'file': 'stay_manual_260918.md', 'images': 'images/260918',
          'title': '외국인체류 안내매뉴얼', 'title_en': 'Foreigner Stay/Residence Guide Manual', 'date': '2026-09-18', 'version': '2026.9',
          'pdf': 'docs/source-manuals/2026-09/stay_manual_260918.pdf', 'pdf_text': 'docs/source-manuals/2026-09/extracted/stay_manual_2026_09_18_pdf.txt'},
}
OFFICIAL_URL = 'https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&BBS_GB_CD=BS10&NTCCTT_SEQ=1062&page=1'
# Chapter starts (1-based line numbers in each Markdown file). A chapter runs to the next start.
CHAPTERS_V = [
    (36,   'common', None),
    (95,   'A-1', None), (109, 'A-2', None), (123, 'A-3', None), (136, 'B-1', None),
    (315,  'B-2', None), (389, 'C-1', None), (409, 'C-3', None), (455, 'C-4', None),
    (502,  'D-1', None), (518, 'D-2', None), (623, 'D-3', None), (639, 'D-4', None),
    (721,  'D-5', None), (739, 'D-6', None), (755, 'D-7', None), (807, 'D-8', None),
    (864,  'D-9', None), (899, 'D-10', None), (985, 'E-1', None), (1020, 'E-2', None),
    (1063, 'E-3', None), (1114, 'E-4', None), (1136, 'E-5', None), (1155, 'E-6', None),
    (1181, 'E-7', None), (4594, 'E-8', None), (4658, 'E-9', None), (4763, 'E-10', None),
    (4788, 'F-1', None), (4847, 'F-2', None), (4870, 'F-3', None), (4897, 'F-5', None),
    (4969, 'F-6', None), (5197, 'G-1', None), (5240, 'H-1', None),
    (5295, 'D-3-rule', None),
    (5963, 'dongpo', None), (7808, 'toptier', None), (9209, 'kstar', None),
]
CHAPTERS_S = [
    (42,   'common', None),
    (297,  'A-1', None), (315, 'A-2', None), (337, 'A-3', None), (356, 'B-1', None),
    (364,  'B-2', None), (372, 'C-1', None), (379, 'C-3', None), (400, 'C-4', None),
    (409,  'D-1', None), (435, 'D-2', None), (692, 'D-3', None), (1227, 'D-4', None),
    (1428, 'D-5', None), (1448, 'D-6', None), (1468, 'D-7', None), (1512, 'D-8', None),
    (1609, 'D-9', None), (1814, 'D-10', None), (2018, 'E-1', None), (2047, 'E-2', None),
    (2097, 'E-3', None), (2138, 'E-4', None), (2161, 'E-5', None), (2184, 'E-6', None),
    (2215, 'E-7', None), (5537, 'E-8', None), (5547, 'E-9', None), (5627, 'E-10', None),
    (5647, 'F-1', None), (5695, 'F-2', None), (5871, 'F-3', None), (5904, 'F-5', None),
    (6178, 'F-6', None), (6432, 'G-1', None), (6455, 'H-1', None),
    (6492, 'dongpo', None), (7974, 'regional', None), (10077, 'youth', None),
    (10505, 'toptier', None), (11588, 'metro', None), (13573, 'kstar', None),
]


md = MarkdownIt('commonmark', {'html': True}).enable('table')

# images: tiny bullet glyphs are dropped; cover/logo images dropped; the rest embedded by key
DROP_IMG = {
    'v': {'image_001', 'image_002', 'image_008', 'image_010'},
    's': {'image_001', 'image_002', 'image_003', 'image_004', 'image_010', 'image_013', 'image_014', 'image_015', 'image_016'},
}
USED_IMG = set()
BULLET_IMG = {'v': {'image_002', 'image_008'}, 's': {'image_003', 'image_010'}}

CIRC = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'

LINE_RULES = [
    (re.compile(r'^\d{1,2}\s?\.\s*\S'), 'n1'),
    (re.compile(r'^\d{1,2}-\d{1,2}\.\s*\S'), 'n1'),
    (re.compile(r'^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]\s?\.?'), 'n0'),
    (re.compile(r'^[가-하]\s?\.\s*\S'), 'n2'),
    (re.compile(r'^(\d{1,2}|[가-하])\)\s*'), 'n3'),
    (re.compile(r'^\((\d{1,2}|[가-하])\)\s*'), 'n3'),
    (re.compile(r'^[' + CIRC + r']'), 'c2'),
    (re.compile(r'^[ⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ]\)?'), 'n4'),
    (re.compile(r'^[❍○◦◯ㅇ●•▪￭■◎]\s*'), 'b2'),
    (re.compile(r'^[-–∙·]\s*'), 'd3'),
    (re.compile(r'^[‣▸►▶☞→⇒⇨➜]\s*'), 'a3'),
    (re.compile(r'^※'), 'nt'),
    (re.compile(r'^\*{1,3}'), 'fn'),
    (re.compile(r'^[□▣◈]'), 'bx'),
    (re.compile(r'^[【\[<＜〈].{1,40}[】\]>＞〉]$'), 'sb'),
]
DOC_TRIGGER = re.compile(r'(제출\s*서류|첨부\s*서류|구비\s*서류|필요\s*서류|기본\s*서류|추가\s*서류|공통\s*서류|필수\s*서류|심사\s*서류|입증\s*서류\s*$|제출서류)')
KEY_PAREN = re.compile(r'^(\s*(?:[❍○◦◯ㅇ●•▪￭■◎\-–‣▸]\s*)?(?:[' + CIRC + r']\s*)?)\(([^()\n]{1,16})\)')

SECTION_KEYS = [
    ('scope',   re.compile(r'^(자격\s*해당자\s*및\s*)?활동\s*범위(\s*및\s*해당자)?$')),
    ('who',     re.compile(r'^해\s*당\s*자$')),
    ('period',  re.compile(r'체류기간(의)?\s*상한|1회\s*부여|1회에\s*부여')),
    ('consul',  re.compile(r'공관장\s*재량')),
    ('cert',    re.compile(r'사증발급인정서\s*발급\s*대상')),
    ('evisa',   re.compile(r'^전자\s*사증$')),
    ('note',    re.compile(r'^참고\s*사항$')),
    ('extra',   re.compile(r'체류자격\s*외\s*활동')),
    ('work',    re.compile(r'근무처')),
    ('grant',   re.compile(r'체류자격\s*부\s*여')),
    ('change',  re.compile(r'체류자격\s*변경')),
    ('extend',  re.compile(r'체류기간\s*연장')),
    ('reentry', re.compile(r'재입국')),
    ('reg',     re.compile(r'^외국인\s*등록$')),
]


def sec_key(label):
    for k, rx in SECTION_KEYS:
        if rx.search(label):
            return k
    return 'other'


def norm_space(s):
    s = s.replace('\u00a0', ' ')
    # "외 교" -> "외교", "해 당 자" -> "해당자": join single hangul syllables separated by single spaces
    def join(m):
        return m.group(0).replace(' ', '')
    s = re.sub(r'(?<![가-힣])(?:[가-힣] ){1,6}[가-힣](?![가-힣])', join, s)
    return re.sub(r'\s+', ' ', s).strip()


def read_lines(path):
    with open(path, encoding='utf-8') as f:
        return f.read().split('\n')


def unescape_md(s):
    return re.sub(r'\\([~*_\[\]`#|<>()\-.!+])', r'\1', s)


# ---------------------------------------------------------------- cleaning

def clean_soup(soup, tag):
    for img in list(soup.find_all('img')):
        src = img.get('src', '')
        m = re.search(r'(image_\d+)', src)
        name = m.group(1) if m else ''
        if tag == 's' and name == 'image_004':
            sp = soup.new_tag('span', attrs={'class': 'arw', 'aria-hidden': 'true'}); sp.string = '→'
            img.replace_with(sp)
            continue
        if name in BULLET_IMG.get(tag, ()):
            img.replace_with(soup.new_tag('i', attrs={'class': 'bul'}))
            continue
        if not name or name in DROP_IMG[tag]:
            img.decompose()
            continue
        key = f'{tag}_{name}'
        USED_IMG.add(key)
        new = soup.new_tag('img', attrs={'data-img': key, 'alt': '원문 그림', 'loading': 'lazy'})
        img.replace_with(new)
    # "목차" back-links
    for u in list(soup.find_all('u')):
        if u.get_text(strip=True) == '목차':
            u.decompose()
    # escaped markdown chars left inside raw html blocks
    for t in list(soup.find_all(string=True)):
        if isinstance(t, NavigableString) and ('\\' in t):
            t.replace_with(unescape_md(str(t)))
    # empty headings / "목차" headings
    for h in list(soup.find_all(re.compile(r'^h[1-6]$'))):
        txt = h.get_text(' ', strip=True)
        if not txt:
            h.decompose()
    # strong wrapping whole p -> keep


def collapse_brs(node):
    """remove leading/trailing/duplicate <br> inside a node"""
    prev_br = True
    for ch in list(node.contents):
        if isinstance(ch, Tag) and ch.name == 'br':
            if prev_br:
                ch.decompose()
            else:
                prev_br = True
        elif isinstance(ch, NavigableString) and not ch.strip():
            continue
        else:
            prev_br = False
    # trailing
    while node.contents:
        last = node.contents[-1]
        if isinstance(last, Tag) and last.name == 'br':
            last.decompose()
        elif isinstance(last, NavigableString) and not last.strip():
            last.extract()
        else:
            break


BLOCK = {'table', 'div', 'p', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'pre', 'hr'}


def line_class(text):
    for rx, c in LINE_RULES:
        if rx.match(text):
            return c
    return 'pl'


def bold_key(soup, line_tag):
    """wrap a leading "(키워드)" in <b class=k>"""
    for t in line_tag.find_all(string=True):
        s = str(t)
        if not s.strip():
            continue
        m = KEY_PAREN.match(s)
        if m:
            pre_s = NavigableString(m.group(1))
            b = soup.new_tag('b', attrs={'class': 'k'})
            b.string = f'({m.group(2)})'
            rest = NavigableString(s[m.end():])
            t.replace_with(pre_s)
            pre_s.insert_after(b)
            b.insert_after(rest)
        return


def structure_cell(soup, cell, doc_ctx=False):
    """Turn a <br>-separated cell into a column of classified lines. Returns a new div."""
    out = soup.new_tag('div', attrs={'class': 'rich'})
    cur = []
    state = {'doc': doc_ctx, 'list': None}

    def flush():
        nonlocal cur
        # strip whitespace-only
        nodes = [n for n in cur if not (isinstance(n, NavigableString) and not n.strip())]
        cur = []
        if not nodes:
            return
        tmp = soup.new_tag('span')
        for n in nodes:
            tmp.append(n.extract() if n.parent else n)
        buls = tmp.find_all('i', class_='bul')
        for b_ in buls:
            b_.decompose()
        text = tmp.get_text('', strip=True)
        if buls and not text:
            last = out.contents[-1] if out.contents else None
            if isinstance(last, Tag) and 'ln' in (last.get('class') or []) and 'pl' in last.get('class'):
                last['class'] = ['ln', 'b2', 'bi']
            elif isinstance(last, Tag) and last.name == 'ul' and last.contents:
                pass
            return
        bul_line = bool(buls)
        if not text:
            # maybe an image-only line
            if tmp.find('img'):
                d = soup.new_tag('div', attrs={'class': 'fig'})
                for c in list(tmp.contents):
                    d.append(c.extract())
                close_list()
                out.append(d)
            return
        cls = line_class(text)
        if state['doc'] and cls in ('n1', 'n0') and not DOC_TRIGGER.search(text):
            state['doc'] = False
        if state['doc'] and cls == 'n2' and not DOC_TRIGGER.search(text) and len(text) < 40:
            state['doc'] = False
        if DOC_TRIGGER.search(text) and len(text) < 120:
            state['doc'] = True
        if state['doc'] and cls == 'c2':
            ul = state['list']
            if ul is None:
                ul = soup.new_tag('ul', attrs={'class': 'docs'})
                out.append(ul)
                state['list'] = ul
            li = soup.new_tag('li', attrs={'class': 'doc'})
            body = soup.new_tag('span', attrs={'class': 'dt'})
            for c in list(tmp.contents):
                body.append(c.extract())
            li.append(soup.new_tag('i', attrs={'class': 'ck'}))
            li.append(body)
            ul.append(li)
            return
        if state['list'] is not None and cls in ('d3', 'fn', 'nt', 'a3', 'n3', 'n4', 'pl') and len(state['list'].contents):
            # attach as sub note to last doc item
            li = state['list'].contents[-1]
            sub = soup.new_tag('div', attrs={'class': 'ln ' + cls})
            for c in list(tmp.contents):
                sub.append(c.extract())
            bold_key(soup, sub)
            li.append(sub)
            return
        close_list()
        if cls == 'n1' and len(text) <= 70:
            cls = 'n1 hd'
        elif cls == 'n2' and len(text) <= 50:
            cls = 'n2 hd'
        elif cls in ('bx', 'sb', 'n0') and len(text) <= 80:
            cls += ' hd'
        if bul_line and cls == 'pl':
            cls = 'b2 bi'
        p = soup.new_tag('div', attrs={'class': 'ln ' + cls})
        for c in list(tmp.contents):
            p.append(c.extract())
        bold_key(soup, p)
        out.append(p)

    def close_list():
        state['list'] = None

    for ch in list(cell.contents):
        if isinstance(ch, Tag) and ch.name == 'br':
            flush()
            ch.decompose()
        elif isinstance(ch, Tag) and ch.name in BLOCK:
            flush()
            close_list()
            blk = ch.extract()
            if blk.name == 'table':
                out.append(transform_inner_table(soup, blk, state['doc']))
            else:
                out.append(blk)
        else:
            cur.append(ch)
    flush()
    return out


def is_doc_table(tbl):
    txt = tbl.get_text(' ', strip=True)
    return bool(txt) and txt[0] in CIRC and ('신청서' in txt or '서류' in txt or '여권' in txt)


def transform_inner_table(soup, tbl, doc_ctx=False):
    if is_doc_table(tbl):
        box = soup.new_tag('div', attrs={'class': 'docbox'})
        for cell in tbl.find_all(['td', 'th']):
            if cell.find_parent('table') is not tbl:
                continue
            box.append(structure_cell(soup, cell, doc_ctx=True))
        return box
    # generic table: structure br-lines in cells lightly, keep grid
    for cell in tbl.find_all(['td', 'th']):
        collapse_brs(cell)
    wrap = soup.new_tag('div', attrs={'class': 'tw'})
    tbl['class'] = 'grid'
    wrap.append(tbl)
    return wrap


def direct_rows(tbl):
    rows = []
    for part in tbl.children:
        if not isinstance(part, Tag):
            continue
        if part.name == 'tr':
            rows.append(part)
        elif part.name in ('thead', 'tbody', 'tfoot'):
            rows += [r for r in part.children if isinstance(r, Tag) and r.name == 'tr']
    return rows


def label_of(cell):
    parts = []
    for s in cell.get_text('\n').split('\n'):
        s = norm_space(s)
        if s and s != '목차' and s not in parts:
            parts.append(s)
    # labels like "별도 허가 없이 / 유학활동이 가능한 / 체류자격" split over lines: dedupe repeated groups
    lab = ' '.join(parts)
    # repeated label phrase (page break artifact) "A B A B" -> "A B"
    for n in range(1, len(parts)):
        if len(parts) % n == 0 and parts == parts[:n] * (len(parts) // n):
            lab = ' '.join(parts[:n])
            break
    toks = []
    for t in lab.split(' '):
        if t not in toks or len(t) <= 1:
            toks.append(t)
    return ' '.join(toks)


def row_cells(r):
    return [c for c in r.children if isinstance(c, Tag) and c.name in ('td', 'th')]


def section_table(tbl):
    rows = direct_rows(tbl)
    if not rows or len(row_cells(rows[0])) != 2:
        return None
    lens = [len(row_cells(r)[1].get_text()) for r in rows if len(row_cells(r)) == 2]
    if lens and sum(lens) / len(lens) < 12:
        return None
    known = 0
    for r in rows:
        cells = row_cells(r)
        if len(cells) == 2 and not cells[0].get('colspan'):
            lab = label_of(cells[0])
            if lab and len(lab) <= 45 and sec_key(lab) != 'other':
                known += 1
    if known < 2 and not (known == 1 and len(rows) <= 3):
        return None
    return rows


def rows_to_sections(soup, rows):
    secs = []
    span_left = 0
    for r in rows:
        cells = row_cells(r)
        if span_left > 0 and secs:
            span_left -= 1
            lab = ''
        elif len(cells) >= 3 and not cells[0].get('colspan') and len(label_of(cells[0])) <= 45:
            lab0 = label_of(cells[0])
            span_left = max(0, int(cells[0].get('rowspan', '1') or 1) - 1)
            body = soup.new_tag('div', attrs={'class': 'rich'})
            secs.append({'t': 'sec', 'k': sec_key(lab0), 'l': lab0, 'body': body})
            cells[0].decompose()
            cells = row_cells(r)
            lab = ''
        else:
            lab = label_of(cells[0]) if len(cells) == 2 and not cells[0].get('colspan') else None
        if lab and len(cells) == 2:
            span_left = max(0, int(cells[0].get('rowspan', '1') or 1) - 1)
        if lab is not None and lab and len(lab) <= 45:
            body = structure_cell(soup, cells[1])
            secs.append({'t': 'sec', 'k': sec_key(lab), 'l': lab, 'body': body})
            continue
        # continuation rows
        if not secs:
            secs.append({'t': 'sec', 'k': 'other', 'l': '', 'body': soup.new_tag('div', attrs={'class': 'rich'})})
        tgt = secs[-1]['body']
        if len(cells) == 1 or (len(cells) == 2 and lab is not None and not lab and not cells[0].get_text(strip=True)):
            tgt.append(structure_cell(soup, cells[-1]))
        else:
            t = soup.new_tag('table', attrs={'class': 'grid'})
            t.append(r.extract())
            for c in t.find_all(['td', 'th']):
                c.name = 'td'
                if c.find('br') and len(c.get_text()) > 60:
                    nb = structure_cell(soup, c); c.clear(); c.append(nb)
            # merge consecutive multi-cell rows into the same table
            last = tgt.contents[-1] if tgt.contents else None
            if isinstance(last, Tag) and last.get('class') == ['tw'] and last.get('data-cont'):
                last.table.append(t.tr.extract())
            else:
                w = soup.new_tag('div', attrs={'class': 'tw', 'data-cont': '1'})
                w.append(t)
                tgt.append(w)
    for s_ in secs:
        s_['h'] = str(s_.pop('body'))
    return secs


def transform_chapter(html, tag):
    soup = BeautifulSoup(f'<div id="root">{html}</div>', 'html5lib')
    root = soup.find(id='root')
    clean_soup(root, tag)
    blocks = []
    buf = soup.new_tag('div')

    def flush_buf():
        nonlocal buf
        if buf.get_text(strip=True) or buf.find('img'):
            blocks.append({'t': 'html', 'h': fix_free_html(soup, buf)})
        buf = soup.new_tag('div')

    for node in list(root.children):
        if isinstance(node, Tag) and node.name == 'table':
            rows = section_table(node)
            if rows:
                flush_buf()
                blocks += rows_to_sections(soup, rows)
                continue
        buf.append(node.extract())
    flush_buf()
    # drop a leading free block that only repeats the chapter title, e.g. "유 학(D-2)"
    if blocks and blocks[0]['t'] == 'html':
        txt = re.sub(r'<[^>]+>', '', blocks[0]['h']).strip()
        if len(txt) <= 30 and re.search(r'\([A-Z]-\d', txt) and len(blocks) > 1:
            blocks.pop(0)
    return blocks


HEAD_MARK = re.compile(r'^[❍○◦◯ㅇ●•▪\-–‣▸※\*' + CIRC + r']')


def fix_free_html(soup, div):
    for b_ in div.find_all('i', class_='bul'):
        b_.decompose()
    # headings that are really paragraphs
    for h in list(div.find_all(re.compile(r'^h[1-6]$'))):
        txt = h.get_text(' ', strip=True)
        if len(txt) > 70 or HEAD_MARK.match(txt):
            h.name = 'p'
            cls = line_class(txt)
            h['class'] = 'ln ' + cls
            bold_key(soup, h)
        else:
            h.name = 'h4'
            h['class'] = 'fh'
    # plain paragraphs: classify for indentation
    for p in div.find_all('p'):
        if p.get('class'):
            continue
        txt = p.get_text(' ', strip=True)
        cls = line_class(txt)
        if cls == 'n1' and len(txt) <= 70:
            cls = 'n1 hd'
        p['class'] = 'ln ' + cls
        bold_key(soup, p)
    # tables
    for tbl in list(div.find_all('table')):
        if tbl.parent is None or tbl.find_parent('table') is not None:
            continue
        rows = direct_rows(tbl)
        # numbered banner tables like | 1 | | 결핵진단서 ... |  -> heading
        if len(rows) == 1:
            cells = [c.get_text(' ', strip=True) for c in rows[0].find_all(['td', 'th'])]
            if 2 <= len(cells) <= 3 and re.fullmatch(r'(붙임\s*)?\d{1,2}', cells[0] or '') and cells[-1]:
                h = soup.new_tag('h3', attrs={'class': 'banner'})
                h.string = (cells[0] + '  ' + cells[-1]).strip()
                tbl.replace_with(h)
                continue
        if len(rows) == 1 and len(rows[0].find_all(['td', 'th'], recursive=False)) == 1:
            # single cell box -> callout
            cell = rows[0].find(['td', 'th'])
            box = structure_cell(soup, cell)
            box['class'] = 'rich callout'
            tbl.replace_with(box)
            continue
        if len(rows) == 0:
            tbl.decompose()
            continue
        for cell in tbl.find_all(['td', 'th']):
            if cell.find('br') and len(cell.get_text()) > 60:
                nb = structure_cell(soup, cell)
                cell.clear()
                cell.append(nb)
            else:
                collapse_brs(cell)
        wrap = soup.new_tag('div', attrs={'class': 'tw'})
        tbl.replace_with(wrap)
        tbl['class'] = 'grid'
        wrap.append(tbl)
    return ''.join(str(c) for c in div.contents)


def split_chapters(lines, spec):
    out = []
    for i, (start, key, _) in enumerate(spec):
        end = spec[i + 1][0] - 1 if i + 1 < len(spec) else len(lines)
        out.append((key, '\n'.join(lines[start - 1:end])))
    return out


def first_title(text):
    for ln in text.split('\n'):
        s = ln.strip()
        if s and not s.startswith('<') and not s.startswith('|'):
            return norm_space(re.sub(r'[#*]', '', s))
    return ''




def split_chapters(lines, spec):
    out = []
    for i, (start, key, _) in enumerate(spec):
        end = spec[i + 1][0] - 1 if i + 1 < len(spec) else len(lines)
        out.append((key, '\n'.join(lines[start - 1:end])))
    return out


def first_title(text):
    for ln in text.split('\n'):
        s = ln.strip()
        if s and not s.startswith('<') and not s.startswith('|'):
            return norm_space(re.sub(r'[#*\\]|<[^>]+>', '', s))
    return ''


def letters(text):
    return Counter(c for c in htmlmod.unescape(text) if re.match(r'[가-힣A-Za-z0-9]', c))


def html_text(h):
    return BeautifulSoup(h, 'html5lib').get_text(' ')


def compact(s):
    return re.sub(r'[^가-힣A-Za-z0-9]', '', s)


def build():
    chapters, reports, search = {}, [], []
    sources = {}
    for tag in ('v', 's'):
        meta = SOURCES[tag]
        path = SRC_DIR / meta['file']
        raw = path.read_bytes()
        text_all = raw.decode('utf-8')
        lines = text_all.split('\n')
        spec = CHAPTERS_V if tag == 'v' else CHAPTERS_S
        # provenance cross-check against the independently extracted PDF text of the same edition
        pdf_compact = compact((ROOT / meta['pdf_text']).read_text(encoding='utf-8'))
        md_plain = BeautifulSoup(md.render(text_all), 'html5lib').get_text('\n')
        probes = [c for c in (compact(l) for l in md_plain.split('\n')) if len(c) >= 15]
        matched = sum(1 for c in probes if c[:15] in pdf_compact)
        sources[tag] = dict({k: v for k, v in meta.items() if k not in ('images',)},
                            markdown=f'docs/source-manuals/2026-09/markdown/{meta["file"]}',
                            sha256=hashlib.sha256(raw).hexdigest(), official_url=OFFICIAL_URL,
                            approval_state='needs_review',
                            pdf_crosscheck={'probes': len(probes), 'matched': matched,
                                            'ratio': round(matched / len(probes), 4)})
        for key, text in split_chapters(lines, spec):
            rendered = md.render(text)
            blocks = transform_chapter(rendered, tag)
            title = first_title(text)
            chapters.setdefault(key, {})[tag] = {'key': key, 'src': tag, 'title': title, 'blocks': blocks}
            orig = letters(BeautifulSoup(rendered, 'html5lib').get_text(' ').replace('목차', ''))
            new = letters(' '.join(html_text(b['h']) + ' ' + b.get('l', '') for b in blocks))
            labels = letters(' '.join(b.get('l', '') for b in blocks))
            reports.append({'src': tag, 'key': key, 'chars': sum(orig.values()),
                            'missing': sum((orig - new).values()), 'added': sum((new - orig).values())})
            for i, b in enumerate(blocks):
                search.append([key, tag, i, re.sub(r'\s+', ' ', html_text(b['h'])).strip()])
    return sources, chapters, reports, search


def image_files():
    out = {}
    for key in sorted(USED_IMG):
        tag, name = key.split('_', 1)
        folder = SRC_DIR / SOURCES[tag]['images']
        f = sorted(folder.glob(name + '.*'))[0]
        from PIL import Image
        im = Image.open(f)
        im = im.convert('RGBA' if im.mode in ('RGBA', 'P', 'LA') else 'RGB')
        if im.width > 1000:
            im = im.resize((1000, round(im.height * 1000 / im.width)))
        buf = io.BytesIO()
        im.save(buf, 'WEBP', quality=82, method=6)
        out[f'{key}.webp'] = buf.getvalue()
    return out


def dumps(v):
    return json.dumps(v, ensure_ascii=False, separators=(',', ':')) + '\n'


def outputs():
    sources, chapters, reports, search = build()
    files = {}
    catalog = {'schema_version': 1, 'edition': '2026.9', 'generated_by': 'scripts/build_manual_reader.py',
               'note': '원문 문장은 바꾸지 않음. 쪽 넘김 때문에 반복된 항목명·목차 링크·장 제목 줄·표지 이미지만 제외.',
               'sources': sources, 'chapters': []}
    for key, by in chapters.items():
        entry = {'key': key}
        for tag, c in by.items():
            files[f'chapters/{tag}/{key}.json'] = dumps(c)
            entry[tag] = {'title': c['title'], 'bytes': sum(len(b['h']) for b in c['blocks']),
                          'sections': [{'t': b['t'], 'k': b.get('k'), 'l': b.get('l', '')} for b in c['blocks']]}
        catalog['chapters'].append(entry)
    catalog['preservation'] = reports
    files['catalog.json'] = json.dumps(catalog, ensure_ascii=False, indent=1) + '\n'
    files['search.json'] = dumps(search)
    return files, catalog


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='rebuild in memory and compare with committed outputs')
    args = ap.parse_args()
    files, catalog = outputs()
    imgs = image_files()
    problems = []
    for r in catalog['preservation']:
        # repeated row labels are the only expected loss; allow 2% of a chapter, never more than 400 letters
        if r['missing'] > max(40, min(400, r['chars'] * 0.02)) or r['added'] > 0:
            problems.append(f"{r['src']}/{r['key']}: missing {r['missing']} added {r['added']} of {r['chars']}")
    for tag, s in catalog['sources'].items():
        if s['pdf_crosscheck']['ratio'] < 0.97:
            problems.append(f"{tag}: Markdown matches only {s['pdf_crosscheck']['ratio']:.2%} of PDF text probes")
    if args.check:
        for rel, content in files.items():
            p = OUT_DIR / rel
            if not p.exists() or p.read_text(encoding='utf-8') != content:
                problems.append(f'stale output: data/manual-reader/{rel} (run python3 scripts/build_manual_reader.py)')
        on_disk = {p.relative_to(OUT_DIR).as_posix() for p in OUT_DIR.rglob('*.json')}
        for extra in sorted(on_disk - set(files) - {'editorial.json'}):
            problems.append(f'orphan output: data/manual-reader/{extra}')
        for name in imgs:
            if not (IMG_OUT / name).exists():
                problems.append(f'missing image: assets/manual-reader/img/{name}')
    else:
        if OUT_DIR.exists():
            for p in OUT_DIR.rglob('*.json'):
                if p.name != 'editorial.json':
                    p.unlink()
        for rel, content in files.items():
            p = OUT_DIR / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
        IMG_OUT.mkdir(parents=True, exist_ok=True)
        for name, data in imgs.items():
            (IMG_OUT / name).write_bytes(data)
    total = sum(r['chars'] for r in catalog['preservation'])
    lost = sum(r['missing'] for r in catalog['preservation'])
    print(f"manual reader: {len(catalog['chapters'])} chapters, {total} letters, {lost} removed as page-break noise "
          f"({lost / total:.3%}); PDF cross-check " +
          ', '.join(f"{t} {s['pdf_crosscheck']['ratio']:.2%}" for t, s in catalog['sources'].items()))
    if problems:
        print('\n'.join('FAIL ' + p for p in problems))
        sys.exit(1)


if __name__ == '__main__':
    main()
