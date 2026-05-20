# Powerbot — Project Context for Claude Code

## What this project is

Powerbot is a chatbot that coaches academic psychology researchers through sample size planning and power analysis. Tone: warm, motivational-interviewing style. It gathers study details, helps determine the smallest effect size of interest (SESOI), explores ways to increase power without increasing N, and guides researchers toward well-powered studies.

The researcher (sbernecker) is not a software engineer — R/RStudio background. All code changes should be explained in plain language.

---

## Stack

| Layer | Tool | Purpose |
|---|---|---|
| UI / web server | Streamlit | Chat interface, password gate, sidebar |
| LLM | Claude Sonnet 4.6 via Anthropic API | The actual AI brain |
| Web search | Built-in `web_search` tool | Methodology lookups during conversations |
| Persistent logging | Supabase (free tier) | Conversation rows survive redeployments |
| Code storage | GitHub (`sbernecker/powerbot`, `main` branch) | Source of truth |
| Hosting | Streamlit Community Cloud | Auto-redeploys on push to `main` |
| Local environment | Claude Code desktop app (Windows) running in a Linux container | Development environment |

Live URL: **https://higherorder-powerbot.streamlit.app/**
Password: stored in Streamlit Cloud secrets as `APP_PASSWORD`

---

## File structure

```
powerbot/
├── app.py                        # Full Streamlit app (~170 lines)
├── system_prompt.md              # Bot personality/instructions — the main editing target
├── requirements.txt              # Python deps: streamlit, anthropic, supabase
├── CLAUDE.md                     # This file
├── .gitignore                    # Excludes secrets.toml, conversations/, .venv/
├── .streamlit/
│   └── secrets.toml.example      # Template; real secrets.toml is gitignored
└── conversations/                # Local JSONL logs (ephemeral on Streamlit Cloud)
```

---

## Key architectural decisions

**system_prompt.md is read from disk on every session** — not hardcoded in app.py. To change bot behavior, edit this file and push. Streamlit Cloud redeploys in ~1 minute.

**Conversation history is sent to the API in full on every turn.** Claude has no native memory; `app.py` resends the entire prior conversation each time. This is how multi-turn context works.

**Session persistence works via URL `?session=` parameter.** On page load, if `?session=<id>` is in the URL, messages are loaded from Supabase. New sessions auto-set this param so bookmarking the URL resumes the conversation.

**`parsed_output` field bug (fixed):** The Anthropic SDK v0.100+ adds a `parsed_output` field to text blocks that the API rejects when replayed in conversation history. Fixed by filtering stored message blocks to only known keys (`type`, `text`, `id`, `name`, `input`) before sending back to the API.

**Prompt caching is enabled** on the system prompt via `cache_control: {type: "ephemeral"}`. After the first turn of a session, the system prompt tokens are cached (~90% cheaper to re-read).

---

## Supabase schema

Table: `conversations`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | auto-generated primary key |
| `session_id` | text | matches the `?session=` URL param |
| `timestamp` | timestamptz | UTC ISO format |
| `role` | text | `"user"` or `"assistant"` |
| `content` | text | plain string for user; JSON string for assistant (list of content blocks) |

RLS is disabled (intentional for now — private testing only, anon key is server-side only).
Supabase project: `dnrctpjsizstfwgvwyhj.supabase.co`

---

## Secrets (never in git)

Stored in Streamlit Cloud's secrets vault and locally in `.streamlit/secrets.toml` (gitignored).

- `ANTHROPIC_API_KEY` — Anthropic API key (starts with `sk-ant-`)
- `APP_PASSWORD` — login password for the Streamlit app
- `SUPABASE_URL` — `https://dnrctpjsizstfwgvwyhj.supabase.co`
- `SUPABASE_KEY` — Supabase anon/public JWT key

---

## How to push changes

**Option A — GitHub web UI (best for system_prompt.md edits):**
1. Go to https://github.com/sbernecker/powerbot
2. Click the file → pencil icon → edit → "Commit changes"
3. Streamlit Cloud auto-redeploys in ~1 min

**Option B — Claude Code pushes for you:**
The git remote proxy in this environment doesn't have write access. Pushes require a GitHub Personal Access Token (classic or fine-grained with `contents: write` on the `powerbot` repo). The user can generate one at https://github.com/settings/tokens.

Once a PAT is available:
```bash
git remote set-url origin "https://<PAT>@github.com/sbernecker/powerbot.git"
git add <files>
git commit -m "description"
git push origin HEAD:main
```

The PAT used during initial setup (`github_pat_11ADAWHMQ09PuRjMFuUK5j_...`) has a 30-day expiry — generate a new one when it expires.

---

## Iteration loop for system prompt changes

1. Edit `system_prompt.md` (GitHub web UI or ask Claude Code)
2. Commit/push to `main`
3. Wait ~1 min for Streamlit Cloud redeploy
4. Open the app → click "Start new conversation" (to get a clean session with the new prompt)
5. Test. If behavior is wrong, identify which instruction is missing/conflicting and edit again.

**One change at a time** — so you know what caused each behavioral shift.

---

## Known deferred items (low priority)

- **Ctrl+C keyboard shortcut** in Streamlit triggers "Clear caches" dialog instead of copying text. Right-click → Copy works as workaround. Could be disabled in Streamlit config.
- **Conversation sharing** (e.g., share a link with a biostatistician) — not implemented. Workaround: download transcript via sidebar button.
- **RLS on Supabase** — currently disabled. Should be enabled before any public launch.
- **Cost monitoring** — set usage alerts at console.anthropic.com → Plans & Billing → Usage limits.
- **PAT rotation** — the GitHub PAT used for pushing expires. Regenerate at https://github.com/settings/tokens when needed.
