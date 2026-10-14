# App Flow — Tailr

**One CV. Every job.**

| Field | Value |
|---|---|
| Version | 0.1 (draft) |
| Companion documents | `PRD.md`, `technical_requirements.md` |
| Scope | Screen inventory, navigation model, per-page specification, states and edge cases |
| UI languages | Spanish (default) and English |
| Audience | Design + implementation |

---

## 1. Purpose and scope

This document translates the product and technical requirements into a page-by-page specification: every route, what it shows, what it does, the states it can be in, and how it connects to the rest of the app. It is the bridge between the PRD and the implementation.

Out of scope: visual design system details (colors, typography tokens), final copy for marketing pages, and analytics implementation.

---

## 2. Navigation model

### 2.1 Route tree

```
/{locale}                                 Landing (public)
├── /how-it-works                         Public explainer
├── /privacy, /terms                      Legal
├── /sign-in, /sign-up                    Clerk
│
├── /start                                Paste a job posting   ← PRIMARY ENTRY
│   └── /[analysisId]                     Analysis + gap chat
│       └── /preview                      CV preview + download
│
├── /onboarding                           First-run profile setup (post sign-up)
│   └── /import                           Upload a master CV
│
├── /profile                              Profile list / overview
│   ├── /new                              Create profile manually
│   └── /[profileId]/edit                 Edit profile (form + facts)
│
├── /history                              Generated CVs
├── /settings                             Account, language, quotas
│   └── /api-key                          Bring Your Own Key
├── /status                               Service status / degraded mode
└── /admin/usage                          Internal cost dashboard (restricted)
```

- `{locale}` ∈ `es` | `en`. `/` redirects to `/es` unless a stored preference says otherwise (PRD RF-8.2, TR-I18N-7).
- Every route below the landing requires locale resolution; app routes additionally require a session **except `/start` and its children**, which support guest mode (PRD RF-1.3).

### 2.2 Route table

| Route | Auth | Render | Purpose |
|---|---|---|---|
| `/{locale}` | Public | Static + client | Landing, primary CTA |
| `/{locale}/how-it-works` | Public | Static | Explain the 95% rule and fact-locking |
| `/{locale}/privacy`, `/terms` | Public | Static | Legal |
| `/{locale}/sign-in`, `/sign-up` | Public | Clerk | Authentication |
| `/{locale}/start` | **Public (guest allowed)** | Dynamic | Paste the job posting |
| `/{locale}/start/[analysisId]` | Public (guest allowed) | Dynamic, streaming | Analysis, gaps, chat |
| `/{locale}/start/[analysisId]/preview` | Session or guest | Dynamic | Generated CV + download |
| `/{locale}/onboarding` | Session | Dynamic | First-run profile setup |
| `/{locale}/onboarding/import` | Session | Client-heavy | CV upload + parse + review |
| `/{locale}/profile` | Session | Dynamic | Profile overview |
| `/{locale}/profile/new` | Session | Dynamic | Manual profile creation |
| `/{locale}/profile/[profileId]/edit` | Session | Dynamic | Edit profile |
| `/{locale}/history` | Session | Dynamic | Generated CV history |
| `/{locale}/settings` | Session | Dynamic | Account, language, quotas |
| `/{locale}/settings/api-key` | Session | Dynamic | BYO-key management |
| `/{locale}/status` | Public | Dynamic | Service status / degraded mode |
| `/{locale}/admin/usage` | Session + allowlist | Dynamic | Internal cost/observability |

### 2.3 Global shell

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Tailr        How it works   [ History ]        🌐 ES ▾    [ Avatar ▾ ]      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                              < page content >                                │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  Tailr · MIT · Privacy · Terms · Status                    Made in Colombia   │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Element | Behavior |
|---|---|
| Logo | Links to `/{locale}` (or `/{locale}/start` when signed in) |
| Nav links | Signed out: *How it works*, locale switcher, **Sign in**, **Start free**. Signed in: *Start*, *Profile*, *History*, *Settings* |
| Locale switcher | Swaps `{locale}` in the current path, preserving the route, query and in-progress state (TR-I18N-3) |
| Avatar menu | Profile, History, Settings, Sign out. For guests: **Sign in** |
| Guest banner | A slim bar shown to guests: *"You can generate 1 CV without an account."* |
| Degraded banner | Shown when the global budget is exhausted (`503`): *"Free capacity reached for today. Add your own API key to keep going."* → links to `/settings/api-key` |

