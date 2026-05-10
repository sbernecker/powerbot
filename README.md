# Powerbot

A chatbot that helps psychology researchers think through sample size planning and power analysis. Warm, motivational-interviewing tone; web search for methodology lookups; conversation logging for review.

This is a local-first v1 you run on your own machine. See the bottom of this file for the iteration loop.

---

## What you'll need

1. **Python 3.11 or newer** — check with `python3 --version`. If you don't have it, install from [python.org](https://www.python.org/downloads/) or via Homebrew / your package manager.
2. **An Anthropic API key** — sign up at [console.anthropic.com](https://console.anthropic.com/), go to *API Keys*, create one. **Set a billing cap** under *Plans & Billing* (e.g. $20) so there are no surprises.
3. **About 10 minutes** the first time.

---

## First-time setup

Open a terminal and `cd` into this folder (the one with `app.py`). Then:

```bash
# 1. Create an isolated Python environment for this project
python3 -m venv .venv

# 2. Activate it (Mac/Linux)
source .venv/bin/activate
# ...or on Windows PowerShell:
#   .venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your secrets file from the template
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Now open `.streamlit/secrets.toml` in any text editor and fill in:
- `ANTHROPIC_API_KEY` — paste the key from console.anthropic.com
- `APP_PASSWORD` — pick anything; you'll type this every time you open the app

The `.streamlit/secrets.toml` file is gitignored — it will never be committed.

---

## Running the app

Every time you want to talk to Powerbot:

```bash
# Activate the env (if not already)
source .venv/bin/activate

# Start the app
streamlit run app.py
```

Your browser opens at `http://localhost:8501`. Enter the password, then chat.

To stop the app: hit `Ctrl+C` in the terminal.

---

## Iterating on the system prompt

The bot's personality, instructions, and clinical guidance all live in **`system_prompt.md`**. This is the main knob.

1. Edit `system_prompt.md` in any text editor.
2. In the running app, click **"Rerun"** (top right) or press `R` in the Streamlit menu. Or click *"Start new conversation"* in the sidebar to make sure the change takes effect from turn 1.
3. Test it. If you like the change, keep it. If not, undo and try again.

The file is plain Markdown — headings, bullets, bold/italic all work. Don't worry about breaking anything; the only thing the app needs is for the file to exist and contain text.

---

## Reviewing conversations

Every conversation is logged to `conversations/<timestamp>-<id>.jsonl` — one file per session. Each line is a JSON object with `timestamp`, `role` (`user` or `assistant`), and `content`.

You can:
- Open the file in any text editor to read the transcript
- Use `cat conversations/*.jsonl` to dump all of them
- Or open in a spreadsheet program that can parse JSON lines

The `conversations/` folder is gitignored — your testing transcripts stay on your machine until you decide otherwise.

---

## Cost notes

Powerbot uses Claude Sonnet 4.6 with prompt caching enabled, so after the first turn of a session the system prompt is cached (~90% cheaper to read than to write fresh). Each web search costs about $0.01.

A typical 30-turn conversation with a handful of searches lands well under $1. Set a budget cap on console.anthropic.com to be safe.

---

## Troubleshooting

**"streamlit: command not found"** — your virtualenv isn't activated. Run `source .venv/bin/activate` first.

**"AuthenticationError"** — your API key in `.streamlit/secrets.toml` is wrong or missing. Double-check it starts with `sk-ant-`.

**Bot says something weird/off-tone** — edit `system_prompt.md` to address it directly. Reload the app.

**Want to start over** — click *"Start new conversation"* in the sidebar.

---

## What's next (after local feels solid)

When you're ready to share with testers:
1. Move logging to a persistent database (Supabase recommended — has a friendly web UI for browsing rows)
2. Push to a private GitHub repo
3. Deploy to Streamlit Community Cloud (free, git-based, auto-redeploys on push)
4. Share the resulting URL + password with testers

We'll tackle that as a separate step once you're happy with the bot's behavior locally.
