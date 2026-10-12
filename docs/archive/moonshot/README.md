# Moonshot historical archive

Audit snapshot: 2026-10-12. **Visable is the canonical active project.**
Moonshot is retained for provenance and recovery, not as a supported application
or a current source of immigration requirements.

## Status update: 2026-10-12 (after the initial audit)

This section records what changed after the initial audit snapshot. The
sections below it are kept as written at that snapshot; where they say
**BLOCKED** for the tag, this update supersedes them.

| Item | Result | Evidence |
| --- | --- | --- |
| Historical tag published | **PASS** | [`archive/moonshot-2026-05-06`](https://github.com/club-paradiso/Visable/tree/archive/moonshot-2026-05-06) pushed by the owner's authenticated `gh`/Git session as a new tag (no force, no overwrite) |
| Tag object type | **PASS** | Annotated (`tag` object), tagger `club-paradiso` |
| Peeled commit | **PASS** | `686ee3e87e04ee1afefe3d0d9a302c5fd2f81b49`, re-fetched into a fresh empty repository |
| Original `main` history reachable from the tag | **PASS** | 471 commits; `git fsck --full` clean |
| Historical tree kept out of Visable `main` | **PASS** | The source commit is not an ancestor of Visable `main` (`283983fcbb9b43b80c1c9ce110785981b2b96f04`) |
| Moonshot `main` unchanged since the audit | **PASS** | Still `686ee3e…`; 32 branches, 110 PR refs, 0 tags |
| Persisted backup (`fb43f0d8…`) re-accessed | **NOT RUN** | Not reachable from the follow-up session; still held privately by the owner |
| Independent re-verification of full history | **PASS** | A new mirror bundle (47,793,571 bytes, SHA-256 `038d8f00d793219027a162a30f90eea07e0ecbf7f5bd7348f7231eff2ce3132c`) passed `git bundle verify`, restored to a mirror with identical refs and object IDs, passed `git fsck --full`, and matched [`refs.tsv`](./refs.tsv) line for line. That regenerated file was **not persisted**; the owner's original bundle remains the backup of record |
| Moonshot archived | **No** | `archived: false` |

Tag scope: the tag preserves Moonshot `main` only. The 32 branches (including
the unmerged `feat/postgres-migration`) and 110 PR refs are preserved by the
full-history bundle, not by this tag.

Tag pushes do not trigger Visable automation: no workflow has a `tags:`
trigger, Railway deploys from `main`, and Vercel deploys from branches.

### GitHub administration audit of `club-paradiso/moonshot`

Checked with the owner's authenticated `gh` session (admin permission on both
repositories). Secrets and full URLs were not recorded.

| Check | Result |
| --- | --- |
| Repository webhooks | 0 |
| Deploy keys | 0 |
| GitHub Actions workflows | 1: GitHub-managed `pages build and deployment` (last run 2026-09-03); no workflow files on `main` |
| GitHub Pages | **Enabled** |
| Deployment environments | 2 (names not yet recorded) |
| Installed GitHub Apps | **BLOCKED**: the token lacked the `admin:org` scope |
| Railway sources | None of the 4 Railway projects use Moonshot (Visable backend: `club-paradiso/Visable`, `main`, `/backend`) |
| Vercel projects | None linked to the Moonshot repository |
| Last push to Moonshot | 2026-05-06 |

No write dependency on Moonshot was found among the items that could be
checked. The audit is still **incomplete**: the GitHub App inventory is
unchecked, and the owner has not yet decided whether the Moonshot Pages site
should stay published. Current Visable runtime code does not reference a
`github.io` origin; only dated audit documents mention the former
`lucanomics.github.io/Paradiso/` address.

### Remaining before archiving Moonshot

1. List the organization's GitHub App installations
   (`gh auth refresh -s admin:org`) and confirm that none needs write access
   to Moonshot.
2. Decide what to do with the Moonshot GitHub Pages site and its two
   environments. They serve outdated April 2026 immigration content.
3. Confirm that no essential work remains only on `feat/postgres-migration`.
   It is preserved in the bundle and in `refs.tsv`.
4. Get the owner's separate approval to archive. Never delete, rename,
   transfer, or change the visibility of the repository.