Locale switching **never** re-runs an LLM call and never loses a form draft or an open chat.

---

## 3. Page specifications

Each page is specified with: purpose, layout, components, states, actions, data/API, and edge cases.

---

### P0 · Landing — `/{locale}`

**Purpose:** explain the promise in one screen and drive to `/start`.
**Entry:** any external link, logo, root redirect.
**Exit:** *Start free* → `/start`; *Sign in* → `/sign-in`.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Tailr                                                                       │
│                                                                              │
│                     Tailor your CV to any job.                               │
│                        Honest. One page. Fast.                               │
│                                                                              │
│                        [  Paste a job posting  ]                             │
│                                                                              │
│     ─────────────────────────────────────────────────────────────────        │
│     1 Paste the posting   2 Answer a few questions   3 Download your CV      │
│                                                                              │
│     ✻ We never invent experience. If we don't know, we ask.                  │
│                                                                              │
│     Why it's different · Free and open source (MIT)                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Component | Notes |
|---|---|
| Hero CTA | Primary action; goes straight to `/start` (no sign-up wall) |
| Three-step strip | Sets expectation that a conversation happens |
| Trust line | States the differentiator: the 95% rule |
| Social proof | Deferred to v1.1; no fake testimonials |

**States:** static. **Analytics:** `landing_view`, `cta_start_click`.
**Edge cases:** if `DEGRADED_MODE` is on, replace the CTA with a notice linking to `/status`.

---

### P1 · Sign in / Sign up — `/{locale}/sign-in`, `/{locale}/sign-up`

**Purpose:** authentication through Clerk.
**Entry:** header, guest gate, a protected deep link.
**Exit:** to the `redirect_url` (default `/onboarding` on first sign-up, `/start` otherwise).

| State | Behavior |
|---|---|
| First sign-up | → `/onboarding` |
| Returning user with a profile | → `redirect_url` or `/start` |
| Returning user without a profile | → `/onboarding` |
| Error | Clerk's inline error, localized |

**Edge cases:** expired session on a protected route → redirect to `/sign-in?redirect_url=…` and return afterwards. Guest-to-user upgrade must preserve the guest's generated CV (RF-1.3).

---

### P2 · Onboarding — `/{locale}/onboarding`

**Purpose:** get a usable master profile in the shortest possible path.
**Entry:** after first sign-up, or from `/profile` when no profile exists.
**Exit:** `/onboarding/import` or `/profile/new`, then `/start`.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Let's build your master profile                          Step 1 of 2        │
│                                                                              │
│   ┌────────────────────────┐      ┌────────────────────────┐                 │
│   │  📄 Upload my CV       │      │  ✍️  Fill it manually   │                 │
│   │  PDF or DOCX           │      │  5 minutes             │                 │
│   │  We'll fill the form   │      │  Full control          │                 │
│   │  for you               │      │                        │                 │
│   └────────────────────────┘      └────────────────────────┘                 │
│                                                                              │
│  You can edit everything later. Nothing leaves your account.                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Component | Notes |
|---|---|
| Upload card | → `/onboarding/import` |
| Manual card | → `/profile/new` |
| Privacy note | Reassures that the CV binary is not stored (RF-15.21 / TR-SEC-5) |

**Edge cases:** user abandons onboarding → next visit to `/start` shows a soft prompt to create a profile, but allows guest generation.

---

### P3 · Import CV — `/{locale}/onboarding/import`

**Purpose:** turn an uploaded CV into a prefilled profile and surface what could not be read.
**Entry:** onboarding, `/profile` → *Import*.
**Exit:** `/profile/[profileId]/edit` (review) or back to onboarding.

