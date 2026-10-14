# Backend Schema & Data Ownership — Tailr

**Where client data lives, and who can see it.**

| Field | Value |
|---|---|
| Version | 0.1 (draft) |
| Companion documents | `PRD.md`, `technical_requirements.md`, `app_flow.md` |
| Scope | Data inventory, systems of record, access control, retention, deletion |
| Audience | Implementation + anyone asking "who can read my CV?" |
| Primary market | Spanish-speaking users (Colombia-first) |

---

## 1. Purpose and scope

Tailr stores highly personal data: someone's work history, contact details, and the jobs they are applying to. This document specifies, for every piece of client data:

1. **What it is** — a complete inventory.
2. **Where it lives** — the system of record.
3. **Who can see it** — an explicit access matrix.
4. **How long it stays** — retention.
5. **How it is destroyed** — deletion and export.

It is written to be readable by a non-engineer, because "who can see my CV?" is a product question, not only a technical one.

Out of scope: table DDL and column types (see `technical_requirements.md` §5), and UI copy for the privacy page (`app_flow.md` P12).

---

## 2. Data principles

These are binding. Every new feature must be checked against them.

| # | Principle | Consequence |
|---|---|---|
| P1 | **Data minimization** | If a field is not needed to generate a CV, it is not collected |
| P2 | **The original CV binary is never stored** | Only the extracted text and the resulting structured profile survive |
| P3 | **No user content is used to train models** | Providers are chosen with zero-retention options where available |
| P4 | **Content never enters logs or analytics** | Logs carry IDs, sizes, tokens and timings only |
| P5 | **The user owns the record** | Every row is reachable only by its owner, enforced by RLS plus a server-side check |
| P6 | **Secrets are write-only** | A stored API key can never be read back, by anyone, through the API |
| P7 | **Deletion is real** | Deleting an account hard-deletes rows and files; there is no soft-delete graveyard |
| P8 | **No human browses user data** | The operator has no UI to read profiles or CVs; the admin surface is aggregate-only |
| P9 | **The client's browser is not storage of record** | Cookies hold a session identifier and a locale, never profile content |

---

## 3. Data flow overview

```
        ┌─────────────┐
        │   Browser   │  guest cookie · locale · transient form drafts
        └──────┬──────┘
               │ (1) CV text extracted locally (pdf.js / mammoth.js)
               │ (2) posting text + profile edits
               ▼
     ┌──────────────────────┐
     │  Next.js on Vercel   │  ← env secrets (provider keys, service role)
     │  (application core)  │  ← logs: IDs, sizes, tokens, timings ONLY
     └───┬────────┬─────────┘
         │        │
         │        └──────────────► ┌────────────────────┐
         │                         │  LLM provider      │  sees: profile facts +
         │                         │  (Groq/Gemini/…)   │  posting text, transient
         │                         └────────────────────┘
         │
    ┌────▼─────────────┐   ┌──────────────┐   ┌─────────────────┐
    │ Supabase Postgres│   │ Supabase     │   │ Upstash Redis   │
    │ profiles, facts, │   │ Storage      │   │ rate counters,  │
    │ analyses, keys   │   │ .docx, PNG   │   │ JD-only cache   │
    └──────────────────┘   └──────────────┘   └─────────────────┘
              ▲
              │ identity only
    ┌─────────┴────────┐
    │      Clerk       │  email, OAuth subject, session
    └──────────────────┘
```

Numbers in the diagram are the two client-side steps that keep heavy personal content out of the server until it is needed.

---

## 4. Data inventory

Every data element the product touches, with classification.

