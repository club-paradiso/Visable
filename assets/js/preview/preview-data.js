/**
 * PreView by Paradiso — local MVP fallback sample data.
 *
 * This file is the offline fallback layer. It mirrors the curated snapshots in
 * data/preview/ and is rendered whenever the backend public-data proxy is
 * unavailable or returns no items.
 *
 * Content policy (hard rules):
 * - Everything here is labeled MVP 샘플 데이터. isSample stays true.
 * - No invented official facts: no phone numbers, fees, processing times,
 *   document lists, or waiver decisions. Unverified fields carry
 *   "공식 원문 확인 필요" instead of a value.
 * - URLs are official mofa.go.kr / overseas.mofa.go.kr / data.go.kr pages
 *   corroborated during source verification; nothing synthesized.
 */
(function () {
  'use strict';

  var DATA = {
    schemaVersion: 1,
    generatedAt: '2026-07-04',
    isSample: true,
    sampleBadgeKo: 'MVP 샘플 데이터',
    sampleNoticeKo:
      '아래 내용은 MVP 샘플 데이터입니다. 확인되지 않은 항목은 값 대신 "공식 원문 확인 필요"로 표시하며, 관할 공관에 최종 확인하세요.',
    apiFallbackMessageKo:
      '현재 공공데이터 API 응답을 불러오지 못해 MVP 샘플 데이터를 표시합니다. 최종 정보는 관할 재외공관 공식 원문을 확인해야 합니다.',
    apiLiveMessageKo:
      '공공데이터 API 기반 — 공관 카드가 외교부 재외공관 정보 API 응답으로 렌더링되었습니다.',
    unsupportedCountryMessageKo:
      '선택한 국가는 아직 PreView MVP 샘플 범위(베트남·몽골·우즈베키스탄)에 없습니다. 관할 재외공관 공식 안내와 외교부 공공데이터 원문을 직접 확인해 주세요. 공관 공식 안내 확인이 가장 확실한 첫 단계입니다.',
    disclaimerKo:
      'PreView는 외교 공공데이터와 공식 공개자료를 바탕으로 입국 전 확인사항을 정리하는 서비스입니다. 최종 사증 발급 여부, 접수 가능 여부, 요구서류, 심사 결과는 관할 재외공관의 공식 안내와 판단을 따라야 합니다.',

    manual: {
      manualVersion: '2026.6',
      importedAt: '2026-07-04',
      sourceLabelKo: '사증발급 안내매뉴얼 (법무부, 2026.6 판독본) — 매뉴얼 기준 참고',
      usageBoundaryKo:
        '매뉴얼 기준 참고는 참고 레이어입니다. 요구서류·심사 결과의 근거가 아니며, 공관별 접수 방식과 추가 제출서류는 관할 재외공관 공식 안내 확인 필요.',
      records: [
        {
          code: 'D-2',
          purposeCategory: 'study',
          headingKo: '유학(D-2)',
          issuanceRouteSummaryKo:
            '매뉴얼 해당 절에서 확인된 발급 경로 단서: 사증발급인정서 관련 절, 첨부서류 절, 제출서류 절 — 적용 대상과 세부 요건은 매뉴얼 원문과 관할 재외공관 공식 안내 확인 필요',
          evidenceLevel: 'manual_reference',
          requiresOfficialMissionCheck: true,
          sourcePointer: { page: 62, section: '유학(D-2)' }
        },
        {
          code: 'D-4',
          purposeCategory: 'study',
          headingKo: '일반연수(D-4)',
          issuanceRouteSummaryKo:
            '매뉴얼 해당 절에서 확인된 발급 경로 단서: 사증발급인정서 관련 절, 첨부서류 절 — 적용 대상과 세부 요건은 매뉴얼 원문과 관할 재외공관 공식 안내 확인 필요',
          evidenceLevel: 'manual_reference',
          requiresOfficialMissionCheck: true,
          sourcePointer: { page: 73, section: '일반연수(D-4)' }
        },
        {
          code: 'C-3',
          purposeCategory: 'short_visit',
          headingKo: '단기방문(C-3)',
          issuanceRouteSummaryKo:
            '매뉴얼 해당 절에서 확인된 발급 경로 단서: 사증발급인정서 관련 절, 전자사증 관련 절, 제출서류 절 — 적용 대상과 세부 요건은 매뉴얼 원문과 관할 재외공관 공식 안내 확인 필요',
          evidenceLevel: 'manual_reference',
          requiresOfficialMissionCheck: true,
          sourcePointer: { page: 27, section: '단기방문(C-3)' }
        },
        {
          code: 'C-4',
          purposeCategory: 'business',
          headingKo: '단기취업(C-4)',
          issuanceRouteSummaryKo:
            '매뉴얼 해당 절에서 확인된 발급 경로 단서: 첨부서류 절 — 적용 대상과 세부 요건은 매뉴얼 원문과 관할 재외공관 공식 안내 확인 필요',
          evidenceLevel: 'manual_reference',
          requiresOfficialMissionCheck: true,
          sourcePointer: { page: 51, section: '단기취업(C-4)' }
        }
      ]
    },

    bundles: [
      {
        id: 'vn',
        countryKo: '베트남',
        countryEn: 'Vietnam',
        iso2: 'VN',
        iso2Verified: true,
        posts: [
          {
            nameKo: '주베트남 대한민국 대사관',
            cityKo: '하노이',
            typeKo: '대사관',
            officialSiteUrl: 'https://overseas.mofa.go.kr/vn-ko/index.do',
            urlVerification: 'search_index_corroborated',
            contactNoteKo:
              '전화번호·주소는 샘플에 수록하지 않았습니다. 공관 공식 홈페이지 또는 공공데이터 API 응답에서 확인해 주세요. 공식 원문 확인 필요.'
          },
          {
            nameKo: '주호치민 대한민국 총영사관',
            cityKo: '호치민',
            typeKo: '총영사관',
            officialSiteUrl: 'https://overseas.mofa.go.kr/vn-hochiminh-ko/index.do',
            urlVerification: 'search_index_corroborated',
            contactNoteKo:
              '전화번호·주소는 샘플에 수록하지 않았습니다. 공관 공식 홈페이지 또는 공공데이터 API 응답에서 확인해 주세요. 공식 원문 확인 필요.'
          }
        ],
        entryPrecheck: {
          statusKo: '공식 원문 확인 필요',
          summaryKo:
            '일반여권 소지자의 대한민국 입국 사증 면제 여부는 이 MVP에서 원문 확인이 완료되지 않았습니다. 외교부 사증 면제협정 체결현황 자료(공공데이터포털 파일데이터)와 관할 공관 공지에서 확인해 주세요.',
          checkPointsKo: [
            '외교부 사증 면제협정 체결현황 원문에서 베트남 항목 확인',
            '관할 재외공관(주베트남 대사관·주호치민 총영사관) 공지 확인'
          ]
        },
        safety: {
          statusKo: '샘플 미수록',
          summaryKo:
            '국가별 안전정보·여행경보는 외교부 공공데이터로 제공됩니다. 이 MVP 샘플에는 실시간 안전정보를 수록하지 않았습니다. 공식 원문 확인 필요.'
        },
        missionNotices: [
          {
            country: '베트남',
            post: '주베트남 대한민국 대사관',
            title: '사증 종류별 첨부서류 게시판',
            url: 'https://overseas.mofa.go.kr/vn-ko/brd/m_2198/list.do',
            fetchedAt: null,
            language: 'ko',
            textSnippet: '공식 원문 확인 필요 — 게시판 경로·제목은 검색 색인 기준이며, 서류 목록은 이 샘플에 수록하지 않았습니다.',
            sourceType: 'overseas_mofa_public_web',
            evidenceLevel: 'official_public_web',
            extractionStatus: 'curated_reference_pending_fetch'
          },
          {
            country: '베트남',
            post: '주베트남 대한민국 대사관',
            title: '베트남인 유학비자 서류 및 절차 안내(어학연수비자 포함)',
            url: 'https://overseas.mofa.go.kr/vn-ko/brd/m_2197/view.do?seq=759500',
            fetchedAt: null,
            language: 'ko',
            textSnippet: '공식 원문 확인 필요 — 게시글 제목은 검색 색인 기준입니다. 본문·서류 목록은 수록하지 않았으며, 완전한 공식 체크리스트가 아닙니다.',
            sourceType: 'overseas_mofa_public_web',
            evidenceLevel: 'official_public_web',
            extractionStatus: 'curated_reference_pending_fetch'
          },
          {
            country: '베트남',
            post: '주호치민 대한민국 총영사관',
            title: '공지사항 게시판',
            url: 'https://overseas.mofa.go.kr/vn-hochiminh-ko/brd/m_4024/list.do',
            fetchedAt: null,
            language: 'ko',
            textSnippet: '공식 원문 확인 필요 — 게시판 경로는 검색 색인에서 확인되었고, 본문은 아직 수집되지 않았습니다.',
            sourceType: 'overseas_mofa_public_web',
            evidenceLevel: 'official_public_web',
            extractionStatus: 'curated_reference_pending_fetch'
          },
          {
            country: '베트남',
            post: '주호치민 대한민국 총영사관',
            title: '구비서류 게시판',
            url: 'https://overseas.mofa.go.kr/vn-hochiminh-ko/brd/m_4020/list.do',
            fetchedAt: null,
            language: 'ko',
            textSnippet: '공식 원문 확인 필요 — 게시판 제목은 검색 색인 기준이며, 서류 목록은 이 샘플에 수록하지 않았습니다.',
            sourceType: 'overseas_mofa_public_web',
            evidenceLevel: 'official_public_web',
            extractionStatus: 'curated_reference_pending_fetch'
          }
        ],
        sources: [
          {
            titleKo: '외교부_국가·지역별 재외공관 정보 (공공데이터포털 OpenAPI)',
            sourceType: 'mofa_public_data_portal_api',
            evidenceLevel: 'official_reference_confirmed',
            url: 'https://www.data.go.kr/data/15075354/openapi.do'
          },
          {
            titleKo: '외교부_국가별 사증 면제협정 체결현황 (공공데이터포털 파일데이터)',
            sourceType: 'mofa_public_data_portal_file',
            evidenceLevel: 'official_reference_partial',
            url: 'https://www.data.go.kr/data/15099235/fileData.do'
          },
          {
            titleKo: '주베트남 대사관·주호치민 총영사관 공식 홈페이지 공개 게시판',
            sourceType: 'overseas_mofa_public_web',
            evidenceLevel: 'official_public_web',
            url: 'https://overseas.mofa.go.kr/vn-ko/index.do'
          },
          {
            titleKo: '사증발급 안내매뉴얼 2026.6 (법무부) — 매뉴얼 기준 참고 레이어',
            sourceType: 'uploaded_visa_issuance_manual_hwp',
            evidenceLevel: 'manual_reference',
            url: null
          },
          {
            titleKo: 'PreView 로컬 MVP 샘플 데이터',
            sourceType: 'curated_mvp_sample',
            evidenceLevel: 'curated_sample',
            url: null
          }
        ]
      },
      {
        id: 'mn',
        countryKo: '몽골',
        countryEn: 'Mongolia',
        iso2: 'MN',
        iso2Verified: true,
        posts: [
          {
            nameKo: '주몽골 대한민국 대사관',
            cityKo: '울란바토르',
            typeKo: '대사관',
            officialSiteUrl: 'https://overseas.mofa.go.kr/mn-ko/index.do',
            urlVerification: 'search_index_corroborated',
            contactNoteKo:
              '전화번호·주소는 샘플에 수록하지 않았습니다. 공관 공식 홈페이지 또는 공공데이터 API 응답에서 확인해 주세요. 공식 원문 확인 필요.'
          }
        ],
        entryPrecheck: {
          statusKo: '공식 원문 확인 필요',
          summaryKo:
            '일반여권 소지자의 대한민국 입국 사증 면제 여부는 이 MVP에서 원문 확인이 완료되지 않았습니다. 외교부 사증 면제협정 체결현황 자료와 관할 공관 공지에서 확인해 주세요.',
          checkPointsKo: [
            '외교부 사증 면제협정 체결현황 원문에서 몽골 항목 확인',
            '관할 재외공관(주몽골 대사관) 공지 확인'
          ]
        },
        safety: {
          statusKo: '샘플 미수록',
          summaryKo:
            '국가별 안전정보·여행경보는 외교부 공공데이터로 제공됩니다. 이 MVP 샘플에는 실시간 안전정보를 수록하지 않았습니다. 공식 원문 확인 필요.'
        },
        missionNotices: [
          {
            country: '몽골',
            post: '주몽골 대한민국 대사관',
            title: '사증(사증발급절차안내) — 공지사항 게시글',
            url: 'https://overseas.mofa.go.kr/mn-ko/brd/m_373/view.do?seq=572641',
            fetchedAt: null,
            language: 'ko',
            textSnippet: '공식 원문 확인 필요 — 게시글 제목은 검색 색인 기준입니다. 본문은 수록하지 않았으며, 완전한 공식 체크리스트가 아닙니다.',
            sourceType: 'overseas_mofa_public_web',
            evidenceLevel: 'official_public_web',
            extractionStatus: 'curated_reference_pending_fetch'
          },
          {
            country: '몽골',
            post: '주몽골 대한민국 대사관',
            title: '공관 대표 페이지 (공지사항 게시판 접점)',
            url: 'https://overseas.mofa.go.kr/mn-ko/index.do',
            fetchedAt: null,
            language: 'ko',
            textSnippet: '공식 원문 확인 필요 — 공지 본문은 아직 수집되지 않았습니다. 공관 공식 안내 확인을 첫 단계로 권장합니다.',
            sourceType: 'overseas_mofa_public_web',
            evidenceLevel: 'official_public_web',
            extractionStatus: 'curated_reference_pending_fetch'
          }
        ],
        sources: [
          {
            titleKo: '외교부_국가·지역별 재외공관 정보 (공공데이터포털 OpenAPI)',
            sourceType: 'mofa_public_data_portal_api',
            evidenceLevel: 'official_reference_confirmed',
            url: 'https://www.data.go.kr/data/15075354/openapi.do'
          },
          {
            titleKo: '외교부_국가별 사증 면제협정 체결현황 (공공데이터포털 파일데이터)',
            sourceType: 'mofa_public_data_portal_file',
            evidenceLevel: 'official_reference_partial',
            url: 'https://www.data.go.kr/data/15099235/fileData.do'
          },
          {
            titleKo: '주몽골 대사관 공식 홈페이지 공개 게시판',
            sourceType: 'overseas_mofa_public_web',
            evidenceLevel: 'official_public_web',
            url: 'https://overseas.mofa.go.kr/mn-ko/index.do'
          },
          {
            titleKo: '사증발급 안내매뉴얼 2026.6 (법무부) — 매뉴얼 기준 참고 레이어',
            sourceType: 'uploaded_visa_issuance_manual_hwp',
            evidenceLevel: 'manual_reference',
            url: null
          },
          {
            titleKo: 'PreView 로컬 MVP 샘플 데이터',
            sourceType: 'curated_mvp_sample',
            evidenceLevel: 'curated_sample',
            url: null
          }
        ]
      },
      {
        id: 'uz',
        countryKo: '우즈베키스탄',
        countryEn: 'Uzbekistan',
        iso2: 'UZ',
        iso2Verified: true,
        posts: [
          {
            nameKo: '주우즈베키스탄 대한민국 대사관',
            cityKo: '타슈켄트',
            typeKo: '대사관',
            officialSiteUrl: 'https://overseas.mofa.go.kr/uz-ko/index.do',
            urlVerification: 'search_index_corroborated',
            contactNoteKo:
              '전화번호·주소는 샘플에 수록하지 않았습니다. 공관 공식 홈페이지 또는 공공데이터 API 응답에서 확인해 주세요. 공식 원문 확인 필요.'
          }
        ],
        entryPrecheck: {
          statusKo: '공식 원문 확인 필요',
          summaryKo:
            '일반여권 소지자의 대한민국 입국 사증 면제 여부는 이 MVP에서 원문 확인이 완료되지 않았습니다. 외교부 사증 면제협정 체결현황 자료와 관할 공관 공지에서 확인해 주세요.',
          checkPointsKo: [
            '외교부 사증 면제협정 체결현황 원문에서 우즈베키스탄 항목 확인',
            '관할 재외공관(주우즈베키스탄 대사관) 공지 확인'
          ]
        },
        safety: {
          statusKo: '샘플 미수록',
          summaryKo:
            '국가별 안전정보·여행경보는 외교부 공공데이터로 제공됩니다. 이 MVP 샘플에는 실시간 안전정보를 수록하지 않았습니다. 공식 원문 확인 필요.'
        },
        missionNotices: [
          {
            country: '우즈베키스탄',
            post: '주우즈베키스탄 대한민국 대사관',
            title: '사증 안내 게시판',
            url: 'https://overseas.mofa.go.kr/uz-ko/brd/m_8550/list.do',
            fetchedAt: null,
            language: 'ko',
            textSnippet: '공식 원문 확인 필요 — 게시판 경로는 검색 색인에서 확인되었고, 본문은 아직 수집되지 않았습니다.',
            sourceType: 'overseas_mofa_public_web',
            evidenceLevel: 'official_public_web',
            extractionStatus: 'curated_reference_pending_fetch'
          },
          {
            country: '우즈베키스탄',
            post: '주우즈베키스탄 대한민국 대사관',
            title: '[주요 안내] 각 비자 신청 종류별 구비서류 안내',
            url: 'https://overseas.mofa.go.kr/uz-ko/brd/m_8550/view.do?seq=1281058',
            fetchedAt: null,
            language: 'ko',
            textSnippet:
              '공식 원문 확인 필요 — 게시글 제목은 검색 색인 기준입니다. 본문·서류 목록은 이 샘플에 수록하지 않았으며, 완전한 공식 체크리스트가 아닙니다.',
            sourceType: 'overseas_mofa_public_web',
            evidenceLevel: 'official_public_web',
            extractionStatus: 'curated_reference_pending_fetch'
          }
        ],
        sources: [
          {
            titleKo: '외교부_국가·지역별 재외공관 정보 (공공데이터포털 OpenAPI)',
            sourceType: 'mofa_public_data_portal_api',
            evidenceLevel: 'official_reference_confirmed',
            url: 'https://www.data.go.kr/data/15075354/openapi.do'
          },
          {
            titleKo: '외교부_국가별 사증 면제협정 체결현황 (공공데이터포털 파일데이터)',
            sourceType: 'mofa_public_data_portal_file',
            evidenceLevel: 'official_reference_partial',
            url: 'https://www.data.go.kr/data/15099235/fileData.do'
          },
          {
            titleKo: '주우즈베키스탄 대사관 공식 홈페이지 공개 게시판',
            sourceType: 'overseas_mofa_public_web',
            evidenceLevel: 'official_public_web',
            url: 'https://overseas.mofa.go.kr/uz-ko/index.do'
          },
          {
            titleKo: '사증발급 안내매뉴얼 2026.6 (법무부) — 매뉴얼 기준 참고 레이어',
            sourceType: 'uploaded_visa_issuance_manual_hwp',
            evidenceLevel: 'manual_reference',
            url: null
          },
          {
            titleKo: 'PreView 로컬 MVP 샘플 데이터',
            sourceType: 'curated_mvp_sample',
            evidenceLevel: 'curated_sample',
            url: null
          }
        ]
      }
    ]
  };

  if (typeof globalThis !== 'undefined') globalThis.PREVIEW_FALLBACK_DATA = DATA;
  if (typeof window !== 'undefined') window.PREVIEW_FALLBACK_DATA = DATA;
})();