**Flow:** three visible steps.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ① Upload            ② Extracting            ③ Review what we couldn't read  │
│  ●━━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━●                               │
│                                                                              │
│   Drop your CV here (PDF or DOCX, max 5 MB)                                  │
│   ┌──────────────────────────────────────────────────────────────────┐       │
│   │                        ⬆  Choose file                            │       │
│   └──────────────────────────────────────────────────────────────────┘       │
│                                                                              │
│   Extraction happens in your browser. The file is never uploaded.            │
└──────────────────────────────────────────────────────────────────────────────┘
```

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  We read your CV. Here's what we could NOT detect:            Step 3 of 3    │
│                                                                              │
│   ⚠️ Projects             — not found (layout may have hidden the section)   │
│   ⚠️ Certifications       — partially detected (2 of 4)                      │
│   ⚠️ Experience dates     — Adventure Software: no end date                  │
│   ⚠️ Languages            — not found                                        │
│                                                                              │
│   ✅ Identity, contact, skills and education were detected.                  │
│                                                                              │
│   [ Review and complete the form ]   [ Skip for now ]                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Component | Notes |
|---|---|
| Dropzone | Accepts PDF/DOCX, validates MIME + extension + size client-side (TR-SEC-4) |
| Extractor | `pdf.js` / `mammoth.js` — runs in the browser (RF-2.2) |
| Progress | Upload → extracting → structuring (the only LLM call on this page) |
| Undetected list | Driven by `fieldConfidence` below threshold (RF-2.4); each item links to the exact field in the editor |
| Detected summary | Positive reinforcement of what did work |

**API:** `POST /api/profile/parse` with `{ cvText, locale }` → partial profile, `fieldConfidence`, `undetected[]`.

**States:**
- **Empty:** dropzone.
- **Extracting:** progress with file name; cancel allowed.
- **Success:** undetected list (possibly empty → celebratory state).
- **Error — unreadable file:** "We couldn't read text from this PDF. It may be a scan." → offer manual entry or a text paste fallback.
- **Error — LLM failure:** retry, plus "fill manually" fallback.
- **Rate limited (`429`):** localized message with `Retry-After`.

**Edge cases:**
- Scanned/image-only PDF → no text layer → explicit message, no silent failure.
- Very long CV (> 100k chars) → truncated with a warning (TR-RL-6).
- DOCX with tables/columns → text extracted but structure lost → item appears in the undetected list.

---

### P4 · Profile editor — `/{locale}/profile/[profileId]/edit`

**Purpose:** the single source of truth for facts. Everything the generator can use lives here.
**Entry:** onboarding review, `/profile`, or the "complete your profile" prompt.
**Exit:** save → `/profile`; or *Tailor a CV* → `/start`.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Master profile · Diego Martínez                        [ Save ]  [ Cancel ] │
├──────────────────────────────────────────────────────────────────────────────┤
│  ▾ Identity & contact                                                        │
│     Name [ Diego Andrés Martínez Florez ]   Email [ … ]                      │
│     Phone [ … ]   LinkedIn [ … ]   GitHub [ … ]                              │
│     ⓘ City is optional and is not shown on the generated CV by default       │
│                                                                              │
│  ▾ Experience                                                        [+ Add] │
│     ┌ Adventure Software · Full-Stack Developer · Jun 2025 – Oct 2025 ┐      │
│     │ • Shipped 5 web applications…            [ fact ] [ edit ] [ × ]│      │
│     │ • Prototyped a voice AI assistant…       [ fact ] [ edit ] [ × ]│      │
│     │ + Add bullet                                                      │      │
│     └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ▾ Projects   ▾ Skills   ▾ Education   ▾ Certifications   ▾ Languages        │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────   │
│  Profile strength  ████████████░░░░  76%   · 12 facts · 3 gaps               │
│  [ Tailor a CV → ]                                                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Component | Notes |
|---|---|
| Accordion sections | Identity, Experience, Projects, Skills, Education, Certifications, Languages |
| Fact badge | Each bullet is a `fact` with provenance (`cv_upload` / `user_input` / `chat_answer`) and is independently editable |
| Inline add/edit | Bullets and items are added inline; no page reload |
| Undetected markers | Fields flagged by the import keep a subtle "please confirm" state until the user edits or confirms them |
| Profile strength | % completeness + fact count + open gaps; a nudge, never a blocker |
| Save behavior | Autosave with debounce plus an explicit Save; unsaved-change guard on navigation |

**States:** new (empty with hints), prefilled-from-import (with confirm markers), editing (dirty), saving, saved, error.
**Edge cases:** deleting a fact that a saved CV referenced → the saved CV keeps its rendered text; new generations simply can't use that fact. Warn before deleting.

---

### P5 · Start / Paste posting — `/{locale}/start`

**Purpose:** the primary entry point. Paste a posting and go.
**Entry:** landing CTA, header *Start*, `/start/[analysisId]` back-link.
**Exit:** `/start/[analysisId]`.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Paste the job posting                                                       │
│                                                                              │
│  Copy the full description from any job board and paste it here.             │
│  ┌──────────────────────────────────────────────────────────────────┐        │
│  │                                                                  │        │
│  │  (job description text)                                          │        │
│  │                                                                  │        │
│  └──────────────────────────────────────────────────────────────────┘        │
│                                                          0 / 20,000 chars     │
│                                                                              │
│  Profile   [ Diego Martínez (master) ▾ ]     [+ New profile]                 │
│                                                                              │
│  [ Analyze posting → ]                          or  [ See an example ]       │
│                                                                              │
│  ⓘ No URL required. We don't scrape job boards.                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Component | Notes |
|---|---|
| Textarea | Paste-only (PRD RF-3.1); counter capped at 20,000 chars (TR-RL-6) |
| Profile selector | **Always visible**, even with a single profile (decision 5). Disabled with a "create your first profile" hint when none exists |
| Guest hint | If signed out: *"You can generate 1 CV without an account."* |
| Example button | **Stays** (decision 3): fills the textarea with a sample posting. Doubles as a demo aid and a testing fixture |

**States:** empty (CTA disabled), pasting, ready, oversize (counter turns red, CTA disabled), submitting.
**Edge cases:**
- Posting shorter than ~200 chars → warning: "This looks too short to analyze" but allow continue.
- Language not ES/EN → detected as `other`; CV is generated in the posting's language if supported, otherwise the app asks which language to use.
- Profile missing → a master profile is a **hard requirement** (decision 4). Show a blocking modal that links to profile creation; the pasted posting is preserved in `localStorage` so the user resumes immediately afterwards.

---

### P6 · Analysis + gap chat — `/{locale}/start/[analysisId]`

**Purpose:** the heart of the product. Show what matches, ask about what doesn't, and block until confident.
**Entry:** after `POST /api/analyze` returns.
**Exit:** `/start/[analysisId]/preview` when generation completes.

**Layout: two panels plus a persistent action bar.**

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  ← Paste another posting        Confidence  ████████░░  78%   Threshold: 95% │
├───────────────────────────────────┬──────────────────────────────────────────┤
│  POSTING ANALYSIS                 │  LET'S CLOSE THE GAPS                    │
│  Senior Node.js Developer         │                                          │
│  Acme · Bogotá · Hybrid           │  I compared the posting with your        │
│                                   │  profile. 4 things are missing.          │
│  Match 87%                        │                                          │
│                                   │  ┌────────────────────────────────────┐  │
│  MUST HAVE                        │  │ Do you have hands-on experience     │  │
│   ✅ Node.js                      │  │ with Docker in production?          │  │
│   ✅ REST APIs                    │  │                                     │  │
│   ✅ SQL / PostgreSQL             │  │ [ Yes, describe… ] [ No ] [ Skip ]  │  │
│   ⚠️ Docker        → asked        │  └────────────────────────────────────┘  │
│   ❓ Kubernetes    → asked        │                                          │
│                                   │  You: I used Docker for local dev and    │
│  NICE TO HAVE                     │  containerized a Postgres instance.      │
│   ✅ Git                          │                                          │
│   ❓ Terraform     → asked        │  Tailr: Noted — I saved that as a fact.  │
│                                   │  Confidence is now 78%. Two gaps left.   │
│  KEYWORDS MISSING                 │  ┌────────────────────────────────────┐  │
│   Kubernetes, Terraform, Docker   │  │ Type your answer…                   │  │
│                                   │  └────────────────────────────────────┘  │
├───────────────────────────────────┴──────────────────────────────────────────┤
│  ⚠️ 2 must-have gaps remain. Answer them to unlock generation.               │
│                                     [ Generate anyway ]  [ Generate CV → ]   │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Component | Notes |
|---|---|
| Confidence meter | Live value from §10 of the technical doc; visually marks the 95% threshold |
| Requirements list | Must / nice groups; each row shows a status badge: COVERED, PARTIAL, **asked**, UNKNOWN |
| Keywords missing | Explicit list — the recruiter view (PRD RF-3.2) |
| Chat panel | Streaming; max 4 questions per round (RF-4.3); questions in the **UI language** regardless of posting language (RF-8.6) |
| Quick answers | *Yes, describe…* / *No* / *Skip* to reduce typing |
| Fact confirmation | When the user answers, the UI confirms the fact was saved, with a link to edit it in the profile |
| Action bar | *Generate CV* enabled at ≥ 95%; *Generate anyway* always available but visually secondary and marks the run as forced |

**States:**
- `ANALYZING` — skeleton loaders in the left panel, chat disabled.
- `ANALYZED` — both panels live.
- `AWAITING_ANSWERS` — chat active; generate disabled unless forced.
- `READY` — confidence ≥ 95%; primary CTA enabled; chat still open for extra context.
- `GENERATING` — inline progress ("Writing bullets… Formatting to one page…"), inputs locked.
- `DONE` — redirect to preview.
- `ERROR` — inline retry with a preserved transcript.

**API:** `POST /api/chat` (streaming), `POST /api/generate`.
**Edge cases:**
- User refuses to answer a must-have gap → *Generate anyway* creates the CV without that claim and records `forced = true`. The preview then shows an explicit notice.
- All providers down (`502`) → banner with retry; the transcript is preserved.
- Posting contains injection text → logged and ignored; the app never changes behavior (TR-SEC-1/2).

---

### P7 · Preview + download — `/{locale}/start/[analysisId]/preview`

**Purpose:** show exactly what will be sent and let the user download it.
**Entry:** generation complete.
**Exit:** download; *Tailor another* → `/start`; *Edit profile* → profile editor.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Your CV is ready                       1 page · 97% full · 0 unverified     │
├───────────────────────────────────────────┬──────────────────────────────────┤
│                                           │  CHECKS                          │
│   ┌───────────────────────────────────┐   │  ✅ One page                     │
│   │                                   │   │  ✅ All claims traced to facts   │
│   │      [ rendered document ]        │   │  ✅ ATS-safe layout              │
│   │                                   │   │  ⚠️ 1 must-have gap unanswered   │
│   │                                   │   │                                  │
│   │                                   │   │  TRACEABILITY                    │
│   │                                   │   │  Every bullet links to a fact →  │
│   │                                   │   │  click to see its source         │
│   │                                   │   │                                  │
│   └───────────────────────────────────┘   │  [ Download .docx ]              │
│                                           │  PDF · coming soon               │
│                                           │  [ Regenerate ]                  │
│                                           │  [ Tailor another posting ]      │
└───────────────────────────────────────────┴──────────────────────────────────┘
```

