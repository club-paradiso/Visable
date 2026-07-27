# Re:Scene by Club Paradiso

> Working title. Final naming and trademark review are pending.

## 1. Executive verdict

**Proceed as a focused MVP.**

The viable product is not a generic transcript generator and not an unrestricted “paste any copyrighted film and download its screenplay” service. Re:Scene should be positioned as a **reverse pre-production workspace** that converts user-owned, licensed, or otherwise authorized video into:

1. a time-synced professional screenplay draft;
2. a scene and shot breakdown;
3. editable character, location, prop, sound, and camera metadata;
4. model-specific thumbnail and generative-video prompt packs;
5. exportable production documents.

The strongest wedge is the conversion of **already-produced video back into reusable production structure**. Existing tools usually stop at transcription, transcript-based editing, or script-to-video. Re:Scene should own the opposite direction: **video to production-ready narrative assets**.

## 2. Why this is worth building

### Market gap

Current products are fragmented:

- Descript, VEED, Kapwing, and Happy Scribe mainly turn audio/video into editable transcripts, captions, and repurposed content.
- StudioBinder and Fountain handle professional screenplay writing and formatting.
- LTX Studio and Runway move from scripts or prompts toward storyboards and generated video.
- Canva and Adobe Express generate thumbnails.

The missing integrated workflow is:

`video source -> multimodal scene understanding -> editable screenplay -> production breakdown -> thumbnail/video prompt pack`

Recent research also treats long-form cinematic video-to-script generation as a distinct and still difficult task, which supports both the technical novelty and the need for careful human review rather than magical one-click claims.

### Best initial users

1. **Independent filmmakers and AI filmmakers** recreating, localizing, studying, or continuing their own footage.
2. **YouTube creators and production agencies** converting finished videos into repeatable content templates, shot lists, and remake prompts.
3. **Film students, editors, and researchers** studying scene construction with authorized material.
4. **Localization and accessibility teams** turning source footage into structured dialogue and action documents.
5. **Archive and production teams** reconstructing missing or incomplete scripts from rights-cleared footage.

### Weak initial users

- casual users who only want subtitles;
- users seeking complete verbatim scripts of commercial films they do not own;
- users who expect frame-perfect action recognition from a single low-resolution pass;
- users wanting a full video editor in version 1.

## 3. Product positioning

### One-line description

**Re:Scene turns authorized video into an editable screenplay, production breakdown, and AI-ready creative prompt pack.**

### Category

- Primary: AI pre-production / reverse pre-production
- Secondary: video intelligence, screenwriting, creator workflow
- Not: generic transcription SaaS, video downloader, full nonlinear editor

### Product promise

“Understand what was made, reconstruct how it works, and prepare what comes next.”

## 4. Legal and platform boundary

This boundary is a product requirement, not a footer nobody reads.

### Supported ingestion modes

#### A. Direct upload

- MP4, MOV, WebM, AVI and other supported formats.
- User must confirm that they own the footage or have permission to process it.
- Full screenplay reconstruction is allowed within the service terms.

#### B. Cloud file import

- Google Drive, Dropbox, OneDrive, or direct object-storage links added later.
- Same rights attestation as direct upload.

#### C. YouTube creator connection

- Google OAuth.
- Prioritize videos owned or managed by the connected channel.
- Caption downloads through the YouTube Data API require authorization and permission to edit the video.

#### D. Public YouTube URL analysis

- Use an officially supported model input path, such as Gemini’s public YouTube URL understanding, without downloading or caching the audiovisual file.
- Default output should be limited to scene analysis, summaries, structural breakdowns, and short quoted excerpts.
- Full verbatim screenplay reconstruction requires rights confirmation.
- Do not use undocumented scraping or downloader libraries in production.

#### E. Other public video websites

- Do not promise universal URL support.
- Support only platforms with official APIs, embeddable media, direct user-authorized file access, or clearly permitted public endpoints.
- Otherwise ask the user to upload the file.

### Required safeguards

- rights attestation before processing;
- clear distinction between “transcribed dialogue” and “AI-inferred action”;
- confidence scores and uncertainty labels;
- deletion controls and retention limits;
- copyright complaint and takedown process;
- no model training on private footage without explicit separate consent;
- no YouTube media downloading, caching, audio extraction, or offline playback through unofficial methods.

## 5. MVP scope

### Input

- direct video upload;
- public YouTube URL through an officially supported multimodal API;
- optional SRT, VTT, TXT, or existing script upload as grounding material;
- language selection and optional character-name hints.

