# Re:Scene Multimodal Scope Addendum

## Decision

Re:Scene should expand from a video-first reverse pre-production tool into a **media-to-production-asset workspace** with three first-class source types:

- Video
- Image
- Text or screenplay

This is an expansion of the same product thesis, not a collection of unrelated AI tools. Every source is converted into structured production knowledge and executable creative assets.

## Unified product statement

**Re:Scene turns videos, images, and scripts into editable screenplays, production breakdowns, thumbnails, and model-ready image or video prompts.**

## Why image input belongs in the product

A single image already contains information creators repeatedly need to reconstruct by hand:

- subject and pose;
- composition and visual hierarchy;
- camera viewpoint and lens character;
- lighting and palette;
- materials, textures, and environment;
- typography;
- thumbnail logic;
- plausible motion for image-to-video generation.

The useful product is not a generic image captioner. It is a visual reverse-engineering tool that exposes both a faithful reconstruction prompt and editable production controls.

## Image output contract

Every image analysis should produce:

1. Visual Evidence Map
   - directly visible facts;
   - ambiguous details;
   - unsupported or hidden facts that must not be invented.
2. Faithful reconstruction prompt.
3. Editable parameter breakdown.
4. Negative constraints.
5. Model-specific prompt variants.
6. Optional thumbnail adaptations.
7. Optional image-to-video motion plan.
8. Confidence and inference notes.

## Product information architecture

### Create project

Choose a source:

- Video
- Image
- Script or text

Then choose a goal:

- Reconstruct
- Analyze
- Adapt
- Generate prompt pack
- Build full creator pack

### Shared workspace concepts

All source types should share:

- source viewer;
- evidence and inference labels;
- editable extracted elements;
- prompt versions;
- project history;
- exports;
- rights and privacy controls.

### Source-specific workspace

#### Video

- synchronized player;
- scene timeline;
- screenplay editor;
- timestamp provenance.

#### Image

- image canvas;
- selectable regions;
- visual evidence panel;
- prompt controls;
- comparison gallery.

#### Script or text

- beat and scene editor;
- shot-list panel;
- continuity registry;
- visual prompt board.

## MVP priority revision

### P0

- direct video upload;
- direct image upload;
- public YouTube URL analysis through an officially supported input path;
- rights mode;
- source classification;
- video scene JSON;
- image evidence JSON;
- text-only prompt packs;
- project deletion and retention controls.

### P1

- synchronized screenplay editor;
- image prompt editor with reusable controls;
- model-specific image prompts;
- image-to-video prompts;
- thumbnail analysis and adaptations;
- Fountain, PDF, JSON, CSV, SRT, and VTT exports where relevant.

### P2

- direct image generation;
- direct video generation;
- visual region selection;
- side-by-side prompt-result evaluation;
- persistent character and style reference libraries;
- storyboard generation.

## Data model additions

Add or generalize these entities:

- `source_assets`
  - `type`: video, image, text
  - `rights_mode`
  - `mime_type`
  - `duration_ms` where applicable
- `observations`
  - source region or timestamp
  - observation type
  - confidence
  - provenance
- `visual_elements`
  - subject
  - composition
  - lighting
  - palette
  - camera
  - typography
  - material
- `prompt_variants`
  - target model
  - prompt type
  - version
  - settings
  - negative constraints
- `continuity_rules`
  - character
  - wardrobe
  - prop
  - location
  - lighting
  - immovable elements

## Validation gates for image mode

Before building direct image-generation integrations, validate that:

- users prefer the structured prompt over a generic one-paragraph caption;
- at least 70 percent of visible facts survive user correction;
- users can meaningfully edit the decomposed controls;
- model-specific variants produce visibly different and useful behavior;
- image-to-video prompts preserve subject identity and composition better than an unstructured baseline;
- users understand which details are observed versus inferred.

## Brand architecture

Re:Scene should remain the umbrella product. Suggested internal feature names:

- Re:Scene Script
- Re:Scene Breakdown
- Re:Scene Prompt
- Re:Scene Thumbnail
- Re:Scene Motion

Avoid separate microbrands for every button. The world has suffered enough from founders naming six tabs as though they were independent companies.

## Phase sequence

1. Gemini Gem pilot for video, image, and text.
2. Collect corrected outputs and scorecards.
3. Lock the JSON contracts.
4. Build the source upload and project shell.
5. Implement image mode first as the cheapest end-to-end coded workflow.
6. Implement short-video mode with background jobs.
7. Add the synchronized screenplay editor.
8. Add paid generation providers only after prompt quality is validated.

Image mode is recommended as the first coded vertical slice because it avoids long-running media jobs, FFmpeg, diarization, and timestamp synchronization while still validating authentication, storage, AI orchestration, provenance, prompt editing, and export architecture.
