"""Where the person a question is about is: abroad (a visa matter) or in Korea (a stay matter).

``manual_evidence.procedure_scopes`` decides which manual a question's excerpts come
from by its procedure words. A question that names no procedure ("마닐라에서 지내는데
한국 대학원에 합격했어요. 유학 비자 받으면 체류기간은?") got no manual, or the stay
manual on the word 체류기간 alone. This module reads where the foreigner is from
place names, invitation words and tasks only done in Korea.

Measured in experiments/waymaker-ai/artemis_bootstrap (procedure_route.py, held-out
sets written by agents that never saw the code): on held-out v12, 20 of 30 questions
routed to the right manual against 13 with the procedure words alone; questions sent to
the wrong manual stayed at 2 of 30. On the 140 real-manual questions, 19 routes changed
and none went to the wrong manual. Not a legal judgement; deterministic, no model call.
"""
from __future__ import annotations

import re

#: Places in Korea.
_KOREAN_PLACES = ("한국", "국내", "서울", "부산", "인천", "대구", "대전", "광주", "울산", "세종", "제주", "수원",
                  "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "창원", "천안", "청주", "전주",
                  "포항", "김해", "안산", "평택", "화성", "용인", "고양", "성남", "여기", "이곳")
_KOREAN_PLACES_EN = ("Korea", "Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Gwangju", "Ulsan", "Sejong",
                     "Jeju", "Suwon", "Changwon", "here")
#: Places abroad people name ("마닐라에서 지내는데"). A place on neither list (농장, 연구소,
#: 카페) says nothing about the country.
_FOREIGN_PLACES = ("베트남", "하노이", "호치민", "필리핀", "마닐라", "세부", "중국", "베이징", "상하이", "칭다오", "하얼빈",
                   "옌볜", "연변", "일본", "도쿄", "오사카", "몽골", "울란바토르", "우즈베키스탄", "타슈켄트", "카자흐스탄",
                   "키르기스스탄", "러시아", "모스크바", "인도네시아", "자카르타", "태국", "방콕", "캄보디아", "프놈펜",
                   "라오스", "미얀마", "네팔", "카트만두", "스리랑카", "방글라데시", "파키스탄", "인도", "뉴델리", "대만",
                   "타이베이", "홍콩", "싱가포르", "말레이시아", "동티모르", "미국", "뉴욕", "캐나다", "토론토", "밴쿠버",
                   "영국", "런던", "독일", "베를린", "프랑스", "파리", "이탈리아", "스페인", "호주", "시드니", "뉴질랜드",
                   "브라질", "페루", "리마", "멕시코", "칠레", "나이지리아", "라고스", "케냐", "이집트", "튀르키예", "터키",
                   "본국", "고향", "친정", "해외", "외국")
_FOREIGN_PLACES_EN = ("Vietnam", "Hanoi", "Philippines", "Manila", "China", "Beijing", "Shanghai", "Japan", "Tokyo",
                      "Osaka", "Mongolia", "Uzbekistan", "Tashkent", "Kazakhstan", "Russia", "Moscow", "Indonesia",
                      "Jakarta", "Thailand", "Bangkok", "Cambodia", "Nepal", "India", "Delhi", "Taiwan", "Taipei",
                      "Singapore", "Malaysia", "America", "York", "Canada", "Toronto", "Vancouver", "England",
                      "London", "Germany", "Berlin", "France", "Paris", "Australia", "Sydney", "Zealand", "Brazil",
                      "Peru", "Lima", "Mexico", "Chile", "Nigeria", "Lagos", "Kenya", "Egypt", "Turkey", "home", "abroad")
#: "X에서 지내는데", "X에 살아요", "X에 2주째 있는데": where someone is now. Not "X에 있는
#: 회사" (an organisation), "X에서 공부하려면" (an intention), "X에 나가 있으면" (a trip), or
#: "…받을 수 있나요".
_ORG = r"(?:회사|교회|기관|학교|대학|영사관|대사관|공장|단체)"
_STAYS_AT_RE = re.compile(
    r"([가-힣]{2,})(?:에서|에)\s+(?:(?!나가|수\s)\S+\s+){0,2}?"
    rf"(?:살(?!려)|지내(?!려)|있(?!는\s*{_ORG}|으려)|머물(?!려)|거주|공부하(?!려)|일하(?!려)|다니(?!려))")