## Provenance and timeline

- Original repository: <https://github.com/club-paradiso/moonshot>.
- First Moonshot `main` commit: `69ca5364b15bd727a13c97d94ed9b2097db22320`,
  2026-04-13 11:05:27 +09:00 (`Create index.html`).
- Final observed Moonshot `main` commit:
  [`686ee3e87e04ee1afefe3d0d9a302c5fd2f81b49`](https://github.com/club-paradiso/moonshot/commit/686ee3e87e04ee1afefe3d0d9a302c5fd2f81b49),
  2026-05-06 17:17:05 +09:00 (merge of PR #110).
- Visable's independent Git history starts on 2026-05-06. Commit
  `816f3c5018cc852929cbd3a96a38f4361f6eb7b5` explicitly records
  `Migrate working Paradiso app from moonshot` on that date.
- Moonshot → Paradiso → Visable describes the product lineage, not a claim
  that all three histories already form one continuous Git ancestry.
- Destination baseline inspected:
  `0ee47d3212d180056e7b6f3d35f9fb2e70fb066a`.

Moonshot combined a static visa explorer and AI page with a FastAPI backend,
PostgreSQL schemas, a source-registry crawler, PDF extraction, and a proposed
Supabase/pgvector retrieval pipeline. Some files were scaffolds or outdated
specifications; their presence does not establish production use.

## Historical reference and publication status

The exact source commit above is the immediately available historical reference.
The proposed **annotated** destination tag is `archive/moonshot-2026-05-06`,
pointing to that same original commit, without merging its tree into `main`.

At this audit snapshot the tag was created and verified locally, but its GitHub
publication was **BLOCKED**: the Git CLI had no push credentials, and the
available connector could create commits/branches but could not import the
original object graph or create annotated tags. **Do not assume the tag exists
on Visable's remote.** No archival application branch was published.
*(Superseded: the tag was later published and verified. See the status update
above.)*

An authenticated maintainer can publish the historical reference independently
of the documentation PR:

```bash
git clone https://github.com/club-paradiso/Visable.git Visable-archive
cd Visable-archive
git fetch https://github.com/club-paradiso/moonshot.git main
git cat-file -t 686ee3e87e04ee1afefe3d0d9a302c5fd2f81b49
git tag -a archive/moonshot-2026-05-06 \
  686ee3e87e04ee1afefe3d0d9a302c5fd2f81b49 \
  -m 'Historical Moonshot main snapshot; not an active deployment branch'
git push origin refs/tags/archive/moonshot-2026-05-06
git ls-remote origin 'refs/tags/archive/moonshot-2026-05-06*'
```

If that tag already exists, inspect its peeled commit before proceeding; do not
overwrite it. Revalidate workflow/deployment tag triggers before publication.
The inspected Visable workflows had no tag or release triggers.

## Full-history backup

The owner has a persisted private backup named
`moonshot-history-2026-10-12.bundle`, with companion checksum
`moonshot-history-2026-10-12.bundle.sha256` and ref manifest
`moonshot-refs-2026-10-12.tsv`, in their ChatGPT files. Ask the repository owner
for these artifacts. They are not assets in the application's static tree.

The backup was saved, retrieved from storage into a separate directory, and
independently restored and verified. A public GitHub Release was **not created**:
the available connector did not support Release creation/binary attachment and
the local Git environment had no authenticated write access.

| Property | Verified value |
| --- | --- |
| Bundle bytes | 47,777,400 |
| SHA-256 | `fb43f0d8e1ab67fe8b2b02b943121d76bd826b97232669c35f26cde3eb3ce595` |
| Source branch refs | 32 |
| Source tag refs | 0 |
| PR Git refs | 110 |
| Named refs in source/restored mirror | 142 |
| Bundle records | 143, including symbolic `HEAD` |
| Reachable commits across all refs | 474 |
| Commits reachable from `main` | 471 |
| Branches fully merged into `main` | 31 |
| Unmerged branch | `feat/postgres-migration` (preserved) |
| LFS pointer blobs detected | 0 |
| Open issues / PRs at audit snapshot | 0 / 0 |
| Releases at audit snapshot | 0 |

The full [ref manifest](./refs.tsv) records the SHA of every branch and PR ref.
All source refs matched the remote advertisement and both independent restores.
All reachable Git object IDs matched the first restore. `git bundle verify` and
`git fsck --full` passed; the persisted artifact's checksum and restored refs
were also verified.

Git bundles do **not** back up issue/PR discussions, settings, permissions,
webhooks, Actions run artifacts, secrets, external databases, or LFS object
payloads. The 110 PR refs preserve Git commits, not the 110 discussions.
The original GitHub repository remains the record for that metadata; it must
not be deleted or transferred as part of this operation.

## Restore source without touching production

Obtain the three backup files from the owner, then work in an empty directory:

```bash
sha256sum -c moonshot-history-2026-10-12.bundle.sha256
git init --bare verify.git
git -C verify.git bundle verify ../moonshot-history-2026-10-12.bundle
git clone --mirror moonshot-history-2026-10-12.bundle moonshot-restored.git
git --git-dir=moonshot-restored.git fsck --full
git --git-dir=moonshot-restored.git for-each-ref \
  --format='%(objectname)%09%(refname)' > restored-refs.tsv
diff -u moonshot-refs-2026-10-12.tsv restored-refs.tsv
git clone moonshot-restored.git moonshot-inspect
git -C moonshot-inspect checkout 686ee3e87e04ee1afefe3d0d9a302c5fd2f81b49
```

Restoring files is not authorization to run crawlers, apply SQL, reset vector
indexes, contact model providers, or deploy the legacy app. Original branch
names may contain shell metacharacters; quote them when checking out a branch.

## Component crosswalk against current Visable

Classes: **1** implemented; **2** superseded; **3** historical;
**4** missing capability worth a future evaluation; **5** obsolete/unsafe to
reintroduce. Classification describes inspected code, not full feature parity
or a blanket claim that every production path works.

| Moonshot evidence | Current Visable evidence | Class and disposition |
| --- | --- | --- |
| `index.html`, `ai.html`, `data/jobcode_master.json` | `index.html`, `ai.html`, `assets/js/unified-search.js`, employment helper | 1/2: active equivalents; keep current implementations |
| `visa_data.json`, `doc_master.json`, `moonshot/visa_data (1).json` | Root canonical files and `backend/data/` deploy mirrors | 2/5: historical records are not current legal data; never overwrite canonical files |
| `moonshot_backend_fastapi.py` | `backend/paradiso_backend.py`, `backend/services/ai_runtime.py`, `model_policy.py` | 2: current API and guarded provider routing supersede the legacy monolith |
| `scripts/rag/extract_pdf.py`, `index_manuals.py`, `migrations/002_rag_pgvector.sql` | `scripts/build_manual_search_index.py`, `backend/services/manual_search.py`, `backend/services/knowledge/` | 2/4: SQLite FTS/BM25 and review-aware knowledge replace the old path; a pgvector vector-search implementation is absent and would need a new justified proposal |
| `migrations/001_schema.sql`, `moonshot/moonshot_schema.sql`, `feat/postgres-migration` | `backend/services/knowledge/store.py` (SQLite), protected JSON data | 3/4: preserve unapplied/unmerged SQL; inspect separately if a PostgreSQL migration is ever justified |
| Public-data and law calls in `moonshot_backend_fastapi.py` | `public_data_client.py`, `korean_law_client.py`, `law_grounding.py` | 1/2: current clients exist; no need to copy old endpoints |
| `moonshot_crawler.py`, `seed_registry_insert.sql` | `scripts/check_source_updates.py`, `data/source_registry.json`, manual monitors | 2/3: current monitoring replaces the legacy crawler; no automatic old SQL/crawler execution |
| Legacy language detection and response disclaimers | `backend/safety_guardrails.py`, `services/answer_quality.py`, current AI/UI warnings | 1/2: current language and safety handling exist |
| April PDF manuals (13.2 MB and 14.8 MB), extracted Markdown, design ZIP (10.8 MB) | Current manual corpus and registry; existing `docs/archive/` | 3: preserved in Git backup only, not duplicated in runtime paths |
| `server.log`, `moonshot/__pycache__/...pyc`, old admin UI and branding | Current source, tests, and design system | 3/5: historical Git retention only; no runtime copying |

Classes 4 are candidate capabilities, not approved migration tasks. No component
was restored or modernized in this archival change.

## Prior audits and what changed

- [May migration gap audit](../../MOONSHOT_TO_PARADISO_MIGRATION_GAP_AUDIT.md).
- [Remaining migration phase plan](../../MOONSHOT_TO_PARADISO_REMAINING_MIGRATION_AUDIT.md).
- [Current architecture](../../ARCHITECTURE.md).

The May audits use former `lucanomics/moonshot` and `lucanomics/Paradiso` names.
The remaining-migration audit explicitly lacked source access. They are dated
evidence, not the current runtime inventory. Their claims of missing law/public
data clients, missing provider fallback, and an undeployed current backend are
superseded by inspected current code and live health/OpenAPI evidence.
The old pgvector scripts/schema remain absent by design of the current path;
their absence alone is not evidence that all manual retrieval is broken.

## Deployment dependency audit and exposure

- Railway `delightful-flow/web` source is `club-paradiso/Visable`, `main`,
  root `/backend`; latest observed deployment status was `SUCCESS`.
- Railway's displayed start command still names `moonshot_backend_fastapi:app`.
  That file in current Git is a small separate app, while
  `backend/railway.json` and `backend/Procfile` select `paradiso_backend:app`.
  Live `/health` and `/openapi.json` showed the current Paradiso Backend and
  build `0ee47d3212d180056e7b6f3d35f9fb2e70fb066a`, including current
  search/enforcement/knowledge routes. This is a configuration-display/runtime
  discrepancy, **not a demonstrated outage**. Its precise cause was not proven.
  No deployment settings were changed.
- No Railway webhook was configured in the inspected project. Other accessible
  Railway application sources were tapso, asad, and print-cess, not Moonshot.
- Vercel's production deployment identified `club-paradiso/Visable`, `main`,
  the same baseline SHA, and status `READY`. A team project query filtered to
  the Moonshot repository returned no projects.
- Moonshot `main` had no `.github/workflows/` files. Visable's scheduled
  monitors belong to Visable and were preserved.
- GitHub repository webhook/App/settings inventory was **BLOCKED** by the
  connector's administration limitations and an unsigned browser session.
  Other external integrations cannot be ruled out from repository code alone.
  This must be checked before final read-only archival.
- A live GET of `/docs/ARCHITECTURE.md` returned HTTP 200. Treat `docs/` as public.
  This folder contains curated text/refs only, with no legacy executable app,
  manuals, database snapshots, logs, environment files, or bundle binary.

## Security, data, and legal caveats

A custom bounded pattern scan inspected all 372 reachable blob versions
(84,204,839 bytes), including 10 binary blobs. Four detections were reviewed as
generic `.env.example` database URI examples or Korean instructional key
placeholders; no confirmed credentials were found. This is **not** a complete
secret or personal-data certification: entropy/semantic scanning and decoding
compressed archives or embedded PDF/image text were not performed.

Historical April immigration manuals, extracted text, code, and data can be
outdated or wrong. Restore for research only. Preserve procedure boundaries,
subcode distinctions, source dates, and review warnings. Visable's protected
canonical data files, API implementations, schemas, workflows, and production
configuration were not edited by this documentation change.

## Maintenance and final archival gate

Preserve this as a dated historical record. Do not maintain a second active
Moonshot app or rewrite its history. Update publication status with actual
remote evidence when the tag is published; never replace original SHAs with
newly manufactured history.

Before requesting approval to archive the original GitHub repository:

1. Publish/verify the destination historical tag and confirm backup access.
2. Resolve/check any essential work from the preserved unmerged branch.
3. Inspect GitHub webhooks and installed integrations for write dependencies.
4. Merge the reviewed documentation PR only with the owner's explicit approval.
5. Verify the merged record and then obtain separate approval to archive Moonshot.

At the initial snapshot, the backup was complete; the documentation PR and tag
publication/merge were separate steps; Moonshot remained **unarchived**.
Reverting the eventual documentation commit rolls back the in-tree record
without changing active code/data or the source repository. Restoring source
from the bundle remains independent of that revert.
