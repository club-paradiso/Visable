# External cross-check — K-ETA temporary exemption (2026-06-13)

목적: 단기입국 체커의 "법령 근거 3스텝" 중 (C) 외부 교차검증 단계 기록.

## 환경 제약
- 공식 누리집 직접 조회(`law.go.kr`, `k-eta.go.kr`, MOFA 공관 `view.do`)는 이 환경에서 HTTP 403으로 차단됨.
- 단, 검색 도구(WebSearch)는 사용 가능하여 공개 색인으로 교차확인을 수행함.

## 확인 결과 — K-ETA 한시 면제 2026-12-31 연장
운영자 제공 사실(2026-06-13: "K-ETA가 2026-12-31까지 유예")을 외부 공개 출처로 교차확인함:

- 주캐나다 대한민국대사관 공지 — "Extension of Temporary Exemption from K-ETA (until December 31, 2026)"
  https://www.mofa.go.kr/ca-en/brd/m_5231/view.do?seq=761797
- VISITKOREA(한국관광공사) — "K-ETA Exemption Period Extended Until 2026"
  https://english.visitkorea.or.kr/svc/contents/contentsView.do?vcontsId=251923
- 복수 재외공관 공지(오스트리아·괌 등) 및 업계 정리(Fragomen 등)에서 동일 확인.

요지(교차확인된 범위):
- 법무부가 관광 활성화를 위해 K-ETA 한시 면제를 1년 추가 연장, **2026-12-31(KST)까지** 유효.
- 적용 대상: 현재 K-ETA 한시 면제 대상인 무사증 국가·지역(저장 사본 기준 22개국·지역, 미국 포함).
- 면제 기간 중 해당 국적자는 K-ETA를 신청하지 않고 무사증 입국 가능. 단, 도착 신고(e-Arrival Card) 면제 등
  K-ETA 혜택을 원하면 선택적으로 신청 가능(수수료 부과).

## 데이터 반영
- `data/short-stay/fixtures/keta_program.json`: `lastVerifiedThrough` 2026-12-31, `extensionUnverified=false`.
- `data/short-stay/sources.json` (k_eta_eligible_countries): `crossCheckedAt=2026-06-13`, `crossCheckUrls` 추가.
- 제도 세부(수수료·유효기간 등)는 여전히 실시간 조회 불가로 저장 사본 기준(confidence: medium).

## 후속(미반영, follow-up)
- e-Arrival Card(도착 신고) 의무화는 별도 제도 — 체커 범위 밖. 향후 별도 안내 검토.
- 2026-12-31 이후 연장·종료 여부는 재확인 필요(체커 워딩에 종료일 이후 확인 안내 포함됨).
