# bro

**Real-time meeting & screen-aware AI assistant** with a terminal-style desktop UI for Linux and Windows.

[![CI](https://github.com/anomalyco/bro/actions/workflows/ci.yml/badge.svg)](https://github.com/anomalyco/bro/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> Not a ChatGPT clone. A **keyboard-first AI copilot** that can listen to meetings, read your screen when you ask, and stream short, speakable answers beside your workflow.

```text
$ meeting start
[MEETING] Started · [AUDIO] Listening…

Speaker A: "Why did you choose PostgreSQL?"
[QUESTION] Detected

> We chose PostgreSQL for JSONB support, reliability, and operational maturity…

$ screen analyze "why is this segfaulting?"
[SCREEN] Capturing… [OCR] … [AI] Analyzing…

> The crash is likely from out-of-bounds vector access after the loop…
```

---

## Table of contents

- [Features](#features)
- [Demo / quick start](#demo--quick-start)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [API keys (free vs own)](#api-keys-free-vs-own)
- [Usage](#usage)
- [Commands reference](#commands-reference)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [HTTP API](#http-api)
- [Development](#development)
- [Testing](#testing)
- [Packaging](#packaging)
- [Privacy & security](#privacy--security)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Community docs](#community-docs)
- [License](#license)
- [Disclaimer](#disclaimer)

---

## Features

| Area | What you get |
|------|----------------|
| **Terminal UI** | Dark monospace shell, streaming answers, command history, status line |
| **Meeting assistant** | Mic → VAD → STT → rolling transcript → question detection → auto-answer |
| **Screen assistant** | Screenshot → OCR → optional vision model → answer about on-screen content |
| **Combined mode** | Meeting + screen + history + RAG in one context package |
| **Multi-provider AI** | OpenAI, Groq, Gemini, OpenRouter, DeepSeek, xAI Grok, NVIDIA Nemotron, custom base URL |
| **Key modes** | Built-in **free** Groq path, or **own** key, or offline **mock** |
| **Voice** | `listen` for one-shot questions; optional system TTS (`espeak-ng`) |
| **RAG** | Local docs (`rag add <path>`) with dependency-free embeddings |
| **Desktop extras** | System tray, optional global hotkeys |
| **Backend** | Optional FastAPI service for health/ask/settings |

---

## Demo / quick start

```bash
git clone https://github.com/anomalyco/bro.git
cd bro

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
# or: uv pip install -e ".[dev]" --python .venv/bin/python

cp .env.example .env
# Edit .env — set FREE_AI_API_KEY or AI_API_KEY

python main.py
# equivalents:
#   python -m bro
#   ./scripts/run.sh
#   bro                 # after pip install -e .
```

First commands inside the app:

```text
help
apikey status
ask "Explain REST vs GraphQL in two sentences"
provider list
```

---

## Requirements

### Runtime

- **Python 3.11+** (tested through 3.14)
- Linux (X11; Wayland best-effort) or Windows 10/11
- Network access if using cloud LLM/STT providers

### Optional system packages

| Need | Fedora | Debian/Ubuntu |
|------|--------|----------------|
| OCR | `tesseract tesseract-langpack-eng` | `tesseract-ocr` |
| Mic I/O | `portaudio-devel` | `portaudio19-dev` |
| TTS | `espeak-ng` | `espeak-ng` |
| Hotkeys (Linux) | `python3-devel` (for `pynput`/evdev) | `python3-dev` |

---

## Installation

### From source (recommended while alpha)

```bash
pip install -e .
pip install -e ".[dev]"       # tests + ruff
pip install -e ".[hotkeys]"   # optional global hotkeys
pip install -e ".[stt-local]"  # optional faster-whisper
```

### Dependency sources

- **Canonical:** [`pyproject.toml`](pyproject.toml)
- **Convenience:** [`requirements.txt`](requirements.txt) → `pip install -r requirements.txt`

---

## Configuration

Copy the example env file:

```bash
cp .env.example .env
```

Important variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_KEY_MODE` | `free` \| `own` \| `mock` | `free` |
| `FREE_AI_API_KEY` | Key used in free mode (e.g. Groq) | empty |
| `FREE_AI_PROVIDER` | Provider id for free mode | `groq` |
| `FREE_AI_MODEL` | Model for free mode | `llama-3.3-70b-versatile` |
| `AI_API_KEY` | Your personal key (`own` mode) | empty |
| `AI_PROVIDER` | `openai`, `groq`, `gemini`, `openrouter`, `deepseek`, `xai`, `nvidia`, `compatible`, `mock` | `groq` |
| `AI_MODEL` | Model id for own mode | provider default |
| `AI_BASE_URL` | Override OpenAI-compatible base URL | provider default |
| `STT_PROVIDER` | `mock` \| `openai` | `mock` |
| `TTS_PROVIDER` | `none` \| `mock` \| `system` | `none` |
| `VOICE_OUTPUT_ENABLED` | Speak answers | `false` |
| `MEETING_CONTEXT_SECONDS` | Rolling transcript window | `120` |
| `MEETING_AUTO_ANSWER` | Auto-answer detected questions | `true` |
| `SCREEN_CAPTURE_ENABLED` | Allow screen commands | `true` |
| `SCREEN_MONITOR` | mss monitor index | `1` |
| `HOTKEYS_ENABLED` | Try global hotkeys | `true` |
| `RAG_PATH` | Auto-ingest path on startup | empty |
| `RESPONSE_STYLE` | `concise` \| `balanced` \| `detailed` \| `technical` | `balanced` |

Settings can also be inspected in-app with `settings`.

---

## API keys (free vs own)

| Mode | Command | Uses |
|------|---------|------|
| **Free** (default) | `apikey free` | `FREE_AI_API_KEY` → Groq by default |
| **Own** | `apikey set <KEY>` | Your key + `AI_PROVIDER` / `AI_MODEL` |
| **Mock** | `apikey mock` | Offline answers (no network) |

```text
apikey status
apikey free
apikey set gsk_or_sk_your_key
provider list
provider openai gpt-4o-mini
provider gemini gemini-2.0-flash
provider deepseek deepseek-chat
provider xai grok-2-latest
provider nvidia nvidia/llama-3.1-nemotron-70b-instruct
model llama-3.3-70b-versatile
```

Keys are stored in **`.env` only** (gitignored). Never commit them.

> If free-mode calls return `401 Invalid API Key`, rotate `FREE_AI_API_KEY` with a valid Groq (or other) key.

---

## Usage

### Meeting copilot

```text
mode meeting
meeting start
# …speak or use:
meeting inject "Why did you choose XGBoost?"
meeting status
meeting stop
```

### Screen copilot

```text
screen read
ask "summarize the error on screen"
screen analyze "why is this failing?"
screen clear
```

### Combined

```text
mode meeting+screen
meeting start
# On a directed question, context can include transcript + optional auto screen grab
```

### Personal knowledge

```text
rag add ./docs
rag add ./README.md
rag status
ask "How does authentication work in our notes?"
rag clear
```

### Hotkeys (if `pynput` available)

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+S` | Screen analyze |
| `Ctrl+Shift+M` | Toggle meeting |
| `Ctrl+Shift+V` | Listen |

---

## Commands reference

| Command | Description |
|---------|-------------|
| `help` | List commands |
| `ask "…"` | Stream an answer |
| `apikey free\|own\|set\|status\|clear\|mock` | Key mode |
| `provider list\|<name> [model]` | Select backend |
| `model [id]` | Show/set model |
| `screen read\|analyze\|clear` | Screen pipeline |
| `listen` / `listen stop` | One-shot voice Q&A |
| `meeting start\|stop\|status\|inject` | Meeting pipeline |
| `rag add\|status\|clear` | Local knowledge |
| `mode [name]` | `general`, `meeting`, `screen`, `meeting+screen`, `coding`, `study` |
| `settings` / `context` / `history` | Introspection |
| `clear` | Clear terminal view |
| `stop` | Stop TTS |
| `exit` / `quit` | Leave the app |

Bare text (unknown command) is treated as `ask`.

---

## Architecture

High-level flow:

```text
Meeting audio + Screen + User question + History + RAG
        ↓
  Context engine (mode-aware, compact package)
        ↓
  Pluggable AI provider (streaming)
        ↓
  Terminal UI  (+ optional TTS)
```

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Product vision: [docs/spec/projectinfo.txt](docs/spec/projectinfo.txt)

---

## Project structure

Professional **src layout**:

```text
bro/
├── src/bro/                 # Installable package
│   ├── __init__.py
│   ├── __main__.py          # python -m bro
│   ├── apps/desktop/        # PySide6 UI, session, hotkeys
│   ├── core/                # commands, config, context, meeting, memory
│   ├── ai/                  # providers, catalog, question detection
│   ├── audio/               # capture, VAD, STT, diarization
│   ├── vision/              # capture pipeline, OCR
│   ├── tts/                 # speech output
│   ├── rag/                 # ingest / embed / retrieve
│   ├── osplat/              # OS screen helpers (Linux/Windows)
│   └── backend/             # FastAPI app
├── tests/                   # unit + integration
├── docs/                    # architecture, MVP, tracker, product spec
├── scripts/                 # run.sh, package.sh
├── .github/                 # CI, issue/PR templates
├── main.py                  # root convenience launcher
├── pyproject.toml           # package metadata & deps
├── requirements.txt         # pip -e . helper
├── .env.example
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
└── README.md
```

---

## HTTP API

Optional service process:

```bash
export PYTHONPATH=src
uvicorn bro.backend.api.app:app --reload
```

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Liveness |
| `GET` | `/api/models` | Active model metadata |
| `GET` | `/api/settings` | Public settings (no secrets) |
| `POST` | `/api/ask` | Non-streaming Q&A |
| `POST` | `/api/tts` | Speak text |
| `POST` | `/api/transcribe` | STT metadata (desktop handles streaming mic) |

Interactive docs: `http://127.0.0.1:8000/docs`

---

## Development

```bash
source .venv/bin/activate
pip install -e ".[dev]"

# Run
python -m bro

# Lint (optional)
ruff check src tests

# Package
./scripts/package.sh
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for PR guidelines and coding standards.

---

## Testing

```bash
pytest -q
```

Tests cover command parsing, config redaction, context engine, question detection, VAD, RAG, providers, and meeting inject flows. CI runs on pull requests (see `.github/workflows/ci.yml`).

---

## Packaging

```bash
./scripts/package.sh
# → dist/*.whl, dist/*.tar.gz, dist/PACKAGING.md
```

Notes for AppImage / deb / rpm / Windows installer are in `dist/PACKAGING.md` after the script runs. Alpha focus is source + wheel installs.

---

## Privacy & security

- Capture is **opt-in** and reflected in the status bar (`MIC` / `AUDIO` / `SCREEN`)
- No hidden recording; no permanent audio/screenshot store by default
- API keys never logged in full; `.env` is gitignored
- **Not** designed to evade Google Meet, Teams, Zoom, or proctoring software

Vulnerability reporting: [SECURITY.md](SECURITY.md)

---

## Roadmap

Tracked in [docs/IMPLEMENTATION_TRACKER.md](docs/IMPLEMENTATION_TRACKER.md).

Highlights still open / partial:

- Higher-quality speaker diarization
- Polished native installers
- Stronger Wayland hotkey/capture support
- Richer FastAPI media upload endpoints

---

## Contributing

Contributions are welcome.

1. Fork + branch
2. `pip install -e ".[dev]"`
3. `pytest -q`
4. Open a PR

Please read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

---

## Community docs

| Doc | Purpose |
|-----|---------|
| [README.md](README.md) | This file |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to develop & PR |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Community standards |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [LICENSE](LICENSE) | MIT |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/MVP.md](docs/MVP.md) | MVP scope |
| [docs/IMPLEMENTATION_TRACKER.md](docs/IMPLEMENTATION_TRACKER.md) | Phase checklist |
| [docs/spec/projectinfo.txt](docs/spec/projectinfo.txt) | Full product vision |

---

## License

[MIT](LICENSE) © bro contributors

---

## Disclaimer

**bro** is an assistive tool. You are responsible for complying with workplace policies, meeting consent laws, and provider terms of service. Do not use it to cheat on exams or bypass security/monitoring software. Cloud providers may process audio/text/images according to their policies when you enable those features.