| Component | Notes |
|---|---|
| Document preview | **Image rendered by the docgen service** (decision 6), not live HTML. Guarantees the preview is byte-faithful to the downloaded file |
| Metrics strip | `page_count`, `fill_pct`, `unverified_count` from the docgen response |
| Checks panel | One page, fact traceability, ATS safety; warnings are explicit and non-blocking |
| Traceability | Each bullet can be expanded to show the `fact_id` and its provenance — this is the visible proof of the promise |
| Download | `.docx` only in v1. **PDF is deferred** (decision 2): the control is shown disabled with a localized "coming soon" label |
| Regenerate | Re-runs generation (counts against quota); useful after editing the profile |

**States:** generating (skeleton), ready, warning (forced generation / unresolved must-have), error (docgen failed → retry, the content tree is preserved).
**Edge cases:**
- Pagination cannot converge to 1 page → show page count with a clear warning and suggest trimming the least relevant bullets.
- Guest user → the download button triggers the **guest gate** (P14) before the file is released.

---

### P8 · History — `/{locale}/history`

**Purpose:** re-download past CVs without spending tokens.
**Entry:** header nav, avatar menu.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Your CVs                                                [ Tailor a new one ]│
├──────────────────────────────────────────────────────────────────────────────┤
│  Acme · Senior Node.js Developer          12 Mar 2026 · 1 page · 97%         │
│  Match 87% · ES                             [ Preview ] [ Download ] [ ⋯ ]   │
├──────────────────────────────────────────────────────────────────────────────┤
│  Globant · Backend Engineer               04 Mar 2026 · 1 page · 95%         │
│  Match 74% · EN                             [ Preview ] [ Download ] [ ⋯ ]   │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Component | Notes |
|---|---|
| Row | Company, role, date, page count, fill %, CV language, match score |
| Actions | Preview, Download (no token cost), delete |
| Empty state | "You haven't generated any CVs yet" + CTA |