| ID | Data element | Classification | Contains personal data? |
|---|---|---|---|
| D-01 | Account email | Identity | Yes |
| D-02 | Account display name | Identity | Yes |
| D-03 | OAuth provider subject (`sub`) | Identity | Yes (pseudonymous) |
| D-04 | Session token / cookie | Credential | Yes (bearer) |
| D-05 | Guest session cookie | Credential | Pseudonymous |
| D-06 | Interface locale preference | Preference | No |
| D-07 | Profile name | Personal | Yes |
| D-08 | Profile contact (phone, email, LinkedIn, GitHub) | Personal | Yes |
| D-09 | Profile city *(optional, not shown on CV by default)* | Personal | Yes |
| D-10 | Facts (experience, project, skill, education text) | Personal | Yes |
| D-11 | Fact metrics (numbers, percentages) | Personal | Yes |
| D-12 | Fact provenance | Metadata | No |
| D-13 | Job posting text | Third-party content | Sometimes (recruiter names, emails) |
| D-14 | Posting URL *(none in v1 — paste-only)* | — | — |
| D-15 | Posting analysis (requirements, keywords, match score) | Derived | Indirectly (match score reveals profile coverage) |
| D-16 | Gap questions and user answers | Personal | Yes (can contain volunteered detail) |
| D-17 | Conversation transcript | Personal | Yes |
| D-18 | Generated CV `.docx` | Personal | Yes |
| D-19 | Generated CV preview image (PNG) | Personal | Yes |
| D-20 | Generation metrics (`fill_pct`, `page_count`, `unverified_count`) | Metadata | No |
| D-21 | Format specification | Configuration | No |
| D-22 | BYO API key | **Secret** | Pseudonymous |
| D-23 | Usage events (tokens, cost, latency) | Telemetry | No (IDs only) |
| D-24 | Rate-limit counters | Telemetry | Pseudonymous (hashed IP) |
| D-25 | Analytics events | Telemetry | No (no identifiers beyond session) |
| D-26 | Application logs | Operational | No (content excluded by P4) |
| D-27 | Extracted CV text *(transient)* | Personal | Yes |
| D-28 | Original CV file *(never persisted)* | Personal | Yes — **not stored** |

---

## 5. Systems of record

| System | Holds | Region / notes |
|---|---|---|
| **Browser** | Guest cookie, locale preference, unsaved form drafts in `localStorage` | User's device. Cleared by the user or on logout |
| **Clerk** | D-01, D-02, D-03, D-04; MFA state; OAuth tokens | Subprocessor, US-hosted. Session management only |
| **Supabase Postgres** | D-06 … D-12, D-15 … D-17, D-20, D-21, D-22, D-23 | **Pinned to `us-east-1` (N. Virginia)** — see §18.1 |
| **Supabase Storage** | D-18, D-19 | Same region as the database. Private buckets; access only through short-lived signed URLs |
| **Upstash Redis** | D-24, and the **posting-only** analysis cache | Region co-located with the functions. TTL-bounded. Never holds profile data (see §13.3) |
| **LLM provider** | In-flight prompt content | Transient, **Zero Data Retention required** (see §8.1). Processed in the US |
| **Vercel** | D-26 logs, environment secrets | **Functions pinned to `iad1` (Washington, D.C.)** — see §18.1. Content excluded by P4 |
| **Analytics provider** | D-25 | Aggregate event names and non-identifying properties |

**Transient, never a system of record:** D-27 (extracted CV text) exists in memory during parsing and is discarded after the profile is written. D-28 is never written anywhere, by design (P2).

---

## 6. Access matrix — who sees what

Legend: **Owner** = the signed-in user who created it · **Server** = Tailr's own backend using the service role · **Operator** = the human running the deployment · **Other user** = any other Tailr account · **Provider** = the LLM provider in use · **Subprocessor** = Clerk / Supabase / Upstash / Vercel.

