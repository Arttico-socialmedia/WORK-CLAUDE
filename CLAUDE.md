# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is **not a software codebase** — it's Ilze's private working repo for social media / content strategy at **Grupo Arttico** and **Tastto**, versioned on GitHub purely for backup. It bundles two unrelated things in one repo by deliberate choice (not a template default):

- `ccos-ratos/` — the "Claude Code OS" kit (from the Ratos de IA course, upstream: `github.com/dobralabs/ccos-ratos`). This is where actual work happens: Claude Code commands, skills, business context files, and content drafts. **It has its own `ccos-ratos/CLAUDE.md`** with the real business context (who Ilze is, tone of voice, active priorities) — read that file when working inside `ccos-ratos/`, don't duplicate it here.
- `BRAND - ARTTICO/` and `BRAND - TASTTO/` — brand identity assets (logos, color palettes, design guides, campaign reports) for the two brands. Mostly binary assets (PNG/AI/PDF) plus a few `design-guide.md` / report `.md` files.

There is no build, lint, or test suite for this repo as a whole — most content is Markdown, images, and Claude Code configuration.

## Automatic git sync (important gotcha)

Both `.claude/settings.json` (repo root) and `ccos-ratos/.claude/settings.json` register a `Stop` hook that auto-commits and pushes on every Claude Code session end:

```bash
git add -A && git commit -m "auto-sync: <timestamp>" && git push
```

- The root-level hook `cd`s into a hardcoded path (`/c/Users/artti/OneDrive/Área de Trabalho/WORK  - CLAUDE`) before running git — if the repo isn't checked out at that exact path, the hook silently no-ops (`|| exit 0`) and nothing gets synced. As of this clone, the repo lives at `C:\Users\artti\WORK-CLAUDE`, which does **not** match that hardcoded path.
- Because of this hook, uncommitted changes are expected to disappear into an auto-sync commit at the end of a session — don't assume `git status` showing clean means a human reviewed the diff.
- **Never commit `.env` files or secrets** — several skills (e.g. `comentario-dm-ratos`) generate `.env` files with API tokens at their own root; these are gitignored per-skill, not at the repo root, so double-check `git status` output before trusting an auto-sync push when adding new credential files.

## Working inside `ccos-ratos/`

This subtree is a self-contained Claude Code project with its own conventions:

- `.claude/commands/` — slash commands: `/setup` (onboarding, generates `ccos-ratos/CLAUDE.md` + `_contexto/`), `/iniciar` (session start, loads context), `/syncar` (manual git sync + first-time GitHub connect), `/mapear` (interview to turn repeatable processes into skills), `/atualizar` (audits context files against actual repo state and proposes fixes), `/novo-projeto` (scaffolds a new project folder with its own `CLAUDE.md`).
- `_contexto/empresa.md`, `_contexto/preferencias.md`, `_contexto/estrategia.md` — business facts, tone-of-voice rules, and current priorities. These are meant to be read at the start of any work session and kept in sync via `/atualizar`, not hand-edited wholesale (commands only append/edit specific lines, never reformat the whole file).
- `templates/skills/` and `templates/perfis/` — starting points for new skills/CLAUDE.md profiles; `templates/ferramentas/catalogo.md` lists available MCPs/CLIs to recommend when building new skills.
- `.claude/skills/` — locally-installed skills specific to this workspace (currently: `comentario-dm-ratos`).

## The one real piece of code: `comentario-dm-ratos` Cloudflare Worker

Path: `ccos-ratos/.claude/skills/comentario-dm-ratos/worker/`

Instagram DM-automation backend (comment-triggered auto-DM + public reply), deployed as a Cloudflare Worker with Cloudflare KV for storage.

```bash
cd "ccos-ratos/.claude/skills/comentario-dm-ratos/worker"
npm run dev      # wrangler dev — local worker
npm run deploy   # wrangler deploy
```

Architecture (`worker/src/index.js`, single file, no build step):
- `GET /webhook` — Meta webhook verification handshake (`hub.verify_token` check).
- `POST /webhook` — receives Instagram comment-change events; for each comment, looks up `AUTOMATIONS` KV by `post:<media_id>`, checks keyword match, and if it matches sends a private-reply DM plus a rotated public comment reply. Runs via `ctx.waitUntil` so Meta gets an immediate 200.
- `GET/POST/DELETE /automations` — CRUD for automation configs, gated by a `?key=<VERIFY_TOKEN>` query param (not a header). Automations are stored both under `post:<media_id>` and in a flat `index` array for listing.
- `GET /privacy` — static privacy-policy page required by Meta's app review.
- Config lives in a per-skill `.env` (never committed) plus `wrangler secret` for the actual Instagram token and verify token; `contas.yaml` in the skill folder tracks which Instagram accounts are wired up.
- "Retroactive" DM sends (for old comments) intentionally bypass the Worker and are run as one-off `curl` calls against the Graph API directly — the Worker only handles live webhook traffic.

Full setup/operational runbook (Meta app creation, Cloudflare account linking, secret rotation, troubleshooting) is documented in `ccos-ratos/.claude/skills/comentario-dm-ratos/SKILL.md` and `references/` — read those before touching this skill rather than re-deriving the flow.
