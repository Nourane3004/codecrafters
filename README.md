CodeCrafters:
# TruthGuard — Multi-Agent Misinformation Detection Platform

TruthGuard is a **dialogue-driven content verification platform** built for the MENACRAFT hackathon. Unlike naive content moderation tools, TruthGuard first asks the user *what* the content is and *what* they need to know. This user context drives the orchestrator to selectively activate only the agents that are relevant – avoiding wasted computation and false conclusions.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Prefect](https://img.shields.io/badge/Prefect-2.0+-FF6E4A?logo=prefect)](https://www.prefect.io)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue)](#license)

---

## 🔍 What is TruthGuard?

TruthGuard detects misinformation across **images, videos, documents, URLs, and social posts** using an ensemble of 8 parallel agents. The system first asks the user to declare the *content nature* (e.g., screenshot, raw photo, meme, news article) and their *analysis goals*. This dialogue overrides naive file‑type routing – a screenshot of a tweet is never treated as “just an image”.

**Core insight:** A `image/jpeg` file could be a raw photo (→ only image forensics) or a tweet screenshot (→ image forensics + OCR + claim verification + source credibility + network analysis). TruthGuard learns this from the user, not from the file header.

### Key Design Principles

- **User‑declared content nature** overrides MIME‑type routing – the orchestrator builds its agent plan from user answers.
- **Minimum sufficient agents** – only the agents needed for the selected goals are activated.
- **Full transparency** – every activation decision is logged in plain English.
- **Graceful degradation** – agents catch exceptions internally; the pipeline never crashes due to a single failure.
- **No mock data in production** – all results are derived from real input.

---

## 🏗️ System Architecture

The pipeline runs in sequence, with the **Agent Committee executing in parallel** (via Prefect’s `ConcurrentTaskRunner`).

### 🔀 Input Router – 3 Layers

The router computes a **pipeline activation score (0–1)** for VISION, TEXT, VIDEO, URL. Any pipeline scoring ≥0.35 is activated.

| Layer | Method | What it does |
|-------|--------|---------------|
| **L1** | Magic bytes | Identifies true MIME type from binary header (prevents spoofing) |
| **L2** | Content sniffing | Inspects ambiguous text/plain to detect URLs, HTML, JSON, or prose |
| **L3** | Pipeline scoring | Rule‑based classifier that combines L1+L2 signals (threshold 0.35) |

> **Important:** The orchestrator *adds* pipelines based on user dialogue – it never removes what the router activated. A screenshot classified as VISION only will get TEXT+URL+NETWORK added when the user declares “social post screenshot”.

### ⚙️ Preprocessing Layer

Each content type is transformed into a unified `NormalizedFeatureObject` before agents run.

| Content Type | Preprocessing Steps | Key Libraries |
|--------------|---------------------|----------------|
| **Image** | OCR, EXIF metadata, ELA compression analysis, FFT spectral analysis, screenshot detection | Pillow, pytesseract, numpy |
| **Video** | Keyframe sampling, sharpness variance, luminosity flicker, face‑edge anomaly, FFT on face patches, audio transcription (Whisper stub) | OpenCV, numpy, whisper |
| **Document** | Text extraction (PDF/DOCX/TXT), heading/table parsing, author metadata | PyMuPDF, pdfplumber, python‑docx |
| **URL** | Page scraping, meta tags, WHOIS domain query, social platform fingerprinting | httpx, beautifulsoup4, python‑whois |

---

## 🤖 Agent Committee (8 Parallel Agents)

All activated agents run simultaneously using Prefect’s `ConcurrentTaskRunner`. Each agent outputs a risk score (0–1) and a confidence value.

| Agent | Weight | Role |
|-------|--------|------|
| **Claim Verifier** (RAG) | 22% | Cross‑references extracted claims against a ChromaDB fact corpus using NLI |
| **Source Credibility** | 18% | Evaluates domain age, known fake‑news lists, HTTPS, TLD, platform risk |
| **Image Forensics** | 14% | ELA, EXIF forensics, FFT spectral analysis, UI detection, OCR |
| **Video Forensics** | 14% | Sharpness variance, temporal flicker, face‑edge anomaly, FFT on faces, metadata |
| **Context Agent** | 12% | Temporal coherence, mixed tense detection, contradictory terms, Wikidata lookup |
| **Linguistic Agent** | 10% | Clickbait detection + AI‑generated text detection (statistical + LLM) |
| **Network Agent** | 10% | Bot probability, suspicious TLDs, propagation pattern classification, LLM synthesis |
| **Claim Extractor** | 0%* | Extracts structured claims (informational only – feeds Claim Verifier & Context) |

\* Claim Extractor weight = 0 because it makes no truth judgement; it only provides input to higher‑weighted agents.

### Agent Details (selected)

**Claim Verifier (RAG)** – Highest weight.  
1. Embed claim with `all-MiniLM-L6-v2`  
2. Retrieve top‑5 evidence chunks from ChromaDB  
3. LLM NLI: SUPPORTED / CONTRADICTED / INSUFFICIENT  
4. Aggregate support/contradiction scores across claims  

**Source Credibility Agent** – Signals: domain age (<30 days → high risk), known fake‑news sites, satire detection, trusted outlets, domain spoofing, suspicious TLDs (.tk, .xyz, etc.), HTTPS, platform risk (Twitter 0.55, Telegram 0.35).

**Image Forensics Agent** – Five detectors: ELA (re‑compression residuals), EXIF editing traces, FFT spectral variance (<48.0 → GAN artifact), screenshot detection (reduced colour palette), optional OCR.

---

## ⚖️ Evidence Fusion – 3 Stages

1. **Weighted Ensemble** – `weighted_avg = Σ (riskᵢ × weightᵢ × confidenceᵢ) / Σ (weightᵢ × confidenceᵢ)`
2. **Bayesian Update** – Starts from neutral prior (log‑odds = 0), each agent updates log‑odds proportionally to evidence strength. Multiple weak signals compound.
3. **Meta‑Model Blend** – `final_risk = α × ensemble + (1‑α) × bayesian` (α = 0.60). `meta_confidence` reflects reliability.

### 🎯 Decision Engine

| Risk Score | Band | Action | Human Review? |
|------------|------|--------|----------------|
| 0.00 – 0.24 | 🟢 GREEN | Auto‑allow | No |
| 0.25 – 0.49 | 🟡 AMBER | Flag review | **Yes** |
| 0.50 – 0.74 | 🟠 ORANGE | Flag review | **Yes** |
| 0.75 – 1.00 | 🔴 RED | Auto‑block | No |

---

## 🖥️ Frontend – 4‑Step Wizard

The frontend (`truthguard-v3.html`) is a self‑contained single‑file application. It communicates with the orchestrator API at `localhost:8001` and degrades gracefully to local computation if the API is unreachable.

1. **Content submission** – file upload, URL, or pasted text.  
2. **Content nature declaration** – 12 types (e.g., social post screenshot, raw photo, meme, news article). Shows expected agent pipeline for each choice.  
3. **Analysis goal selection** – 8 goals (authenticity, source credibility, claim verification, etc.). Only selected agents are activated.  
4. **Agent plan review → Run** – Displays ACTIVE/SKIP status with written reasons before execution, then live stage‑by‑stage loading.

### Why a Dialogue System?

A `image/jpeg` could be a raw photo (→ VISION only), a tweet screenshot (→ VISION+TEXT+URL+NETWORK), a meme (→ VISION+TEXT+CONTEXT), or a WhatsApp screenshot (→ VISION+TEXT+CONTEXT). Routing by MIME alone would activate only VISION in all these cases – missing the most important analysis dimensions. The dialogue system makes content nature **explicit**, and the orchestrator overrides the router accordingly.

---

## 🔌 API Reference

### Orchestrator API (`localhost:8001`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/agents` | GET | List all agents with weights & trigger conditions |
| `/analyse/plan` | POST | Preview activation plan without running |
| `/analyse` | POST | Full analysis (multipart form data) |

**Key fields for `/analyse`** (multipart/form-data):
- `file` (binary) – optional if URL mode
- `input_type` – `image` / `video` / `document` / `url`
- `content_nature` – e.g., `social_post_screenshot`
- `analysis_goals` – JSON array, e.g., `'["authenticity","source_credibility"]'`
- `source_url`, `post_text`, `platform`, `author_handle` – optional contextual fields

### Preprocessing API (`localhost:8000`)

| Endpoint | Input | Returns |
|----------|-------|---------|
| `POST /preprocess/image` | multipart image | `NormalizedFeatureObject` |
| `POST /preprocess/url` | `{"url": "..."}` | `NormalizedFeatureObject` |
| `POST /preprocess/document` | multipart PDF/DOCX/TXT | `NormalizedFeatureObject` |
| `POST /preprocess/video` | multipart video | `NormalizedFeatureObject` |

---

## 📦 Installation

### Minimal (no GPU, no OCR)
```bash
pip install fastapi uvicorn python-multipart httpx pydantic pillow pymupdf beautifulsoup4
# Core preprocessing & agents
pip install -r Preprocessing/requirements.txt

# OCR (requires Tesseract binary)
# Ubuntu: sudo apt install tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra
pip install pytesseract

# Video
# Ubuntu: sudo apt install ffmpeg
pip install opencv-python-headless openai-whisper

# RAG (Claim Verifier)
pip install sentence-transformers chromadb

# Orchestration
pip install prefect

# LLM providers (choose one or more)
pip install anthropic  # Claude
pip install groq       # Groq (LLaMA)
# Ollama: install binary separately
# 1. Preprocessing service (port 8000)
cd Preprocessing
uvicorn main:app --reload --port 8000

# 2. Orchestrator API (port 8001)
uvicorn orchestrator_api:app --reload --port 8001

# 3. Open the frontend
# Open truthguard-v3.html in any browser

codecrafters-main/
├── Preprocessing/              # FastAPI preprocessing service
│   ├── main.py                 # /preprocess/{image,url,document,video}
│   └── app/
│       ├── models/feature_object.py
│       └── pipeline/           # per‑type processors
├── Agents/                     # 8 agent modules + orchestrator + fusion
│   ├── orchestrator.py         # Prefect flow
│   ├── evidence_fusion.py      # 3‑stage fusion + DecisionEngine
│   ├── claim_extractor.py
│   ├── claim_verifier.py       # RAG + NLI
│   ├── agent_image_forensics.py
│   ├── agent_video_forensics.py
│   ├── context_agent.py
│   ├── source_cred_agent.py
│   ├── network_agent.py
│   └── linguistic_agent.py
├── Router/                     # 3‑layer content router
│   ├── router.py               # main entry
│   ├── layer1magic.py
│   ├── layer2sniff.py
│   ├── layer3classifier.py
│   └── models.py
├── orchestrator_api.py         # User‑dialogue orchestrator (port 8001)
├── chroma_db/                  # Pre‑built vector store (fact corpus)
├── truthguard-v3.html          # Frontend wizard UI
└── README.md                   # This file



🛠️ Tools & Why They Were Chosen
Tool	Purpose	Why not alternative
FastAPI	API layer	Async‑native, automatic OpenAPI docs, Pydantic validation
Prefect	Orchestration	ConcurrentTaskRunner gives true parallelism + retries + logging
Pillow	Image processing	Zero native deps, handles ELA, EXIF, pixel diffs
OpenCV	Video frame analysis	Industry standard, Haar cascades bundled, headless version available
NumPy	FFT spectral analysis	Already a transitive dependency; reveals GAN upsampling artifacts
PyMuPDF	PDF extraction	Fast, respects RTL (Arabic), layout‑aware
httpx	URL scraping	Async‑native, integrates with async/await
sentence-transformers	Claim embedding	all-MiniLM-L6-v2 – fast on CPU, 384‑dim vectors
ChromaDB	Vector store	Python‑native, persistent, no external server
Groq (LLM)	Claim extraction & NLI	500 tokens/sec on LLaMA‑3.3‑70B – real‑time inference
python-whois	Source credibility	Complete WHOIS parser for 100+ TLDs