_STAYS_AT_EN_RE = re.compile(
    r"\b(?:I(?:'m| am)|we(?:'re| are)|(?:he|she)(?:'s| is))\s+(?:still\s+|already\s+|back\s+home\s+)?"
    r"(?:in|at|living in|based in|staying in)\s+([A-Z][a-z]+)"
    r"|\bI\s+live\s+in\s+([A-Z][a-z]+)|\bout of\s+([A-Z][a-z]+)|\bcame (?:in)?to\s+([A-Z][a-z]+)"
    r"|\b(?:registered|living) (?:here )?in\s+([A-Z][a-z]+)|\bcontract in\s+([A-Z][a-z]+)")
_ABROAD_WORD_RE = re.compile(r"(?:고향|본국|친정|해외|외국)\s*\S*\s*(?:에|에서)\s*(?:있|살|지내)|아직\s+\S+에\s+있"
                             r"|한국(?:에|으로)\s*(?:가|오|들어가|들어오)(?:려|고\s*싶|면|게\s*되)"
                             r"|\b(?:come|coming|move|moving|fly|flying)\s+(?:to\s+Korea|over)\b|\boverseas\b|\babroad\b|\bfrom here\b",
                             re.IGNORECASE)
_IN_KOREA_WORD_RE = re.compile(r"들어와(?:서|\s*있)|들어왔|입국해서|입국했|와\s*있|외국인등록\s*(?:하고|했|돼)|등록돼\s*있"
                               r"|\balready in Korea\b|\bwithout leaving\b|\bstill in Korea\b", re.IGNORECASE)
#: Bringing someone from abroad: a visa matter even when the asker is in Korea.
_INVITE_RE = re.compile(r"초청|불러\s*오|불러서|불러오|모셔\s*오|데려오|데리고\s*오|뽑겠|채용하려|고용하려|사증발급인정서"
                        r"|영사관|대사관|\binvite\b|\bsponsor\b|\bhire me\b|\boffer from\b|\bbook flights\b|\bconsulate\b|\bembassy\b",
                        re.IGNORECASE)
#: Something only done in Korea: a stay matter even when the asker is abroad.
IN_KOREA_TASK_RE = re.compile(r"외국인등록증|연장|변경|재입국|아르바이트|시간제|옮겨|바꿀|바꾸|자격외|신고"
                               r"|\bextend\b|\bswitch\b|\breport\b|\bcard expires\b|\bpart-time\b|\bchange\b", re.IGNORECASE)
def location(question: str) -> str:
    """"abroad" (a visa matter: the foreigner concerned is outside Korea or is being
    brought in), "korea" (a stay matter: they are in Korea, or the task is one only
    done in Korea) or "" (cannot tell)."""
    q = question or ""
    korea = abroad = False
    for m in _STAYS_AT_RE.finditer(q):
        # The place word, or the word before it: "캐나다 집에서", "필리핀 마닐라에서".
        before = q[max(0, m.start() - 8):m.start()]
        if any(p in m.group(1) for p in _KOREAN_PLACES):
            korea = True
        elif any(p in m.group(1) or p in before for p in _FOREIGN_PLACES):
            abroad = True
    for m in _STAYS_AT_EN_RE.finditer(q):
        place = next(g for g in m.groups() if g)
        if place in _KOREAN_PLACES_EN:
            korea = True
        elif place in _FOREIGN_PLACES_EN:
            abroad = True
    abroad = abroad or bool(_ABROAD_WORD_RE.search(q))
    korea = korea or bool(_IN_KOREA_WORD_RE.search(q))
    invite, task = bool(_INVITE_RE.search(q)), bool(IN_KOREA_TASK_RE.search(q))
    if invite and not (korea and task and not abroad):
        return "abroad" if (abroad or korea) else ""
    if korea and (task or not abroad):
        return "korea"
    if abroad and not korea:
        return "abroad"
    return ""