### Core processing

1. media validation and rights confirmation;
2. low-resolution first-pass video understanding;
3. dialogue transcription and speaker segmentation;
4. scene-boundary detection;
5. character, location, prop, action, sound, and camera-cue extraction;
6. structured scene JSON generation;
7. second-pass correction for low-confidence scenes;
8. screenplay assembly;
9. user review and correction.

### Output modes

#### Screenplay mode

- scene headings;
- action lines;
- character cues;
- dialogue;
- parentheticals where justified;
- sound and music cues;
- transitions only when visually meaningful;
- optional scene numbers and timestamps.

#### Breakdown mode

- scene list;
- cast and character list;
- locations;
- props and wardrobe;
- sound and music;
- shot size, camera movement, angle, and visual style;
- confidence and source timestamp for every extracted item.

#### Creator pack

- three thumbnail concepts;
- thumbnail copy and composition notes;
- image-generation prompts;
- YouTube title, description, chapters, tags, and short-form hooks;
- shot-by-shot prompts for selected video models;
- negative prompts, continuity notes, aspect ratio, duration, camera, lighting, lens, movement, and audio fields.

### Exports

MVP:

- Fountain;
- PDF;
- TXT and Markdown;
- JSON;
- CSV scene breakdown;
- SRT and VTT.

Later:

- FDX;
- DOCX;
- StudioBinder or other production-tool integrations;
- editable storyboard packages.

Fountain is the safest first professional screenplay interchange format because it is plain text, human-readable, and importable by major screenwriting applications.

## 6. User experience

### Main flow

1. **Create project**
2. **Choose source**: upload, YouTube URL, cloud import
3. **Confirm rights and privacy**
4. **Choose output**: screenplay, breakdown, creator pack, or all
5. **Processing dashboard** with visible stages
6. **Review workspace**
7. **Resolve uncertain characters and scenes**
8. **Export or generate creator assets**

### Review workspace layout

- Left: embedded or uploaded video player
- Center: screenplay editor synchronized to playback
- Right: scene metadata, confidence, characters, prompts, and warnings
- Bottom: scene timeline with boundaries and keyframes

Every generated sentence should be traceable to a timestamp or marked as inference. Otherwise the product becomes an eloquent hallucination machine, a market already generously oversupplied.

## 7. Technical architecture

### Recommended stack

- Frontend: Next.js, TypeScript, React, Tailwind, shadcn/ui
- Auth: Supabase Auth or Clerk
- Database: PostgreSQL with row-level security
- Object storage: Supabase Storage, Cloudflare R2, or S3-compatible storage
- Queue: Inngest, Trigger.dev, or a Redis-backed worker
- Media tools: FFmpeg and PySceneDetect for uploaded files only
- AI orchestration: provider adapter layer
- Deployment: Vercel for web, Railway or Cloud Run for workers

### Initial model routing

#### First pass

- Gemini 3.6 Flash or a current equivalent multimodal model
- low media resolution for scene indexing and rough metadata

#### Precision pass

- higher-resolution multimodal pass only for uncertain scenes;
- dedicated speech-to-text and diarization when dialogue accuracy matters;
- stronger reasoning model for final screenplay assembly and consistency checks.

#### Thumbnail and prompt generation

- text model generates composition briefs and model-specific prompts;
- image generation is optional in MVP and should sit behind a provider adapter;
- store the prompt, settings, seed/reference metadata, and generated result separately.

### Intermediate schema

The screenplay must be generated from a stable structured representation rather than directly from raw video.

```json
{
  "project_id": "uuid",
  "source": {
    "type": "upload|youtube|cloud",
    "rights_mode": "owned|licensed|analysis_only"
  },
  "characters": [],
  "scenes": [
    {
      "scene_id": "scene_001",
      "start_ms": 0,
      "end_ms": 25000,
      "heading": {
        "interior_exterior": "INT.",
        "location": "KITCHEN",
        "time_of_day": "NIGHT",
        "confidence": 0.82
      },
      "action_beats": [],
      "dialogue": [],
      "sound_cues": [],
      "camera_cues": [],
      "props": [],
      "uncertainties": []
    }
  ]
}
```

### Accuracy strategy

- combine audio and visual understanding;
- preserve original timestamps;
- never silently invent character names;
- use provisional labels such as MAN 1 until confirmed;
- compare transcript, subtitles, lip movement, visible speaker, and scene context;
- run continuity checks across scenes;
- expose confidence and let users correct the character registry once for global propagation.