**Edge cases:** deleted profile → its generated CVs are deleted too (cascade), with a confirmation warning.

---

### P9 · Settings — `/{locale}/settings`

**Purpose:** account, language, quotas and data control.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Settings                                                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│  LANGUAGE                                                                    │
│    Interface language            ( ) Español   (•) English                    │
│    ⓘ The CV language follows the job posting, not this setting.               │
│                                                                              │
│  USAGE TODAY                                                                 │
│    Analyses        3 / 20        Generations    1 / 10                       │
│    Chat messages   14 / 60       [ Add your own API key to remove limits → ] │
│                                                                              │
│  DATA                                                                        │
│    [ Export my data ]   [ Delete my account and all data ]                   │
│                                                                              │
│  ABOUT                                                                       │
│    Tailr is free and open source (MIT).                                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Component | Notes |
|---|---|
| Interface language | Writes the user's locale and switches the UI immediately (TR-I18N-2) |
| Usage | Reads today's counters; links to BYO-key when close to limits |
| Data | Export and hard delete (RF-7.3, TR-SEC-11) |
| Delete | Double confirmation requiring typing the word *delete* |

**Edge cases:** deleting the account while a generation is in progress → cancel first, then delete.

---

### P10 · BYO-key — `/{locale}/settings/api-key`