| Data | Owner | Server | Operator | Other user | Provider | Subprocessor |
|---|---|---|---|---|---|---|
| D-01…D-04 Account & session | ✅ | ✅ (id only) | ❌ | ❌ | ❌ | ✅ Clerk |
| D-05 Guest cookie | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| D-06 Locale | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| D-07…D-09 Profile identity & contact | ✅ | ✅ | ❌ | ❌ | ✅ when generating | ✅ Supabase |
| D-10, D-11 Facts | ✅ | ✅ | ❌ | ❌ | ✅ retrieved subset only | ✅ Supabase |
| D-12 Provenance | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ Supabase |
| D-13 Posting text | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ Supabase, Upstash (hash + derived only) |
| D-15 Analysis | ✅ | ✅ | ⚠️ aggregate only | ❌ | ❌ | ✅ Supabase |
| D-16, D-17 Q&A and transcript | ✅ | ✅ | ❌ | ❌ | ✅ (the answered turn) | ✅ Supabase |
| D-18, D-19 Generated CV & preview | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ Supabase Storage |
| D-20…D-21 Metrics, format spec | ✅ | ✅ | ⚠️ aggregate only | ❌ | ❌ | ✅ Supabase |
| D-22 BYO API key | ⚠️ write-only, masked hint | ⚠️ decrypt in memory per request | ❌ | ❌ | ⚠️ used to authenticate, not stored | ✅ Supabase (ciphertext) |
| D-23 Usage events | ❌ (not exposed) | ✅ | ⚠️ aggregate only | ❌ | ❌ | ✅ Supabase |
| D-24 Rate counters | ❌ | ✅ | ⚠️ aggregate only | ❌ | ❌ | ✅ Upstash |
| D-25 Analytics | ❌ | ✅ | ⚠️ aggregate only | ❌ | ❌ | ✅ Analytics provider |
| D-26 Logs | ❌ | ✅ | ⚠️ operational only | ❌ | ❌ | ✅ Vercel |
| D-27 Extracted CV text | ✅ | ⚠️ in memory only | ❌ | ❌ | ✅ during structuring | ❌ not persisted |
| D-28 Original CV file | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ **never transmitted or stored** |

### 6.1 Reading the matrix

- **No other user can see anything.** There is no sharing, no public profile, no leaderboard.
- **The LLM provider is the only third party that sees profile content**, and only the retrieved subset of facts relevant to the posting, never the whole profile (TR-RL-8).
- **The operator cannot read user content through the product.** There is no admin screen that lists profiles or downloads CVs; the admin surface reports counts and costs (D-15, D-20, D-23 aggregated).
- **The operator could technically access the database** with service-role credentials. This is stated honestly in §19 rather than hidden.

---

## 7. Row Level Security summary

RLS is enabled on **every** table. The ownership predicate is always derived from the Clerk JWT, never from client input.

| Table | Owner predicate | Client-readable | Client-writable |
|---|---|---|---|
| `profiles` | `user_id = auth.jwt()->>'sub'` | Own rows | Own rows |
| `facts`, `experience`, `projects`, `education`, `certifications` | via parent `profile_id` | Own rows | Own rows |
| `job_analyses`, `questions`, `conversations`, `generated_cvs` | via parent `profile_id` | Own rows | Own rows |
| `format_specs` | `owner_id is null` (global) or own | Global + own | Own only |
| `usage_events` | — | ❌ | ❌ (server-insert only) |
| `user_api_keys` | `user_id = auth.jwt()->>'sub'` | `provider` + `key_hint` only | Insert / delete only |

**Defense in depth:** RLS is the second line. Every mutation also performs a server-side ownership check resolved from the session, so a misconfigured policy alone cannot leak data.

---

## 8. Third-party subprocessors

