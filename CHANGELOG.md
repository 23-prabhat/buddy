# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-08-14

### Added

- Terminal-style desktop UI (PySide6)
- Streaming AI answers (mock + OpenAI-compatible providers)
- Free vs own API key modes (`apikey free|set|own|mock`)
- Multi-provider catalog: OpenAI, Groq, Gemini, OpenRouter, DeepSeek, xAI Grok, NVIDIA Nemotron
- Screen capture, OCR (Tesseract), optional vision analysis
- Voice listen pipeline (mic → VAD → STT)
- Meeting mode with rolling transcript and question detection
- Combined meeting + screen context routing
- Simple speaker labeling (User / Speaker A/B)
- Local RAG (hashing embeddings, file ingest)
- System tray + optional global hotkeys
- FastAPI service layer (`/api/health`, `/api/ask`, …)
- Packaging helpers (`scripts/package.sh`, wheel/sdist)
- Professional `src/bro` package layout and open-source docs

### Security

- API keys only via `.env` (gitignored)
- Explicit capture indicators; no silent recording by default