**Purpose:** let power users bypass shared limits with their own provider key.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Bring your own API key                                                      │
│                                                                              │
│  Use your own LLM key to skip the shared daily limits.                        │
│  Your key is encrypted, never shown again, and never logged.                 │
│                                                                              │
│  Provider  [ Groq ▾ ]                                                        │
│  API key   [ •••••••••••••••••••••••••• ]   [ Save ] [ Test ]                │
│                                                                              │
│  Current: groq · gsk_…4f2a          [ Remove ]                               │
│                                                                              │
│  ⓘ Your key is used only for your own requests. If it fails, your            │
│    generation fails; we never fall back to the shared key.                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Component | Notes |
|---|---|
| Provider selector | Only providers already integrated (RF-15.27) |
| Key field | Write-only; after saving, only `provider` + `key_hint` are ever returned (RF-15.23) |
| Test button | Performs a minimal validation call and reports a localized result |
| Remove | Takes effect immediately and returns the user to shared quotas (TR-RL-14) |
| Explanation | States the no-silent-fallback rule explicitly (RF-15.26) |

**Edge cases:** invalid key → clear error, never a silent fallback; key with exhausted provider quota → error surfaces the provider's message.

---

### P11 · How it works — `/{locale}/how-it-works`

**Purpose:** explain the 95% rule and fact-locking — the reason to trust the product.
**Content blocks:** the problem with AI-generated CVs; what fact-locking means (with a worked example of a rejected bullet); what happens when we don't know something; what we never do (no invented metrics, no scraping of your data); open source and MIT.
**States:** static. **Edge cases:** deep-linkable anchors from the landing page.

---

### P12 · Privacy and Terms — `/{locale}/privacy`, `/{locale}/terms`

**Purpose:** legal and transparency obligations.
**Privacy page must state:** what is stored (profile, facts, analyses, generated files), what is not (the original CV binary), retention, subprocessors (Clerk, Supabase, Upstash, LLM provider), and how to delete everything.
**Edge cases:** locale-specific legal text — if only one language is legally reviewed, show the reviewed version with a notice.

---

### P13 · Status / degraded — `/{locale}/status`

**Purpose:** honest communication when the free capacity is exhausted.
**Shows:** current mode (normal / degraded / capacity reached), what is affected, when it resets, and the BYO-key workaround.
**Entry:** the degraded banner, `503` responses, footer link.
**Edge cases:** must be statically renderable and must not depend on the LLM.

