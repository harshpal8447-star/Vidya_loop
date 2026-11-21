<div align="center">

<img src="assets/vidyaloop_logo.png" alt="VidyaLoop Logo — Learn, Practice, Improve, Repeat." width="380" />

<h1>VidyaLoop</h1>

<p><strong><em>Learn, Practice, Improve, Repeat.</em></strong></p>

<p>
  An interactive, voice-enabled <strong>AI Virtual Classroom &amp; Evidence-Grounded RAG Study Suite</strong><br/>
  that transforms your PDFs, PowerPoint decks (<code>.pptx</code>), Word docs, and notes into a natural bilingual AI teacher.
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+" />
  <img src="https://img.shields.io/badge/Streamlit-1.40%2B-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/ElevenLabs-Scribe%20v2%20%26%20Multilingual%20v2-111827?style=for-the-badge&logo=audiomack&logoColor=70e5ff" alt="ElevenLabs" />
  <img src="https://img.shields.io/badge/Groq-GPT--OSS--120B-F55036?style=for-the-badge&logo=lightning&logoColor=white" alt="Groq LLM" />
  <img src="https://img.shields.io/badge/RAG-BM25--IDF%20%2B%20Local%20Vector%20Store-7C3AED?style=for-the-badge" alt="BM25-IDF Local RAG" />
  <img src="https://img.shields.io/badge/Deploy-Render%20Blueprint-46E3B7?style=for-the-badge&logo=render&logoColor=060b16" alt="Render Ready" />
  <img src="https://img.shields.io/badge/Team-GenX%20AI-0EA5E9?style=for-the-badge" alt="Team GenX AI" />
</p>

<p>
  <a href="#problem-solution">Problem &amp; Solution</a> &nbsp;&bull;&nbsp;
  <a href="#ai-virtual-tutor">AI Virtual Tutor</a> &nbsp;&bull;&nbsp;
  <a href="#learning-cycle">Learning Loop</a> &nbsp;&bull;&nbsp;
  <a href="#system-architecture">Architecture</a> &nbsp;&bull;&nbsp;
  <a href="#voice-pipeline">Voice Flow</a> &nbsp;&bull;&nbsp;
  <a href="#study-suite">15-Module Suite</a> &nbsp;&bull;&nbsp;
  <a href="#benchmarks">Benchmarks</a> &nbsp;&bull;&nbsp;
  <a href="#quick-start">Quick Start</a> &nbsp;&bull;&nbsp;
  <a href="#team-genx-ai">Team GenX AI</a>
</p>

</div>

---

## 🌟 Executive Overview

Students today juggle hundreds of pages across lecture PDFs, PowerPoint slides, scanned handouts, and scattered revision notes. Generic AI chatbots frequently **hallucinate outside the syllabus**, speak in **walls of silent, overly technical text**, struggle with **Indian English & Hinglish voice queries**, and provide **no closed-loop practice or mastery tracking**.

