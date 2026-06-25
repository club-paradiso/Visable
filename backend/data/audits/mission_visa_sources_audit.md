# Mission Visa Sources Audit

## Scope
- Date: 2026-06-25
- Task: official-source retry for Paradiso visa/stay guidance.
- Mission/embassy web enrichment: not attempted beyond the HiKorea official notice and attachments.

## Result
- Global mission coverage was not claimed.
- No embassy or consulate-specific requirements were added to canonical data.
- No mission-specific document requirements were treated as universal.
- No processing-time or appointment guidance was updated.

## Reason
- Core acquisition and readability work found the 260623 stay manual and 260623 change log to be unreadable distribution/protected HWPX packages.
- The task priority was to avoid source-mixing and avoid introducing unsupported legal or document claims.
- Mission-specific enrichment would be a separate audit after readable national manual text is available.

## Follow-up
- If a later PR performs mission enrichment, label every source as mission-specific.
- Recommended first pass: official MOFA/embassy pages for US, Japan, China, Vietnam, Philippines, Nepal, Thailand, Canada, Australia, and UK missions.
- Do not promote any mission-specific requirement into national checklist fields without explicit national-manual support.