---

### P14 · Guest gate (modal)

**Purpose:** convert a guest into a user at the moment of highest intent — right after the CV is generated.
**Trigger:** guest clicks any download, or navigates to a protected route.

```
┌──────────────────────────────────────────────────────────────────┐
│  Your CV is ready 🎉                                              │
│                                                                  │
│  Create a free account to download it and keep it in your        │
│  history. Everything you just answered is saved.                 │
│                                                                  │
│  [ Continue with Google ]   [ Continue with email ]              │
│                                                                  │
│  No credit card. Free forever. Open source.                      │
└──────────────────────────────────────────────────────────────────┘
```

**Rules:**
- Exactly **one** generation without an account (RF-1.3).
- The guest's profile answers and generated CV are migrated to the new account on sign-up.
- The gate never appears *before* the first generation completes — the value must be shown first.

**Edge cases:** guest closes the modal → the generated CV stays available while the signed guest cookie lives (decision 1); signing up migrates the profile answers and the generated CV into the new account.

---

### P15 · Admin usage dashboard — `/{locale}/admin/usage`

**Purpose:** internal observability. Restricted to an email allowlist.
**Shows:** tokens and cost per day, provider failure rate, hallucination rate (rejected bullets / total), forced-generation rate, pagination iterations per document, p95 generation latency.
**Entry:** direct URL only; never linked in the UI.
**Edge cases:** unauthorized users get a `404`, not a `403`, to avoid disclosing the route.

---

### P16 · Error pages

| Page | Content |
|---|---|
| `404` | "This page doesn't exist" + link to `/start` |
| `500` | Apology, retry, link to `/status` |
| `503` (capacity) | Explains the free-tier limit, reset time, BYO-key workaround |
| Offline | Detected client-side; the paste textarea keeps its content in `localStorage` |

All error copy is localized and never exposes stack traces or provider messages verbatim.

---

## 4. Cross-cutting flows

### 4.1 Guest happy path (no account)

```
Landing → /start (paste) → /start/[id] (answer 4 questions) → Generate
  → /preview → click Download → GUEST GATE → sign up
  → profile + generated CV migrated → download released
```

### 4.2 Onboarding (CV import)

```
Sign up → /onboarding → /onboarding/import → (client extraction)
  → undetected fields listed → /profile/[id]/edit → save
  → /start
```

### 4.3 Returning user

```
Sign in → /start → paste → analyze → (confidence already ≥ 95% because the
profile is complete) → Generate → /preview → download
```

### 4.4 Gap-resolution loop (inside P6)

```
analyze → confidence 0.62 → 4 questions
  → answer 2, skip 1, "no" on 1 → confidence 0.89 → 2 more questions
  → answer both → 0.96 → Generate enabled
```

### 4.5 Capacity exhausted

```
Any LLM-backed action → 503 → banner + /status
  → user adds BYO-key at /settings/api-key → retries → succeeds
```

---

## 5. Pipeline state → UI mapping

| Pipeline state (technical doc §8) | Page | UI treatment |
|---|---|---|
| `IDLE` | P5 | Paste form, CTA disabled until text present |
| `ANALYZING` | P6 | Skeletons; chat disabled |
| `ANALYZED` | P6 | Requirements + match score; chat enabled |
| `AWAITING_ANSWERS` | P6 | Generate disabled (force available) |
| `READY` | P6 | Generate enabled; confidence meter at/above threshold |
| `READY_FORCED` | P6 | Generate enabled with a persistent warning |
| `GENERATING` | P6 | Locked inputs, inline progress |
| `REGENERATING` | P6 | "Adjusting to fit one page…" |
| `DONE` | P7 | Preview + checks + downloads |

---

## 6. Error and edge-case matrix

