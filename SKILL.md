---
name: obsidian-knowledge-forge
description: 知识库锻造 — Obsidian 知识库自动化管理。Use when managing the Obsidian knowledge base automation (vault-pipeline, inbox-watcher, forge-status), troubleshooting pipeline issues, assessing vault quality, or interacting with the MyBrain vault at /mnt/i/ObsidianVaults/MyBrain
---

# Obsidian Knowledge Forge

## Overview

Automated knowledge pipeline: files dropped into Obsidian `00-Inbox` are auto-converted, AI-processed, classified, linked, and indexed. Runs on WSL2/Ubuntu, watches vault on Windows I: drive via `/mnt/i/ObsidianVaults/MyBrain`.

## Architecture

```
Windows Obsidian (UI)        WSL2/Ubuntu (processing)
─────────────────────       ─────────────────────────
Drop files into 00-Inbox →  inbox-watcher (60s poll)
                            ↓
                            vault-pipeline:
                            ① pandoc/markitdown convert
                            ①.5 quality gate (dedup + size filter)
                            ② obsidian-forge process-all (AI)
                            ③ classify-inbox
                            ④ strengthen-graph
                            ⑤ update-mocs + sync
                            ↓
                            → 10-Zettelkasten / 03-Resources
```

Key directories: `00-Inbox` (landing), `00-Raw` (originals), `03-Resources` (captured), `10-Zettelkasten` (distilled knowledge), `99-Archives`.

## Quick Reference

| Command | What it does |
|---------|-------------|
| `forge-status` | Full health check (env, tools, processes, model) |
| `forge-log` | Last 30 lines of pipeline log |
| `forge-restart` | Kill and restart inbox-watcher + keep_forge_alive |
| `tail -f ~/.obsidian-forge/logs/pipeline.log` | Live pipeline trace |
| `tail -f ~/.obsidian-forge/logs/watcher.log` | Live watcher trace |
| `ls /mnt/i/ObsidianVaults/MyBrain/00-Inbox/` | Check what's waiting |
| `~/.local/bin/vault-pipeline` | Manual full pipeline run |
| `forge-audit` | Full vault quality scan (A/B/C/D grading) |
| `forge-dedup --dry-run` | Preview duplicate files (same title, different timestamp) |
| `forge-dedup` | Archive duplicates to 99-Archives/_dedup |
| `forge-clean-stubs --dry-run` | Preview STUB files (empty summary + <1KB + no wikilinks) |
| `forge-clean-stubs` | Archive STUB files to 99-Archives/_stubs |
| `forge-status-ai` | Quick AI connection test (ping DeepSeek/Ollama) |
| `obsidian-forge --vault-path ... status` | obsidian-forge native status (AI config, vault info) |

## Quality Gate (runs automatically in pipeline)

Before AI processing, each Inbox file is checked:
- **Size gate**: <200 byte files rejected (moved to `99-Archives/_quality-rejected`)
- **Dedup gate**: files matching existing content by canonical title are rejected

Rejected files: `99-Archives/_quality-rejected/`
Deduplicated files: `99-Archives/_dedup/`

## Troubleshooting

**Files stuck in Inbox (>2 min):**
1. `ls /mnt/i/ObsidianVaults/MyBrain/00-Inbox/` — I/O error means Unicode filename bug
2. Fix: rename in Windows Explorer, replace special quotes like `""` with regular chars
3. `.canvas` files are skipped by design — move them out manually

**Pipeline not running:**
1. `forge-status` — check if inbox-watcher is alive
2. If dead: `forge-restart`
3. Check logs: `forge-log`

**WSL2 reboot recovery:**
- Open any Ubuntu terminal → services auto-start via `~/.bashrc`
- Verify: `forge-status`

**AI not generating summaries (empty `summary: ''` in processed files):**
1. `obsidian-forge --vault-path /mnt/i/ObsidianVaults/MyBrain status` — check AI section
2. Verify `base_url` points to DeepSeek (`https://api.deepseek.com/v1`) not localhost
3. Config files:
   - `~/.obsidian-forge/config.toml` — global AI config (`[ai]` section)
   - `/mnt/i/ObsidianVaults/MyBrain/vault.toml` — per-vault model override (`[ai] model`)
   - `~/.config/obsidian-forge/.env` — API key (env vars, must be in this exact path)
4. Provider must be `openai-compatible`, model must be a valid DeepSeek model (e.g. `deepseek-chat`)
5. Test: `OPENAI_COMPATIBLE_API_KEY="sk-..." obsidian-forge --vault-path ... status`

## Two-Layer Quality System

### Layer 1: Bash automation (objective, repeatable)
```bash
forge-dedup --dry-run     # Preview exact duplicates (same URL, re-scraped)
forge-dedup               # Archive them to 99-Archives/_dedup
```
These handle mechanical tasks: identical files, size filters, file counting. They are fast and deterministic.

### Layer 2: Agent content review (judgment, preferred for quality)
Bash cannot judge content usefulness. For actual quality assessment, use Agent sub-agents:

**Pattern**: Spawn 3-5 parallel agents, each reading ~30 notes from a different section of 03-Resources. Each agent evaluates:
- Is the content original analysis, or just a scraped snippet?
- Is the `summary` field populated, or empty (meaning pipeline didn't really process it)?
- Would a human find this useful if searching this topic?
- Signal-to-noise: how many notes are "stubs" (title + link only) vs. actual knowledge?

**Why Agent review is reliable and bash scoring is not:**
- Bash scores link count → MOC index pages get inflated scores (not real quality)
- Bash scores tag presence → pipeline auto-tags everything (meaningless signal)
- Agent reads actual text → can distinguish "RSS snippet stub" from "deep analysis"

**Agent review prompt template:**
```
Read the first 30 .md files in 03-Resources/Reference/Articles-Papers/.
For each file, classify as:
- STUB: summary is empty, only title + source link, <500 bytes
- SNIPPET: has a 1-2 sentence AI summary but no original analysis
- KNOWLEDGE: substantial content with original analysis or synthesis
Report counts and flag the worst offenders.
```

### Quick Audit Commands
```bash
forge-dedup --dry-run                # Check for new duplicates
forge-dedup                          # Clean duplicates
# For content quality: use Agent sub-agents (see Layer 2 above)
```

## Monthly Maintenance

1. `forge-dedup` — clean exact duplicates (bash)
2. Spawn Agent sub-agents to sample-review 03-Resources content quality
3. Review `99-Archives/_quality-rejected/` — delete if useless
4. Check Zettelkasten:Resources ratio — target >1:10
5. Run `forge-status` — verify pipeline health
