# 2026 HiKorea PDF Manual Source Identity Report

## Official Notice
- URL: https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&BBS_GB_CD=BS10&NTCCTT_SEQ=1062&page=1
- Notice title observed: 체류자격별 통합 안내 매뉴얼(최신)
- Attachments observed on the notice: `260617 사증민원 자격별 안내 매뉴얼.hwp`, `260623 체류민원 자격별 안내 매뉴얼.hwpx`, `260623 사증.체류 민원 자격별 안내 매뉴얼 수정 이력.hwpx`
- Production extraction route for this PR: user-provided readable desktop PDF exports of the official manuals, not the protected HWP/HWPX bodies.

## Visa Issuance Manual
- Domain: 입국 전 사증발급
- Original PDF filename: `260617 사증민원 자격별 안내 매뉴얼.pdf`
- Normalized PDF path: `backend/data/sources/manuals/260617_visa_manual_exported.pdf`
- Readable text path: `backend/data/sources/manuals/260617_visa_manual_readable.txt`
- Sections path: `backend/data/sources/manuals/260617_visa_manual_sections.json`
- SHA-256: `c54e3b739b54e19e64e2ea6ee5bc49228194b5f164b51efa6b461534561e9fd1`
- File size: 13,189,698 bytes
- File type: PDF document
- PDF metadata: 487 pages, unencrypted, A4, Creator `한컴오피스 한글 Viewer`, CreationDate `Thu Jun 25 23:48:48 2026 KST`
- Cover text sample from extraction: `사증발급 안내매뉴얼 ... 2026. 6. 법무부 출입국·외국인정책본부`
- Extracted text SHA-256: `c4fa08b49350fc672176760868d68237d063abe03290dd490c10a28f495f6653`
- Extracted text quality: 458,881 characters, 3,098 lines, Hangul ratio 0.5952

## Stay/Residence Manual
- Domain: 입국 후 체류민원, 체류기간 연장, 체류자격 변경, 외국인등록, 신고, 근무처 변경/추가
- Original PDF filename: `260623 체류민원 자격별 안내 매뉴얼.pdf`
- Normalized PDF path: `backend/data/sources/manuals/260623_stay_manual_exported.pdf`
- Readable text path: `backend/data/sources/manuals/260623_stay_manual_readable.txt`
- Sections path: `backend/data/sources/manuals/260623_stay_manual_sections.json`
- SHA-256: `00375f44b6245337813a5c36f53671f642b52c6006a65f1fcf3eb808f93fb51f`
- File size: 14,962,255 bytes
- File type: PDF document
- PDF metadata: 780 pages, unencrypted, A4, Creator `한컴오피스 한글 Viewer`, CreationDate `Thu Jun 25 23:47:44 2026 KST`
- Cover text sample from extraction: `외국인체류 안내매뉴얼 2026. 6. 법무부 출입국·외국인정책본부`
- Extracted text SHA-256: `18a754fe7aeba8f4701034b2818646ef631a8a7ea45d625996ad2b10ccef70da`
- Extracted text quality: 716,788 characters, 4,785 lines, Hangul ratio 0.5823

## Readability Result
- Visa manual: success. Full page-level text and status-code inventory were extracted from the readable PDF.
- Stay manual: success. Full page-level text and status-code inventory were extracted from the readable PDF.
- Change-log PDF: not provided or found in readable PDF form during this pass. The official notice lists a HWPX change-log attachment, but this PR does not use unreadable HWPX body bytes as production source text.
- HWP/HWPX diagnostic outputs from earlier work remain non-production evidence and were not used to change legal guidance.

