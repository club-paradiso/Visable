# Re:Scene MVP Execution Plan

## Status

- Project: Re:Scene by Club Paradiso
- Stage: Phase 0 discovery and concierge validation
- Decision: Conditional GO
- Rule: Do not begin a full production build until the validation gates below are met.

## 1. Product thesis to test

Creators and small production teams will pay for a tool that turns authorized video into an editable, time-synced screenplay and production breakdown, because it saves substantially more time than ordinary transcription and produces assets they can actually reuse for remakes, localization, pitching, thumbnails, and generative-video workflows.

## 2. Phase 0 deliverables

### A. Landing-page prototype

Required sections:

1. Hero: upload a video or paste an authorized YouTube URL.
2. Three output previews:
   - screenplay;
   - production breakdown;
   - creator prompt pack.
3. Rights and privacy explanation.
4. Before-and-after sample.
5. Pricing hypothesis.
6. Waitlist and interview application.

The landing page must not claim universal video downloading, perfect transcription, or official screenplay recovery.

### B. Clickable product prototype

Required screens:

1. Project dashboard.
2. Source selection.
3. Rights confirmation.
4. Processing stages.
5. Synchronized review workspace.
6. Export drawer.
7. Creator-pack panel.

### C. Concierge workflow

Manually process three to five real user videos using the proposed pipeline. Record:

- video duration;
- processing cost;
- total turnaround time;
- number of scenes;
- transcript correction time;
- screenplay correction time;
- retained generated content;
- user satisfaction;
- willingness to pay.

## 3. Validation interviews

Recruit:

- three independent filmmakers or film students;
- three YouTube creators or editors;
- two AI-video creators;
- two agency, localization, or archive users.

Interview questions must focus on past behavior rather than compliments:

1. When did you last reconstruct a script or shot list from finished video?
2. What did you produce and how long did it take?
3. Which part was most annoying or expensive?
4. What did you use instead?
5. Which output would you actually export?
6. Which errors would make the tool unusable?
7. Would you upload private footage? Under what retention terms?
8. What did you pay for adjacent tools during the last year?
9. Would you pay for this exact sample result today?

## 4. Phase 0 acceptance gates

Proceed to coded MVP only when all conditions are met:

- at least 10 qualified interviews completed;
- at least 6 users report a recurring or expensive version of the problem;
- at least 3 users provide rights-cleared footage;
- concierge processing reduces manual reconstruction time by at least 50 percent;
- users retain at least 70 percent of generated scene structure after edits;
- at least 2 users commit to a paid pilot or make a refundable deposit;
- no unresolved ingestion approach depends on unofficial YouTube downloading.

## 5. MVP feature order

### P0: indispensable

1. Authentication and project ownership.
2. Direct video upload.
3. Public YouTube URL analysis through an officially supported multimodal input path.
4. Rights mode selection:
   - owned;
   - licensed;
   - analysis only.
5. Asynchronous processing jobs.
6. Scene-boundary timeline.
7. Dialogue transcription and provisional speaker labels.
8. Structured scene JSON.
9. Synchronized screenplay editor.
10. Timestamp and confidence provenance.
11. Fountain, PDF, JSON, CSV, SRT, and VTT export.
12. User deletion and retention controls.
13. Text-only thumbnail and generative-video prompt packs.

### P1: useful after core quality

1. Existing SRT/VTT/script grounding upload.
2. Character registry with global rename.
3. Scene merge and split.
4. Creator presets.
5. Team comments.
6. Channel OAuth for creator-owned YouTube assets.
7. Usage metering and credit billing.

### P2: deliberately postponed

1. FDX and DOCX export.
2. Generated storyboard frames.
3. Direct image or video generation.
4. StudioBinder and editing-suite integrations.
5. Batch channels and enterprise workspaces.
6. Support for additional public video platforms.

## 6. Recommended repository shape

```text
apps/
  web/                 # Next.js application
  worker/              # media and AI orchestration worker
packages/
  db/                  # schema, migrations, RLS policies
  screenplay/          # scene schema, Fountain/PDF exporters
  media/               # FFmpeg and scene-detection adapters
  ai/                  # multimodal, STT, reasoning, image-prompt adapters
  ui/                  # shared Club Paradiso components
  observability/       # logs, traces, usage and cost events
docs/
  club-paradiso/rescene/
```