**VidyaLoop** closes that gap end-to-end. Upload your course material once—VidyaLoop indexes every page and slide locally into a fast **BM25-IDF hybrid vector store**, pairs it with a **borderless animated 3D AI Virtual Tutor (Ma'am)** powered by **ElevenLabs** and **Groq**, verifies every answer against **verbatim source quotes with 1-click page/slide previews**, and guides learners through a continuous **Learn → Practice → Improve → Repeat** cycle.

---

<a id="ai-virtual-tutor"></a>
## 👩‍🏫 AI Virtual Tutor (Ma'am)

<table>
  <tr>
    <td width="310" align="center" valign="middle">
      <img src="assets/tutor_idle.webp" alt="VidyaLoop Animated AI Virtual Tutor (Ma'am)" width="275" />
      <br/>
      <sub><em>Borderless 3D AI Teacher seamlessly blended onto the dark classroom stage</em></sub>
    </td>
    <td valign="top">
      <h3>Interactive Voice-to-Voice Classroom</h3>
      <ul>
        <li><strong>Continuous Alpha-Blended Lip-Sync:</strong> 4 pixel-locked feathered WebP frames (<code>idle</code>, <code>blink</code>, <code>mid</code>, <code>open</code>) driven at 60fps by ElevenLabs character/viseme timestamps—zero frame pop, zero torso wobble, organic breathing, and 175ms sine-eased natural blinking.</li>
        <li><strong>Real-Time Speech-Bubble Captions:</strong> Floating student &amp; teacher dialogue bubbles highlight words in sync with Ma'am's voice alongside a 72-bar reactive audio aura.</li>
        <li><strong>Natural Bilingual Teaching (English &amp; Hinglish):</strong> Speak in English, Hindi, or natural Hinglish—Ma'am detects your language automatically and explains concepts simply with human pauses, warm pacing, and zero robotic jargon.</li>
        <li><strong>4 Selectable Teacher Personas:</strong> Switch instantly between <code>Ms. Sarah</code> (default), <code>Ms. Jessica</code>, <code>Prof. Bella</code>, and <code>Prof. Alice</code>, or toggle <code>Multilingual v2</code> (expressive human voice) and <code>Flash v2.5</code> (ultra-low latency).</li>
        <li><strong>Session History &amp; Instant Replay:</strong> Revisit past Q&amp;As in the top-right History drawer and replay cached audio lessons with zero extra API calls.</li>
        <li><strong>Evidence-Backed Slide &amp; Page Previews:</strong> Every syllabus lesson includes verified verbatim quotes and inline rendered PDF pages or PowerPoint slides.</li>
      </ul>
    </td>
  </tr>
</table>

---

<a id="problem-solution"></a>
## 🎯 The Problem & Our Solution

| Dimension | ❌ Traditional Studying & Generic Chatbots | ✅ VidyaLoop (*Learn, Practice, Improve, Repeat.*) |
| :--- | :--- | :--- |
| **Syllabus Accuracy** | Generic LLMs hallucinate facts or answer outside university curricula without proof. | **Strict Evidence-Grounded RAG** with verbatim quote verification, relevance gating, and inline PDF page / PPTX slide previews. |
| **Student Experience** | Passive reading of dense 200-page PDFs or silent walls of AI text. | **Full-screen Animated AI Tutor (Ma'am)** with expressive voice narration, real-time lip-sync, and conversational speech bubbles. |
| **Voice & Language Barrier** | Speech recognition breaks on Indian accents, quiet mics, and Hindi-English code-switching. | **WAV Peak Normalization + ElevenLabs Scribe v2** with anti-wrong-language guard, phonetic ASR repair, and **Hindi-to-English RAG search bridge**. |
| **Multi-Format Notes** | Most tools only handle plain text or basic PDFs, ignoring slide decks and scanned notes. | Native ingestion for **PDF (digital + Tesseract OCR fallback), PowerPoint (`.pptx`), Word (`.docx`), and `.txt`** files. |
| **Closed-Loop Retention** | Answering one question gives no insight into weak topics or exam readiness. | Integrated **Interactive Quizzes, 2/5/7/10-Mark Exam Mode, Weak-Topic Detection, Knowledge Maps, Smart Notes & Study Planner** saved per user in SQLite. |
| **Zero-Friction Deployment** | Heavy external vector DBs (Pinecone/Chroma servers) break free-tier hosting. | **100% self-contained local JSON BM25-IDF vector index + SQLite**—runs locally or deploys in 1 click on **Render Free Tier** (`render.yaml`). |

---

<a id="learning-cycle"></a>
## 🔁 The VidyaLoop Learning Cycle

```mermaid
flowchart LR
    classDef learn fill:#0f2942,stroke:#70e5ff,stroke-width:2px,color:#eaf5ff
    classDef practice fill:#22174a,stroke:#a78bfa,stroke-width:2px,color:#eaf5ff
    classDef improve fill:#0f332c,stroke:#79f3c1,stroke-width:2px,color:#eaf5ff
    classDef repeat fill:#361c3d,stroke:#f472b6,stroke-width:2px,color:#eaf5ff

    L["1. LEARN<br/>Upload PDF / PPTX / DOCX<br/>AI Virtual Tutor Ma'am<br/>Teach Me & Smart Notes"]:::learn
    P["2. PRACTICE<br/>Interactive MCQ Quizzes<br/>2 / 5 / 7 / 10-Mark Exam Mode<br/>Question Bank Generator"]:::practice
    I["3. IMPROVE<br/>Weak-Topic Detection<br/>Where Did I Learn This?<br/>Cross-Doc Compare & Proof"]:::improve
    R["4. REPEAT<br/>Adaptive Study Planner<br/>Concept Knowledge Map<br/>My Memory & Progress Analytics"]:::repeat

    L -->|"Build Grounded Understanding"| P
    P -->|"Score & Diagnose Gaps"| I
    I -->|"Target Weak Concepts"| R
    R -->|"Continuous Mastery Loop"| L
```

---

<a id="system-architecture"></a>
## 🏗️ System Architecture

```mermaid
flowchart TB
    classDef client fill:#0c1c30,stroke:#70e5ff,stroke-width:2px,color:#eaf5ff
    classDef voice fill:#1f163b,stroke:#c084fc,stroke-width:2px,color:#eaf5ff
    classDef rag fill:#0e2e2a,stroke:#79f3c1,stroke-width:2px,color:#eaf5ff
    classDef llm fill:#331d12,stroke:#fb923c,stroke-width:2px,color:#eaf5ff
    classDef store fill:#172033,stroke:#94a3b8,stroke-width:2px,color:#eaf5ff

    subgraph UI["Frontend & Virtual Classroom (Streamlit - app.py)"]
        direction LR
        Mic["Voice Mic Input<br/>st.audio_input WAV"]:::client
        Text["Text Query & 15 Study Modules<br/>Vault - Quiz - Exam - Planner"]:::client
        Stage["Animated 3D Avatar Stage<br/>tutor_avatar.py - 4 WebP Frames<br/>Lip-Sync + Speech Bubbles + 72-Bar Aura"]:::client
        Preview["Evidence & Proof Renderer<br/>Inline PDF Page / PPTX Slide Viewer"]:::client
    end

    subgraph Ingestion["Multi-Format Document Ingestion (ingest.py & utils.py)"]
        direction LR
        Docs["PDF - PPTX - DOCX - TXT<br/>uploads/"]:::store
        Parser["PyMuPDF + Tesseract OCR<br/>python-pptx - docx2txt"]:::rag
        Embed["LocalHashEmbeddings +<br/>BM25-IDF + Bigram Indexer"]:::rag
    end

    subgraph VoiceIn["Voice Capture & ASR Pipeline (voice_service.py)"]
        direction LR
        Clean["Stdlib WAV Cleaner<br/>Peak Normalization & Silence Trim"]:::voice
        Scribe["Primary STT: ElevenLabs scribe_v2<br/>Anti-Wrong-Language Guard"]:::voice
        Whisper["Fallback STT: Groq<br/>whisper-large-v3"]:::voice
    end

    subgraph Intelligence["Grounded RAG & Tutor Intelligence (rag_chain.py)"]
        direction LR
        Repair["Query Repair & Hindi-to-EN Bridge<br/>Groq openai/gpt-oss-20b"]:::llm
        Search["BM25-IDF + Exact-Word +<br/>Cosine Hybrid Retriever"]:::rag
        Gate["Relevance Gate & Grounded Tutor<br/>Groq openai/gpt-oss-120b"]:::llm
        Verify["Verbatim Citation Verifier &<br/>Natural Hinglish/EN Formatter"]:::rag
    end

    subgraph VoiceOut["Expressive Voice Synthesis (voice_service.py)"]
        TTS["ElevenLabs TTS /with-timestamps<br/>eleven_multilingual_v2 / flash_v2_5<br/>Audio Base64 + Word & Viseme Timings"]:::voice
    end

    subgraph Storage["Zero-Ops Local Persistence"]
        direction LR
        Index[("Local Vector Index<br/>db/second_brain_index.json<br/>2,332 Pre-Indexed Chunks")]:::store
        SQLite[("SQLite User & Analytics DB<br/>users.db - auth.py & db_manager.py<br/>bcrypt - Quizzes - Notes - Plans")]:::store
    end

    Docs --> Parser --> Embed --> Index
    Mic --> Clean --> Scribe
    Scribe -.->|"Automatic Fallback"| Whisper
    Scribe --> Repair
    Whisper --> Repair
    Text --> Repair
    Repair --> Search
    Index --> Search
    Search --> Gate --> Verify
    Verify --> TTS --> Stage
    Verify --> Preview
    Text <--> SQLite
    Verify --> SQLite
```

---

<a id="voice-pipeline"></a>
## 🎙️ Voice-to-Voice Pipeline

Every voice turn passes through a resilient, latency-optimized pipeline engineered specifically for real student microphones and bilingual English/Hinglish speech:

```mermaid
sequenceDiagram
    autonumber
    actor Student as Student (Browser Mic)
    participant App as Streamlit Classroom (app.py)
    participant Voice as Voice Service (voice_service.py)
    participant RAG as Grounded RAG (rag_chain.py + ingest.py)
    participant Avatar as 3D AI Tutor Ma'am (tutor_avatar.py)

    Student->>App: Speaks question (English, Hindi, or Hinglish)
    App->>Voice: Raw WAV audio bytes + mic language hint
    Voice->>Voice: Peak-normalize volume & trim leading/trailing silence
    Voice->>Voice: Transcribe via ElevenLabs scribe_v2 (fallback: Groq whisper-large-v3)
    Note over Voice: Anti-wrong-language guard retries in Hindi<br/>if accidental foreign script is detected
    Voice-->>App: Clean transcript text

    App->>RAG: Transcript + selected source filter + chat history
    alt Casual Greeting / Small Talk
        RAG-->>App: Warm, natural conversational reply (no forced citations)
    else Academic / Syllabus Question
        RAG->>RAG: Phonetic ASR typo repair + Hindi-to-EN search query (gpt-oss-20b)
        RAG->>RAG: BM25-IDF + exact-word + bigram retrieval from local index
        RAG->>RAG: Relevance gating + grounded lesson generation (gpt-oss-120b)
        RAG->>RAG: Verify verbatim source quotes against retrieved chunks
        RAG-->>App: Structured lesson + natural spoken script + citations
    end

    App->>Voice: Spoken script + selected Ma'am voice & model
    Voice->>Voice: ElevenLabs /with-timestamps (eleven_multilingual_v2)
    Voice-->>App: MP3 Base64 + word timestamps + mouth viseme curves

    App->>Avatar: Render full-screen stage (audio + words + visemes + bubbles)
    Avatar-->>Student: 60fps lip-synced Ma'am + live speech bubbles + inline page/slide proof
```

---

<a id="study-suite"></a>
## 📚 15-Module Study Suite

VidyaLoop ships as a unified learning workspace with **15 interactive views** persisted per authenticated student account:

| # | Module | Purpose & Key Capabilities |
| :-: | :--- | :--- |
| **1** | **👩‍🏫 AI Virtual Tutor** | Full-screen borderless animated AI teacher (Ma'am) with voice-to-voice mic, natural English/Hinglish replies, real-time speech-bubble captions, 4 personas, cached History Replay, and inline source page/slide previews. |
| **2** | **🏠 Student Dashboard** | Live telemetry of questions asked, quizzes completed, average score, weak topics, saved memories, active study plan progress, and recent learning activity. |
| **3** | **💬 Ask VidyaLoop** | Multi-turn grounded RAG chat across all or selected documents with verbatim quote verification, source citations, and instant document previews. |
| **4** | **📍 Where Did I Learn This?** | Reverse-lookup any concept across your entire uploaded library to pinpoint exact document names, page/slide numbers, matching excerpts, and rendered visual previews. |
| **5** | **🎓 Teach Me Mode** | Step-by-step conceptual breakdowns tailored to beginner, intermediate, or exam-ready clarity with optional ElevenLabs voice playback. |
| **6** | **🎯 Exam Mode** | Generates structured university **2-mark, 5-mark, 7-mark, and 10-mark** answers grounded in your syllabus with marking-scheme bullet clarity and voice narration. |
| **7** | **🧪 Interactive Quiz** | Document-grounded MCQ assessments with instant grading, per-question explanations, source references, automatic **weak-topic tracking**, and score history. |
| **8** | **❓ Question Generator** | Creates curated short-answer, conceptual, and long-answer practice question banks directly from uploaded chapters or decks. |
| **9** | **📝 Smart Notes** | Distills lengthy PDFs and PowerPoint decks into crisp revision sheets, definitions, key takeaways, and bulleted summaries. |
| **10** | **⚖️ Compare Documents** | Side-by-side structured comparison across two or more uploaded sources to highlight similarities, differences, and overlapping concepts. |
| **11** | **🗺️ Knowledge Map** | Extracts a structured concept graph (topics, sub-concepts, and directional relationships) directly from your uploaded material. |
| **12** | **📅 Study Planner** | Builds a personalized day-by-day revision schedule based on exam date and daily study hours with interactive task check-offs saved to SQLite. |
| **13** | **🧠 My Memory** | Personal searchable note vault for saving formulas, insights, and reminders with tags and keyword filtering. |
| **14** | **📂 Document Vault** | Upload, inspect, preview, and index new `.pdf`, `.pptx`, `.docx`, and `.txt` files on the fly; includes 4 pre-indexed sample study documents out of the box. |
| **15** | **⚙️ Settings & Voice Studio** | Configure AI Tutor voice persona, ElevenLabs model (`Multilingual v2` vs `Flash v2.5`), microphone language mode, and live API/quota diagnostics. |

---

<a id="benchmarks"></a>
## ⚡ Engineering Highlights & Benchmarks

Every layer of VidyaLoop was profiled and hardened for real-world classroom reliability and fast interactive response:

| Engineering Focus | Implementation Detail | Measurable Impact |
| :--- | :--- | :--- |
| **Zero-Stall Cold Boot** | Replaced heavy top-level `langchain_core` imports with a lightweight native `Document` class and lazy-loaded file parsers (`ingest.py`, `rag_chain.py`). | Cold import dropped from **26.4s → ~1.05s** (**25× speedup**) |
| **Instant View Navigation** | Single-rerun `on_click` sidebar callbacks, non-blocking background ElevenLabs quota check thread, persistent `httpx.Client` pooling, and native system typography. | All 15 modules render in **~185–210 ms** per switch |
| **High-Precision Local RAG** | Custom **BM25-IDF + exact word-boundary regex + bigram phrase scoring** with mtime-cached JSON index loading (`ingest.py`). | Eliminates substring false positives across **2,332 chunks**; zero external vector DB cost |
| **Bilingual Voice Accuracy** | Pure-stdlib WAV peak normalization & silence trimming + **ElevenLabs `scribe_v2`** + anti-wrong-language guard + Groq `whisper-large-v3` fallback + fast `gpt-oss-20b` phonetic repair & Hindi-to-English search bridge. | Reliably understands quiet mics, Indian accents, and Hinglish code-switched queries |
| **Zero-Hallucination Grounding** | LLM relevance gating separates casual/general queries from syllabus lookups, followed by strict verbatim substring verification against retrieved document chunks. | Prevents unrelated textbook chunks from bleeding into general questions |
| **Expressive Human Prosody** | Tuned ElevenLabs `eleven_multilingual_v2` voice parameters (`stability: 0.35`, `similarity_boost: 0.78`, `style: 0.44`, `speed: 0.95`, `use_speaker_boost: true`) + conversational pause formatting. | Natural classroom cadence instead of flat robotic text reading |
| **Cross-Platform Portability** | Cross-platform Windows/POSIX path normalization in `utils.py` & `ingest.py`. | Pre-indexed vaults created on Windows run seamlessly on Linux / Render Free Tier |

---

## 🛠️ Technology Stack

| Layer | Technology | Role in VidyaLoop |
| :--- | :--- | :--- |
| **Frontend & UI** | `Streamlit 1.40+`, Custom HTML5/CSS3/JS Canvas | 15-module dark-mode classroom UI, interactive widgets, and full-screen avatar stage (`app.py`, `tutor_avatar.py`) |
| **Speech-to-Text (ASR)** | **ElevenLabs `scribe_v2`** + **Groq `whisper-large-v3`** fallback | High-accuracy multilingual voice transcription with WAV preprocessing and language guard (`voice_service.py`) |
| **Text-to-Speech & Lip-Sync** | **ElevenLabs `eleven_multilingual_v2`** & **`eleven_flash_v2_5`** (`/with-timestamps`) | Natural human voice synthesis returning synchronized audio + word/viseme timestamps (`voice_service.py`) |
| **LLM Reasoning & Repair** | **Groq API** (`openai/gpt-oss-120b` & `openai/gpt-oss-20b`) | Grounded lesson synthesis, exam/quiz generation, fast ASR phonetic repair & Hindi-to-English bridging (`rag_chain.py`) |
| **Retrieval & Indexing** | Custom **BM25-IDF + Exact-Word + Bigram + `LocalHashEmbeddings`** | Fast, dependency-light local vector store persisted in `db/second_brain_index.json` (`ingest.py`) |
| **Document Parsing & OCR** | `PyMuPDF (fitz)`, `pytesseract`, `python-pptx`, `docx2txt`, `Pillow` | Multi-format ingestion & high-DPI inline page/slide preview rendering (`ingest.py`, `utils.py`, `app.py`) |
| **Auth & Persistence** | `SQLite3`, `bcrypt` | Secure password hashing + per-user memories, quiz stats, weak topics, study plans, and logs (`auth.py`, `db_manager.py`) |
| **Cloud Deployment** | **Render Blueprint** (`render.yaml`, Python `3.12.8`) | 1-click free-tier web service deployment with `/_stcore/health` checks |

---

## 📁 Repository Structure

```text
Vidya_loop/
├── app.py                                # Main Streamlit application & 15-module UI router
├── rag_chain.py                          # Grounded RAG engine, bilingual tutor, quiz/exam/notes & quote verifier
├── voice_service.py                      # WAV cleaner, ElevenLabs Scribe v2 STT, Multilingual v2 TTS & visemes
├── tutor_avatar.py                       # Borderless 3D AI Ma'am stage, 60fps alpha-blended lip-sync & captions
├── ingest.py                             # Multi-format ingestion (PDF/OCR/PPTX/DOCX/TXT) & BM25-IDF vector store
├── auth.py                               # bcrypt authentication & SQLite user initialization
├── db_manager.py                         # Per-user SQLite analytics (memories, quiz history, study plans, logs)
├── utils.py                              # Cross-platform path resolver, slide/page labels & document helpers
├── test.py                               # Quick Hinglish/English BM25-IDF retrieval smoke test
├── render.yaml                           # Render Free-Tier Blueprint deployment config (Python 3.12.8)
├── requirements.txt                      # Lightweight 13-package runtime dependency list
├── .env.example                          # Template for required environment variables (no secrets committed)
├── .streamlit/
│   └── config.toml                       # Dark classroom theme, headless server & 100MB upload config
├── assets/
│   ├── vidyaloop_logo.png                # Brand hero logo
│   ├── vidyaloop_icon.png                # App favicon & sidebar badge
│   ├── tutor_idle.webp                   # Animated Ma'am frame 1 (idle)
│   ├── tutor_blink.webp                  # Animated Ma'am frame 2 (natural eye blink)
│   ├── tutor_mid.webp                    # Animated Ma'am frame 3 (mid-articulation)
│   └── tutor_open.webp                   # Animated Ma'am frame 4 (open-vowel articulation)
├── db/
│   └── second_brain_index.json           # Pre-indexed local BM25-IDF vector store (2,332 chunks)
├── uploads/                              # Pre-loaded sample PDFs for instant out-of-the-box demos
│   ├── Cyber Security Unit-1.pdf
│   ├── Cyber_Security_Unit-3__BCC-301_.pdf
│   ├── Bhagavad-gita.pdf
│   └── dhani Part A.pdf
├── VidyaLoop_GenX_AI_Presentation.pptx   # 5-slide official Team GenX AI project pitch deck
└── README.md                             # Project documentation & visual architecture guide
```

---

<a id="quick-start"></a>
## 🚀 Quick Start

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/harshpal8447-star/Vidya_loop.git
cd Vidya_loop
python -m venv .venv
```

Activate the virtual environment and install the slim 13-package dependency list:

```bash
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# macOS / Linux
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and add your API keys (**`.env` is gitignored and never committed**):

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `GROQ_API_KEY` | **Yes** | — | Groq Cloud API key for grounded reasoning (`openai/gpt-oss-120b`), query repair (`openai/gpt-oss-20b`), and fallback STT (`whisper-large-v3`). |
| `ELEVENLABS_API_KEY` | **Yes** *(for voice)* | — | ElevenLabs API key powering `scribe_v2` speech recognition and expressive `eleven_multilingual_v2` / `eleven_flash_v2_5` lip-synced TTS. |
| `ELEVENLABS_VOICE_ID` | Optional | `EXAVITQu4vr4xnSDxMaL` | Default AI Tutor voice (`Ms. Sarah`). |
| `ELEVENLABS_MODEL_ID` | Optional | `eleven_multilingual_v2` | Default TTS model (`eleven_multilingual_v2` or `eleven_flash_v2_5`). |
| `GROQ_MODEL` | Optional | `openai/gpt-oss-120b` | Primary Groq LLM used for RAG lessons, quizzes, and exam answers. |

### 3. Verify RAG Retrieval & Launch VidyaLoop

```bash
# Optional: verify Hinglish/English BM25-IDF retrieval against the pre-indexed vault
python test.py

# Launch the VidyaLoop Virtual Classroom
streamlit run app.py
```

Open **http://localhost:8501** in your browser, create an account on the local sign-in screen (`users.db` initializes automatically on first run), and start learning!

---

## ☁️ One-Click Deployment on Render (Free Tier)

VidyaLoop includes a production-ready [`render.yaml`](render.yaml) Blueprint:

1. Fork or connect **`harshpal8447-star/Vidya_loop`** in the **Render Dashboard** (**New + → Blueprint**).
2. Render automatically configures `vidyaloop-ai-tutor` with **Python `3.12.8`**, headless Streamlit flags, and `/_stcore/health` probes.
3. Enter your `GROQ_API_KEY` and `ELEVENLABS_API_KEY` secrets when prompted and click **Apply**.
4. Your live classroom boots immediately with the pre-indexed knowledge vault ready to demo—no external database provisioning needed.

---

## 📊 Presentation & Future Roadmap

* **Pitch Deck:** Download or view our 5-slide presentation right in this repo → [`VidyaLoop_GenX_AI_Presentation.pptx`](VidyaLoop_GenX_AI_Presentation.pptx)
* **Planned Enhancements:**
  * 🔐 **Google OAuth 2.0 Sign-In** for frictionless 1-click student onboarding.
  * 📧 **Automated Gmail Study Reminders** notifying students of pending syllabus targets, scheduled quizzes, and weak-topic revisions.
  * 👥 **Collaborative Study Rooms** allowing peer groups to share curated document vaults and quiz leaderboards.

---

<a id="team-genx-ai"></a>
## 👥 Team GenX AI

<div align="center">

| Team Member | Team | Project |
| :--- | :---: | :---: |
| **Harsh Pal** | **GenX AI** | VidyaLoop |
| **Dhani Varshney** | **GenX AI** | VidyaLoop |
| **Dipika Mourya** | **GenX AI** | VidyaLoop |
| **Ansh Kumar** | **GenX AI** | VidyaLoop |

<br/>

**VidyaLoop** — *Learn, Practice, Improve, Repeat.*<br/>
Built with ❤️ by **Team GenX AI**

</div>