| Subprocessor | Receives | Purpose | Content visibility | Retention | DPA |
|---|---|---|---|---|---|
| **Clerk** | Email, OAuth subject, session metadata | Authentication | Identity only; no CV or posting content | Session-scoped | Published |
| **Supabase** | All persisted product data | Database + file storage | Full (it is the system of record) | Per §15 | Published |
| **Upstash** | Rate counters, hashed IPs, posting hash + derived analysis | Rate limiting + cache | No profile content (see §13.3) | TTL (minutes to days) | Published |
| **Vercel** | Application logs, environment secrets, request metadata | Hosting | No content by policy (P4) | Provider default | [Published addendum](https://vercel.com/legal/Vercel_Inc_-_Data_Processing_Addendum.pdf) |
| **LLM provider (Groq)** | Retrieved facts, posting text, chat turns | Analysis + writing | Transient; the only subprocessor that sees profile content | **Zero Data Retention enforced** (§8.1) | Published |
| **Analytics provider** | Event names + non-identifying properties | Product analytics | No content (P4) | Aggregate | Published |

Each subprocessor's current list is published on the privacy page and must be updated before a new one is added. Published DPAs are archived in `/legal/dpas/` with the date they were retrieved.

### 8.1 LLM provider data policy — a hard constraint

The LLM hop is the only place profile content leaves our infrastructure, so the provider must satisfy **zero data retention (ZDR)**. This is a selection criterion, not a preference.

| Provider | Default retention | ZDR available? | Verdict |
|---|---|---|---|
| **Groq** | Inference requests are **not retained by default**. Inputs/outputs are logged only for reliability or abuse cases, up to 30 days. Data sits in US GCP buckets; SCCs available | **Yes — for all customers**, self-serve via Data Controls, with no enterprise contract | ✅ **Primary.** Best fit: ZDR at the free tier, which is exactly the constraint we have |
| **Google Gemini API** | Free-tier content falls under the unpaid-service data terms, which allow use for **product improvement and model training**, with possible human review | Not on the free tier | ❌ **Excluded for profile content.** Enabling the safer behaviour requires a billing-enabled project, which breaks the free-tier constraint |
| **OpenRouter** | Depends on the upstream provider; retention varies per model and is published per provider | Provider-dependent; routing can be filtered to ZDR-only providers | ⚠️ **Fallback only**, and only with ZDR-only routing enabled |

Sources: [Groq — Your Data](https://console.groq.com/docs/your-data) · [Gemini API — data logging and sharing](https://ai.google.dev/gemini-api/docs/logs-policy) · [OpenRouter — provider logging](https://openrouter.ai/docs/guides/privacy/provider-logging).

**Decision:** Groq is the primary provider, with **ZDR enabled in Data Controls before the first real user**. Any fallback provider must meet the same bar. A provider that trains on free-tier content is never used for profile data, *not even as a last resort* — in that situation the app degrades or prompts for a BYO key instead.

**Consequence:** the "free tier" constraint and the ZDR requirement interact. If Groq's limits become the bottleneck, the answer is BYO-key (RF-15.22) or a paid provider, never a free provider that trains on user CVs.

---

## 9. Identity and session data

- Clerk is the identity system of record. Tailr never stores passwords.
- The Clerk JWT `sub` is the only user key stored in our database. No email or name is duplicated into Postgres beyond what the user puts in their profile.
- Session cookies are HttpOnly and Secure; the app never reads identity from a client-supplied `user_id`.
- On sign-out, the session is revoked at Clerk and any guest cookie is cleared.

---

## 10. Guest data lifecycle

Per decision 1 (`app_flow.md` §10.1), guests are identified by a **signed, HttpOnly cookie** — there is no Clerk anonymous account.

| Stage | What exists | Where |
|---|---|---|
| Guest pastes a posting | Posting text + in-memory session state | Browser + server memory; the profile requirement (decision 4) means a profile must exist first, so a guest without a profile is routed to create one |
| Guest answers questions | Answers held in the guest session record | Postgres, keyed to the guest cookie |
| Guest generates a CV | Generated `.docx` + preview | Supabase Storage, keyed to the guest session |
| Guest downloads | Guest gate (P14) → sign-up | — |
| Sign-up | Profile answers and the generated CV are **migrated to the new account** | Ownership keyed to the new `sub` |
| Cookie cleared / expires | Guest rows become orphaned and are purged by the retention job | §15 |

**Guest data is real personal data.** It is subject to the same RLS-equivalent protections, the same encryption, and the same retention limits as account data.

---

## 11. BYO API keys

The most sensitive secret in the system.

| Aspect | Rule |
|---|---|
| Storage | AES-256-GCM ciphertext in `user_api_keys.key_ciphertext` |
| Key material | `BYO_KEY_ENCRYPTION_KEY`, held only in Vercel environment variables |
| Read-back | **Impossible.** The API returns `provider` and `key_hint` (`gsk_…4f2a`) only |
| Logging | Never. Not in app logs, not in error messages, not in telemetry |
| Use | Decrypted in memory for the duration of a single request, then discarded |
| Fallback | If the key fails, the request fails. **Never** silently falls back to the platform key (RF-15.26) |
| Deletion | Immediate; the user returns to shared quotas (TR-RL-14) |
| Operator | Cannot read it. It is ciphertext in the database and the UI never displays it |

---

## 12. Generated artifacts

- `.docx` and preview PNG live in **private** Supabase Storage buckets. Buckets are never public.
- Files are served through **short-lived signed URLs** (15 minutes, TR-SEC-9), never by a guessable path.
- Signed URLs are generated server-side after an ownership check; a leaked URL expires quickly.
- Regenerating a CV creates a new object; the old one is deleted rather than versioned.
- Deleting a profile cascades to its generated artifacts (rows **and** storage objects).

---

## 13. Logging, telemetry and analytics

### 13.1 What logs may contain
IDs, task names, provider and model, token counts, latency, error codes, HTTP status, timings.

### 13.2 What logs must never contain
CV text, posting text, chat content, names, emails, phone numbers, profile facts, generated bullets, or API keys.

### 13.3 The posting analysis cache — a specific care point

Caching identical postings is a cost requirement (TR-RL-7), but the cache is **shared infrastructure**. The rule:

| Cached | Not cached |
|---|---|
| Posting-derived data: requirements, keywords, detected language, seniority, red flags | Anything derived from a user's profile: match score, coverage classification, gap list, confidence |
| Keyed by `jd_hash` (a hash of the posting text) | Any user identifier alongside the posting content |

**Rationale:** two users pasting the same posting may share the *posting* analysis, because that content belongs to the employer and is identical. The **match score and gaps are profile-specific** and are always computed per user. Consequence: the cache never becomes a cross-user leak of who applied where.

### 13.4 Analytics
Event names and non-identifying properties only, per `app_flow.md` §8. No content, no names, no emails.

### 13.5 IP addresses
Used transiently for rate limiting, stored in Redis **hashed with a rotating salt**, with a TTL of minutes. Not persisted to Postgres, not joined to a user record, not exported.

---

## 14. What we never store

Explicit, verifiable commitments:

| Never stored | Why it matters |
|---|---|
| The original uploaded CV file (D-28) | Removes the highest-risk artifact entirely; extraction happens in the browser |
| Plaintext API keys | Ciphertext only |
| CV, posting, or chat content in logs | P4 |
| Passwords | Clerk handles identity |
| Payment data | The product is free; no payments exist |
| IP addresses in long-term storage | §13.5 |
| Data used for model training | P3 |

---

## 15. Retention schedule

**Default is short. The user can opt in to keep content indefinitely.**

| Data | Default | With *Keep my data* on | Trigger for deletion |
|---|---|---|---|
| Profile, facts, experience, projects, education, certifications | Until the user deletes them | Same | User action, or account deletion |
| Job analyses | **30 days** | Until deleted | Age-out job, or user deletion |
| Questions and conversations | **30 days** | Until deleted | Age-out job, or user deletion |
| Generated CVs (`.docx`, PNG) | **30 days** | Until deleted | Age-out job, or user deletion |
| Guest session data | **7 days** from last activity | n/a | Age-out job, or sign-up migration |
| Usage events | 90 days | 90 days | Age-out job |
| Rate-limit counters | Minutes (TTL) | Minutes (TTL) | Automatic |
| Application logs | Provider default (short) | Provider default | Automatic |
| BYO key | Until removed by the user | Same | User action, or account deletion |

Rules:
- **The profile itself is never age-out deleted.** It is the user's own asset and the input to every generation. Only *derived* content expires: analyses, conversations and generated files.
- The **Keep my data** toggle is **off by default** and reversible. Turning it off re-applies the 30-day window to existing rows from that moment.
- Usage events carry no personal content, so they are kept for 90 days to allow quarter-over-quarter cost analysis.
- Age-out jobs run on a schedule and are idempotent. Retention values are constants in code, not scattered literals.
- Surfacing the toggle requires a settings surface; this extends `app_flow.md` P9.

---

## 16. Deletion and export

### 16.1 User-initiated deletion
| Scope | Effect |
|---|---|
| Delete a single generated CV | Removes the row and its storage objects |
| Delete a profile | Cascades to all child rows and artifacts; requires confirmation |
| Delete the account | Hard-deletes profile, facts, analyses, questions, conversations, generated files, BYO key, and the Clerk account |

### 16.2 Guarantees
- Deletion is **hard delete**, not a status flag (P7).
- Storage objects are removed as well as database rows; orphan sweeps run periodically as a safety net.
- Confirmation requires typing a word, and the UI states exactly what will be destroyed.
- Deletion is immediate for the user's perspective; backups may retain a copy for the provider's backup window, which is disclosed.

### 16.3 Export
The user can export their data as JSON (profile, facts, analyses) plus the generated `.docx` files. Export is self-service and does not require contacting support.

---

## 17. Encryption and key management

| Layer | Measure |
|---|---|
| In transit | TLS 1.2+ for all traffic, including subprocessor calls |
| At rest (database, storage) | Encryption at rest provided by Supabase |
| Field-level | `user_api_keys.key_ciphertext` with AES-256-GCM and a per-record nonce |
| Secrets | Vercel environment variables; never in the client bundle, never in the repo |
| Sessions | HttpOnly, Secure cookies; Clerk-managed tokens |
| Signed URLs | Short TTL, generated server-side after an ownership check |

Key rotation: `BYO_KEY_ENCRYPTION_KEY` rotation is a documented procedure that re-encrypts rows in a single pass; until it completes, both keys are accepted for decryption.

---

## 18. Cross-border transfers and region pinning

### 18.1 Decided regions

| Component | Region | Why |
|---|---|---|
| Supabase project (Postgres + Storage) | **`us-east-1` — N. Virginia** | Lowest-latency well-connected region for Colombia, and a *specific* region rather than a general grouping, so the data location is exact |
| Vercel functions | **`iad1` — Washington, D.C.** | Same coast as the database, so the app↔DB hop stays inside the US East corridor. It is also Vercel's default, avoiding cross-region latency |
| Upstash Redis | Co-located with the functions | Rate limiting must be fast |
| LLM provider | United States (Groq retains in US GCP buckets) | No provider offers a Colombia or South America endpoint today |

**Why not São Paulo (`sa-east-1`)?** It is geographically closer to Colombia, but latency to northern South America from São Paulo is typically higher than from US East, and it would split the database away from the functions. It stays as the option to revisit **if data residency in South America becomes a legal requirement**, not a performance one.

Reference: [Supabase — available regions](https://supabase.com/docs/guides/platform/regions). Region lists change; confirm availability in the dashboard at project creation.

### 18.2 What this means for users

- Profile, facts, generated CVs and keys are stored in the **United States**.
- Prompts are processed in the **United States**.
- This is disclosed in Spanish on the privacy page, because Ley 1581 requires informing the *titular* about international transfers and the recipients.
- Region selection is a **data-location control, not proof of legal compliance**. Choosing a region on a free tier does not by itself satisfy a residency obligation.

---

## 19. Operator access — the honesty clause

It is technically possible for whoever runs the deployment to read the database with service-role credentials. Pretending otherwise would be dishonest. The position is:

1. **There is no product surface to browse user data.** No admin screen lists profiles, and no endpoint returns another user's CV. The admin dashboard is aggregate-only (counts, costs, error rates).
2. **Policy: no human reads user content.** Debugging uses synthetic fixtures and anonymized examples, not production rows.
3. **The code is MIT and self-hostable.** A user who does not want to trust this deployment can run their own. That is the structural answer to the trust question, and it is a deliberate design choice rather than a marketing line.
4. **Any exception must be logged.** If a future incident ever requires reading a specific record, it is recorded in a changelog.

This clause exists because "who sees my data?" deserves an answer that survives scrutiny.

---

## 20. Threat model: who could see what they shouldn't

| Threat | Likelihood | Impact | Control |
|---|---|---|---|
| Another user reads someone's CV | Low | High | RLS + server-side ownership checks + non-guessable IDs + signed URLs |
| A signed URL leaks | Medium | Medium | 15-minute TTL, ownership check before generation |
| Prompt injection exfiltrates profile facts | Medium | Medium | Posting and CV treated as data; retrieved-subset retrieval limits exposure; no tool access for the LLM |
| Provider retains content | Medium | Medium | Zero-retention settings where available; documented subprocessor list |
| Log scraping exposes content | Low | High | P4 enforcement; lint/CI check that log calls carry no content fields |
| Stolen BYO key from the database | Low | High | AES-256-GCM, key never in the same system as the ciphertext's key material |
| Operator misuse | Low | High | §19: no UI, policy, open source, self-hostable |
| Cache leaks cross-user data | Medium | High | §13.3: posting-only cache, profile-derived values always computed per user |
| Backup retention after deletion | Medium | Low | Documented backup window; deletion propagates |

---

## 21. Compliance notes

| Regime | Relevance | Position |
|---|---|---|
| **Colombia — Ley 1581 de 2012** (protección de datos personales, SIC) | Primary market | The user is the *titular*; collection is with consent at sign-up; the privacy policy is available in Spanish; deletion and consultation rights are self-service |
| **GDPR** | If EU users arrive | Legal basis: contract performance + consent. Rights: access, rectification, erasure, portability, objection. §16 covers erasure and portability |
| **CCPA/CPRA** | If US (California) users arrive | No sale of personal information; disclosure of categories collected; deletion and access rights |

**Not legal advice.** Before launch, the privacy policy and the consent flow should be reviewed by someone qualified, especially the Spanish-language texts, given Ley 1581's specific requirements for *autorización* and *aviso de privacidad*.

---

## 22. Verification: how we prove these claims

Claims in this document are testable. Each one maps to an automated check.

| Claim | Verification |
|---|---|
| RLS blocks cross-user access | Integration test: user B queries user A's profile and receives zero rows |
| No CV binary is stored | Test asserts no storage bucket receives the uploaded file; request payload inspection |
| Logs contain no content | CI lint rule that log calls cannot include content fields + a test that greps emitted logs |
| Deletion is hard delete | Test: delete account, then assert zero rows and zero storage objects remain |
| BYO key is unreadable | Test: after saving, every read path returns only `provider` and `key_hint` |
| Cache holds no profile data | Test: two users with different profiles posting the same `jd_hash` get different match scores from one cached posting analysis |
| Signed URLs expire | Test: URL returns 403 after the TTL |
| Signed URLs require ownership | Test: a signed URL generated for user A cannot be minted by user B |
| Short-by-default retention works | Test: rows older than the window are deleted by the age-out job; rows protected by *Keep my data* survive |
| ZDR is actually on | Pre-launch check: ZDR enabled in the provider console; a log assertion that no provider call runs with a training-enabled configuration |

---

## 23. Decisions and open questions

### 23.1 Resolved

| # | Question | Decision |
|---|---|---|
| 1 | Region pinning | Supabase **`us-east-1`** + Vercel **`iad1`** (US East, co-located) — §18.1 |
| 2 | Zero-retention providers | **Groq with ZDR enabled** as primary. The Gemini free tier is **excluded** for profile content because unpaid-service terms allow training on it — §8.1 |
| 3 | Retention defaults | **Short by default with an opt-in to keep**: 30 days for analyses, conversations and generated CVs; 7 days for guest data — §15 |
| 4 | DPAs | Publish and archive each subprocessor's addendum in `/legal/dpas/`; see 23.2 for the countersignature caveat |

### 23.2 Still open

1. **DPA countersignature.** Major subprocessors publish a Data Processing Addendum, but a *countersigned* copy generally requires a paid plan. Confirm per provider and record the outcome. For a free, non-monetized project the published addendum is likely sufficient, but this should be verified rather than assumed.
2. **Retention toggle UX.** The *Keep my data* opt-in needs a settings surface; this extends `app_flow.md` P9.
3. **Guest migration edge case.** If the guest cookie is lost before sign-up, purge the orphaned rows immediately or hold them for the 7-day window?
4. **Export format.** Is JSON plus `.docx` enough, or is a human-readable PDF export expected? (Note PDF export is deferred to v2.)
5. **South America residency.** Revisit `sa-east-1` only if a legal requirement appears, not for latency.