A separate app or monorepo workspace is preferable to dumping this into the existing immigration product surface. Shared Club Paradiso brand primitives may be reused, but product code and data boundaries must remain independent.

## 7. Proposed implementation stack

- Web: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui
- Database and auth: Supabase PostgreSQL, Auth, and row-level security
- Object storage: Cloudflare R2 or S3-compatible storage
- Background jobs: Trigger.dev, Inngest, or Railway worker with Redis queue
- Uploaded-media processing: FFmpeg and PySceneDetect
- AI layer: provider adapters rather than hard-coded model calls
- Deployment: Vercel for web; Railway or Cloud Run for workers
- Monitoring: Sentry plus structured job and cost events

## 8. Model-routing policy

### Draft pass

Use a fast multimodal model at low video resolution for:

- scene indexing;
- rough character and location detection;
- action-beat extraction;
- preliminary shot and sound metadata.

### Precision pass

Use dedicated speech-to-text and diarization where required, then reprocess only low-confidence scenes at higher resolution. A stronger reasoning model assembles the final screenplay and runs continuity checks.

### Prompt pack

Use a text model with model-specific templates. Store:

- target model;
- requested duration and aspect ratio;
- shot and camera language;
- lighting and style;
- dialogue and audio requirements;
- continuity references;
- negative constraints;
- prompt version.

### Development-model instruction

For implementation agents:

- Primary coding model: GPT-5.6 Thinking, high reasoning, for architecture, schema, security review, and multi-file implementation.
- Fast auxiliary model: a current low-cost coding model for repetitive tests, fixtures, and documentation only.
- Multimodal production models must remain configurable through environment variables and provider adapters.

## 9. Core data entities

- users
- workspaces
- projects
- media_sources
- processing_jobs
- media_segments
- characters
- scenes
- dialogue_lines
- action_beats
- production_elements
- prompt_packs
- exports
- usage_events
- consent_records
- deletion_requests

Every generated content row must retain source timestamps, confidence, model/version, and whether it was observed, transcribed, inferred, or user-edited.

## 10. Security and privacy requirements

- signed upload URLs;
- private buckets by default;
- row-level access controls;
- encryption in transit and at rest;
- configurable automatic deletion;
- explicit consent records;
- separate opt-in for any model-improvement use;
- redaction of secrets and personal identifiers from logs;
- no public project URLs unless the owner enables sharing;
- workers must delete temporary media and extracted frames after job completion.

## 11. Initial quality test set

Use rights-cleared clips covering:

1. two-person dialogue in a quiet room;
2. overlapping speakers;
3. fast-cut action;
4. music and little dialogue;
5. multiple languages;
6. off-screen dialogue;
7. captions that differ from spoken dialogue;
8. dark or low-resolution footage;
9. documentary interview;
10. vertical creator video.

Track scene-boundary precision, word error rate, speaker attribution, screenplay retention, hallucinated actions, and end-to-end cost per minute.

## 12. First coded milestone

The first coded milestone is complete only when a user can:

1. create a project;
2. upload a five-minute rights-cleared clip;
3. see processing progress;
4. receive scene boundaries and a synchronized screenplay draft;
5. correct a character name once and propagate it;
6. inspect timestamps and confidence;
7. export Fountain and JSON;
8. delete the project and all media.

Thumbnail prompts and video prompts may follow in the same milestone only after the screenplay pipeline meets the quality floor. Decorative AI confetti is not a substitute for a reliable core workflow.

## 13. Immediate backlog

- [ ] Finalize name and conduct trademark/domain screening.
- [ ] Create landing-page copy and information architecture.
- [ ] Build clickable Figma prototype.
- [ ] Prepare two rights-cleared demo clips.
- [ ] Define scene JSON schema with validation.
- [ ] Build a local five-minute pipeline spike.
- [ ] Compare multimodal-only versus STT-plus-multimodal accuracy.
- [ ] Measure per-minute cost and latency.
- [ ] Draft terms, privacy, rights attestation, and retention language.
- [ ] Recruit ten validation interviewees.
- [ ] Run three concierge projects.
- [ ] Decide GO, PIVOT, or STOP using the acceptance gates.