## 8. Cost and performance assumptions

Gemini video understanding currently samples video at roughly 1 FPS and tokenizes approximately 300 input tokens per second at default resolution or 100 at low resolution. At current listed Gemini 3.6 Flash input pricing, a one-hour first pass is roughly USD 1.62 at default resolution or USD 0.54 at low resolution before output, storage, retries, speech services, and higher-quality verification passes.

A realistic internal target for an hour of uploaded video is therefore:

- low-cost draft: USD 1 to 3;
- production-quality multi-pass draft: USD 3 to 10;
- retail price must include storage, failed jobs, support, payment fees, and model-price volatility.

Do not offer unlimited long-form processing at launch. That is how founders discover that cloud providers have a better business model than they do.

## 9. Suggested pricing hypothesis

### Free

- one short project;
- up to 5 minutes;
- screenplay preview;
- watermark or limited export;
- no permanent storage.

### Creator

- KRW 14,900 to 24,900 per month;
- monthly processing credits;
- screenplay, creator pack, and standard exports.

### Studio

- KRW 59,000 to 129,000 per month;
- longer uploads;
- team review;
- batch projects;
- higher-quality passes;
- brand and prompt presets.

### Pay-as-you-go

- essential for long-form video;
- charge by processed minute and quality mode.

Pricing must be validated through landing-page tests and interviews before implementation of a complicated billing matrix.

## 10. Success metrics

### Activation

- user reaches first generated scene within one session;
- user exports or edits at least one scene;
- processing failure rate below 5 percent.

### Quality

- speaker attribution accuracy;
- scene-boundary precision;
- percentage of generated lines retained after user editing;
- time saved compared with manual reconstruction;
- confidence calibration, not merely average confidence.

### Retention

- second project created within 14 days;
- creator-pack export rate;
- percentage of projects reopened for revision.

## 11. Delivery phases

### Phase 0: validation

- clickable landing page and workflow prototype;
- five filmmaker interviews;
- five creator or agency interviews;
- three manually processed concierge projects;
- test willingness to pay.

### Phase 1: narrow MVP

- direct upload;
- public YouTube URL analysis mode;
- scene JSON;
- synchronized screenplay editor;
- Fountain, PDF, and JSON export;
- thumbnail and video prompt text generation;
- deletion and retention controls.

### Phase 2: creator workflow

- channel OAuth;
- title, chapter, and thumbnail workflows;
- reusable style and character presets;
- team review and comments;
- usage billing.

### Phase 3: production ecosystem

- FDX export;
- storyboard generation;
- production breakdown integrations;
- model-specific direct generation connectors;
- enterprise privacy and regional storage.

## 12. Explicit non-goals for MVP

- universal downloading from arbitrary video sites;
- full Final Cut, Premiere, or DaVinci replacement;
- perfect actor identification without user confirmation;
- automatic reconstruction of an entire commercial film for unauthorized distribution;
- training a custom foundation model;
- direct publishing to every social platform;
- fully automated generative-video rendering.

## 13. Go or no-go criteria

Proceed from Phase 0 to Phase 1 only if all are true:

1. at least 6 of 10 target users rate the problem as frequent and costly;
2. at least 3 users provide real footage for testing;
3. the concierge workflow saves at least 50 percent of manual reconstruction time;
4. users retain at least 70 percent of the generated scene structure after edits;
5. at least 2 users are willing to pay a stated amount rather than merely describing the idea as “interesting.”

## 14. Primary sources

- YouTube API caption download permissions: https://developers.google.com/youtube/v3/docs/captions/download
- YouTube API developer policies: https://developers.google.com/youtube/terms/developer-policies
- YouTube Terms of Service: https://www.youtube.com/static?template=terms
- Gemini video understanding: https://ai.google.dev/gemini-api/docs/video-understanding
- Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- Fountain screenplay format: https://fountain.io/
- StudioBinder screenwriting workflow: https://www.studiobinder.com/screenplay-generator/
- OmniScript research: https://arxiv.org/abs/2604.11102

## 15. Immediate decision

**Incubate Re:Scene as a Club Paradiso project, but build the first release around authorized footage, structured screenplay reconstruction, and human-verifiable outputs.**

The thumbnail and video-prompt features should be included as downstream outputs, not allowed to distract the MVP into becoming another bloated all-purpose AI video suite.