| Situation | Where | Behavior |
|---|---|---|
| Rate limited (`429`) | Any LLM action | Localized message with `Retry-After`; BYO-key link |
| Capacity reached (`503`) | Any LLM action | Persistent banner + `/status` |
| All providers failed (`502`) | P6 | Inline retry; transcript preserved |
| LLM output fails schema (`422`) | P6/P7 | Automatic silent retry once, then a user-facing retry |
| Unreadable PDF | P3 | Explicit message + manual/paste fallback |
| Posting too short | P5 | Warning, continue allowed |
| Posting too long | P5 | Counter red, CTA disabled, trim hint |
| Unsupported posting language | P5/P6 | Ask which CV language to use |
| Pagination cannot reach 1 page | P7 | Explicit warning with page count + trim suggestion |
| Forced generation with open must-have gaps | P7 | Warning + `unverified_count` surfaced |
| Guest tries to download | P7 | Guest gate (P14) |
| Session expires mid-flow | P6 | Draft state persisted; re-auth then resume |
| Fact deleted after a CV was generated | P8 | Saved CV keeps its rendered text; warning on delete |

---

## 7. Responsive and accessibility

| Aspect | Requirement |
|---|---|
| Breakpoints | Mobile (<640), tablet (640–1024), desktop (>1024) |
| P6 on mobile | Panels stack: analysis collapsible on top, chat anchored to the bottom sheet |
| Keyboard | Full flow completable without a mouse; visible focus rings |
| Screen readers | Confidence meter exposes an accessible value and label; chat messages use live regions |
| Contrast | WCAG 2.1 AA |
| Motion | Respects `prefers-reduced-motion` for skeletons and progress |
| Language | `lang` attribute updates on locale switch |

---

## 8. Analytics events (privacy-safe, no content)

| Event | Properties |
|---|---|
| `landing_view` | locale |
| `cta_start_click` | locale, signed_in |
| `posting_submitted` | length_bucket, detected_lang |
| `analysis_completed` | match_score_bucket, must_count, gap_count, confidence |
| `question_answered` | round, answered \| skipped \| no |
| `generation_completed` | fill_pct, page_count, forced, cv_lang, duration_ms |
| `generation_failed` | error_code |
| `download_clicked` | format, guest |
| `guest_gate_shown` | trigger |
| `signup_completed` | from_guest |
| `byo_key_saved` | provider |
| `limit_hit` | layer, task |

No CV text, posting text, names or emails ever enter analytics (TR-SEC-7).

---

## 9. Acceptance criteria (page level)

| # | Criterion |
|---|---|
| AC-1 | A guest can paste a posting, answer questions and see a previewed CV with **no account** (P5→P7). |
| AC-2 | The download for a guest is gated by P14 and the generated CV survives sign-up. |
| AC-3 | P6 never enables *Generate CV* below 95% confidence unless *Generate anyway* is used, and that choice is visible in P7. |
| AC-4 | Every bullet in P7 can be traced to a fact and its provenance. |
| AC-5 | P3 explicitly lists fields it could not detect; none are silently dropped. |
| AC-6 | Switching locale anywhere preserves state and triggers **no** LLM call. |
| AC-7 | Every page renders correctly in both `es` and `en`, with no missing keys. |
| AC-8 | With `RATE_LIMIT_ENABLED=false`, no rate-limit UI appears; with it enabled, `429` copy is clear and localized. |
| AC-9 | Degraded mode is reachable from every LLM-backed page via the banner. |
| AC-10 | P7 shows `page_count`, `fill_pct` and `unverified_count` accurately. |

---

## 10. Decisions and open questions

All six questions from the first draft of this document are resolved.

### 10.1 Resolved

| # | Question | Decision | Impact on this document |
|---|---|---|---|
| 1 | Guest data persistence | **Cookie.** A signed, HttpOnly guest cookie; no Clerk anonymous accounts. | The guest CV survives while the cookie lives. A cleared cookie or a different browser starts over (P14) |
| 2 | PDF download | **Deferred.** v1 ships `.docx` only. | P7 shows PDF as *coming soon*; P8 offers `.docx` only |
| 3 | Demo posting | **Stays**, as a demo aid and a testing fixture. | P5 keeps the *See an example* button |
| 4 | Profile requirement | **A master profile is required.** No generation without one, not even for guests. | P5 blocks with a profile-creation modal and preserves the pasted posting |
| 5 | Multi-profile selector | **Always visible**, even with a single profile. | P5 always renders the selector |
| 6 | Preview fidelity | **Image rendered by the docgen service**, not live HTML. | The preview is byte-faithful to the downloadable file (P7) |

### 10.2 Still open

None. New questions raised during implementation should be appended here.
