"""ElevenLabs TTS (with word/viseme timestamps) & Groq Whisper STT service.

Uses httpx directly (zero extra SDK overhead) for maximum reliability across
Python 3.12 (Render) and Python 3.14 (local), with graceful error handling.
"""

from __future__ import annotations

import array
import base64
import hashlib
import io
import os
import re
import threading
import time
import wave
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
VOICE_VERSION = 6
DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
DEFAULT_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

MIC_LANGUAGES: Dict[str, Optional[str]] = {
    "Auto (English + Hindi)": None,
    "English": "en",
    "Hindi / Hinglish": "hi",
}

_SCRIBE_LANG_MAP: Dict[str, str] = {
    "en": "eng",
    "hi": "hin",
}

TUTOR_PERSONAS: Dict[str, Dict[str, str]] = {
    "Ms. Sarah — Warm AI Tutor": {
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "accent": "#70e5ff",
        "accent_secondary": "#a78bfa",
        "avatar_style": "sarah",
        "tagline": "Warm, reassuring & expressive teacher",
    },
    "Ms. Jessica — Natural Conversational Ma'am": {
        "voice_id": "cgSgspJ2msm6clMCkdW9",
        "accent": "#79f3c1",
        "accent_secondary": "#70e5ff",
        "avatar_style": "laura",
        "tagline": "Friendly, lively, everyday conversational voice",
    },
    "Prof. Bella — Warm Educator": {
        "voice_id": "hpp4J3VqNfWAUOO0d1Us",
        "accent": "#c084fc",
        "accent_secondary": "#70e5ff",
        "avatar_style": "alice",
        "tagline": "Warm, expressive classroom educator",
    },
    "Prof. Alice — Clear Academic Ma'am": {
        "voice_id": "Xb7hH8MSUJpSbSDYk0k2",
        "accent": "#a78bfa",
        "accent_secondary": "#70e5ff",
        "avatar_style": "alice",
        "tagline": "Structured university educator & exam coach",
    },
}

ELEVENLABS_MODELS: Dict[str, str] = {
    "Multilingual v2 (Natural Human · EN/Hindi)": "eleven_multilingual_v2",
    "Flash v2.5 (Ultra-Fast)": "eleven_flash_v2_5",
}


_HTTP_CLIENT: Optional[httpx.Client] = None


def _get_http_client() -> httpx.Client:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.Client(timeout=35.0)
    return _HTTP_CLIENT


def get_api_key() -> str:
    load_dotenv(override=False)
    return (os.getenv("ELEVENLABS_API_KEY") or "").strip()


def is_voice_configured() -> bool:
    return bool(get_api_key())


def make_cache_key(text: str, voice_id: str, model_id: str) -> str:
    digest = hashlib.sha256(f"{voice_id}|{model_id}|{text}".encode("utf-8")).hexdigest()
    return digest[:24]


def clean_text_for_speech(text: str, max_chars: int = 1100) -> str:
    """Strip Markdown, code blocks, links, and citation footers for natural TTS."""
    if not text:
        return ""

    cleaned = text.strip()
    # Drop trailing source/tip footers added for visual reading
    cleaned = re.split(r"\n---\n|\n####\s*📚|\n_Tip:", cleaned, maxsplit=1)[0]
    # Remove fenced code blocks
    cleaned = re.sub(r"```[\s\S]*?```", " See the code block on screen. ", cleaned)
    # Remove inline markdown links [label](url) -> label
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)
    # Remove bare URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    # Remove markdown formatting characters
    cleaned = re.sub(r"[#*_`~>|]+", " ", cleaned)
    # Remove decorative emojis/symbols while keeping punctuation & Devanagari/Latin text
    cleaned = re.sub(r"[\U00010000-\U0010ffff\u2600-\u27bf]", "", cleaned)
    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) <= max_chars:
        return cleaned

    # Trim cleanly at the last sentence boundary before max_chars
    window = cleaned[:max_chars]
    last_punct = max(window.rfind(". "), window.rfind("? "), window.rfind("! "))
    if last_punct > max_chars * 0.55:
        return window[: last_punct + 1].strip()
    return window.rsplit(" ", 1)[0].strip() + "."


def _char_to_viseme(ch: str) -> str:
    c = ch.lower()
    if c in "mbp":
        return "closed"
    if c in "fv":
        return "fv"
    if c in "ou":
        return "round"
    if c in "ei":
        return "wide"
    if c in "a":
        return "open"
    if c.isalpha():
        return "mid"
    return "rest"


def _parse_alignment(alignment: Optional[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Convert ElevenLabs character timestamps into word timings and compact visemes."""
    if not isinstance(alignment, dict):
        return [], []

    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    n = min(len(chars), len(starts), len(ends))
    if n == 0:
        return [], []

    words: List[Dict[str, Any]] = []
    visemes: List[Dict[str, Any]] = []

    buf: List[str] = []
    w_start: Optional[float] = None
    w_end: float = 0.0
    last_viseme: Optional[str] = None
    last_v_time: float = -1.0

    for i in range(n):
        ch = str(chars[i])
        st = float(starts[i])
        en = float(ends[i])

        v = _char_to_viseme(ch)
        if v != last_viseme and (st - last_v_time) >= 0.045:
            visemes.append({"t": round(st, 3), "v": v})
            last_viseme = v
            last_v_time = st

        if ch.isspace():
            if buf and w_start is not None:
                words.append({"w": "".join(buf), "s": round(w_start, 3), "e": round(w_end, 3)})
                buf = []
                w_start = None
        else:
            if w_start is None:
                w_start = st
            buf.append(ch)
            w_end = en

    if buf and w_start is not None:
        words.append({"w": "".join(buf), "s": round(w_start, 3), "e": round(w_end, 3)})

    if visemes:
        visemes.append({"t": round(float(ends[n - 1]), 3), "v": "rest"})

    return words, visemes


def synthesize_speech_with_timestamps(
    text: str,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
    max_chars: int = 1100,
) -> Dict[str, Any]:
    """Synthesize MP3 speech + exact word/viseme timestamps via ElevenLabs REST API."""
    api_key = get_api_key()
    spoken_text = clean_text_for_speech(text, max_chars=max_chars)
    vid = (voice_id or DEFAULT_VOICE_ID).strip()
    mid = (model_id or DEFAULT_MODEL_ID).strip()

    if not spoken_text:
        return {"ok": False, "error": "No speakable text provided.", "spoken_text": ""}

    if not api_key:
        return {
            "ok": False,
            "error": "ELEVENLABS_API_KEY is not configured. Add it in .env or Render Environment Variables.",
            "spoken_text": spoken_text,
        }

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "text": spoken_text,
        "model_id": mid,
        "voice_settings": {
            "stability": 0.35,
            "similarity_boost": 0.78,
            "style": 0.44,
            "use_speaker_boost": True,
            "speed": 0.95,
        },
    }

    try:
        client = _get_http_client()
        # 1. Preferred endpoint: audio + character-level alignment timestamps
        ts_url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{vid}/with-timestamps?output_format=mp3_44100_128"
        resp = client.post(ts_url, headers=headers, json=payload)

        if resp.status_code == 200:
            data = resp.json()
            audio_b64 = data.get("audio_base64", "")
            if audio_b64:
                audio_bytes = base64.b64decode(audio_b64)
                alignment = data.get("alignment") or data.get("normalized_alignment")
                words, visemes = _parse_alignment(alignment)
                duration = words[-1]["e"] if words else 0.0
                return {
                    "ok": True,
                    "audio_base64": audio_b64,
                    "audio_bytes": audio_bytes,
                    "words": words,
                    "visemes": visemes,
                    "spoken_text": spoken_text,
                    "duration": duration,
                    "voice_id": vid,
                    "model_id": mid,
                    "chars_used": len(spoken_text),
                    "error": None,
                }

        # 2. Fallback to standard TTS endpoint if /with-timestamps isn't available
        if resp.status_code in (400, 404, 422):
            std_url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{vid}?output_format=mp3_44100_128"
            std_headers = {**headers, "Accept": "audio/mpeg"}
            std_resp = client.post(std_url, headers=std_headers, json=payload)
            if std_resp.status_code == 200 and std_resp.content:
                audio_b64 = base64.b64encode(std_resp.content).decode("ascii")
                return {
                    "ok": True,
                    "audio_base64": audio_b64,
                    "audio_bytes": std_resp.content,
                    "words": [],
                    "visemes": [],
                    "spoken_text": spoken_text,
                    "duration": 0.0,
                    "voice_id": vid,
                    "model_id": mid,
                    "chars_used": len(spoken_text),
                    "error": None,
                }
            resp = std_resp

        # Surface clean error without ever echoing API keys
        detail = ""
        try:
            err_json = resp.json()
            detail_obj = err_json.get("detail", err_json)
            if isinstance(detail_obj, dict):
                detail = detail_obj.get("message") or str(detail_obj)
            else:
                detail = str(detail_obj)
        except Exception:
            detail = resp.text[:180]
        return {
            "ok": False,
            "error": f"ElevenLabs API error ({resp.status_code}): {detail}",
            "spoken_text": spoken_text,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Could not reach ElevenLabs service: {exc}",
            "spoken_text": spoken_text,
        }


_QUOTA_CACHE: Dict[str, Any] = {"ts": 0.0, "data": None, "loading": False}


def _refresh_quota_bg(api_key: str) -> None:
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(
                f"{ELEVENLABS_BASE_URL}/user/subscription",
                headers={"xi-api-key": api_key},
            )
            if resp.status_code == 200:
                payload = resp.json()
                used = int(payload.get("character_count", 0))
                limit = int(payload.get("character_limit", 0))
                _QUOTA_CACHE["data"] = {
                    "used": used,
                    "limit": limit,
                    "remaining": max(0, limit - used),
                    "tier": payload.get("tier", "free"),
                }
    except Exception:
        pass
    finally:
        _QUOTA_CACHE["loading"] = False


def fetch_elevenlabs_quota() -> Optional[Dict[str, Any]]:
    """Return cached ElevenLabs quota instantly and refresh in background (never blocks UI)."""
    api_key = get_api_key()
    if not api_key:
        return None
    now = time.time()
    if (now - _QUOTA_CACHE["ts"]) >= 60 and not _QUOTA_CACHE.get("loading"):
        _QUOTA_CACHE["ts"] = now
        _QUOTA_CACHE["loading"] = True
        threading.Thread(target=_refresh_quota_bg, args=(api_key,), daemon=True).start()
    return _QUOTA_CACHE["data"]


def _has_unexpected_script(text: str) -> bool:
    """Detect scripts outside English/Hindi (e.g. Japanese, Arabic/Urdu, Korean, Cyrillic, Chinese)."""
    return bool(re.search(r"[\u0600-\u06FF\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF\u0400-\u04FF]", text or ""))


def _preprocess_wav_audio(audio_bytes: bytes) -> tuple[bytes, bool]:
    """Normalize quiet laptop mic WAV volume & trim dead silence (pure stdlib, <5ms).

    Returns (cleaned_bytes, is_silent). Non-WAV audio passes through unchanged.
    """
    if not audio_bytes or not audio_bytes[:4] == b"RIFF":
        return audio_bytes, False
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            raw = wf.readframes(wf.getnframes())
        if sampwidth != 2 or not raw:
            return audio_bytes, False

        samples = array.array("h")
        samples.frombytes(raw)
        if not samples:
            return audio_bytes, True

        peak = max(abs(min(samples)), abs(max(samples)))
        # Reject near-silent recordings (room hum / accidental mic tap)
        if peak < 220:
            return audio_bytes, True

        # Trim leading/trailing dead silence (with 180ms padding so first word is never clipped!)
        thresh = max(180, int(peak * 0.05))
        step = max(1, n_channels)
        first = 0
        last = len(samples) - 1
        for i in range(0, len(samples), step):
            if abs(samples[i]) >= thresh:
                first = i
                break
        for i in range(len(samples) - 1, -1, -step):
            if abs(samples[i]) >= thresh:
                last = i
                break
        pad = int(framerate * 0.18) * n_channels
        start_i = max(0, first - pad)
        end_i = min(len(samples), last + pad)
        if end_i > start_i:
            # Align to channel frame boundary
            start_i -= start_i % n_channels
            end_i -= end_i % n_channels
            samples = samples[start_i:end_i]

        # Gentle peak normalization (boosts quiet laptop mics cleanly without clipping)
        if peak < 24000:
            gain = min(6.5, 26000.0 / max(1, peak))
            samples = array.array("h", (max(-32767, min(32767, int(s * gain))) for s in samples))

        out_buf = io.BytesIO()
        with wave.open(out_buf, "wb") as wf_out:
            wf_out.setnchannels(n_channels)
            wf_out.setsampwidth(2)
            wf_out.setframerate(framerate)
            wf_out.writeframes(samples.tobytes())
        return out_buf.getvalue(), False
    except Exception:
        return audio_bytes, False


def _run_elevenlabs_scribe(audio_bytes: bytes, filename: str, language: Optional[str]) -> Optional[Dict[str, Any]]:
    """Primary STT: ElevenLabs Scribe v2 (top-tier Indian English + Hindi + Hinglish accuracy)."""
    api_key = get_api_key()
    if not api_key:
        return None
    mime = "audio/wav" if filename.lower().endswith(".wav") else "audio/mpeg"
    data: Dict[str, str] = {
        "model_id": "scribe_v2",
        "tag_audio_events": "false",
    }
    if language and language in _SCRIBE_LANG_MAP:
        data["language_code"] = _SCRIBE_LANG_MAP[language]
    try:
        client = _get_http_client()
        resp = client.post(
            f"{ELEVENLABS_BASE_URL}/speech-to-text",
            headers={"xi-api-key": api_key},
            data=data,
            files={"file": (filename, audio_bytes, mime)},
        )
        if resp.status_code == 200:
            payload = resp.json()
            text = (payload.get("text") or "").strip()
            lang = (payload.get("language_code") or "").lower()
            prob = float(payload.get("language_probability") or 1.0)
            return {"text": text, "language": lang, "prob": prob, "engine": "elevenlabs_scribe_v2"}
    except Exception:
        pass
    return None


def _run_whisper(client: Any, audio_bytes: bytes, filename: str, language: Optional[str]) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "model": "whisper-large-v3",
        "file": (filename, audio_bytes),
        "response_format": "verbose_json",
        "temperature": 0.0,
    }
    if language:
        kwargs["language"] = language
    result = client.audio.transcriptions.create(**kwargs)
    text = (getattr(result, "text", "") or "").strip()
    segments = getattr(result, "segments", None) or []
    detected_lang = (getattr(result, "language", "") or "").lower()
    probs = []
    for seg in segments:
        p = seg.get("no_speech_prob") if isinstance(seg, dict) else getattr(seg, "no_speech_prob", None)
        if isinstance(p, (int, float)):
            probs.append(float(p))
    avg_no_speech = (sum(probs) / len(probs)) if probs else 0.0
    return {"text": text, "language": detected_lang, "no_speech_prob": avg_no_speech, "engine": "groq_whisper_v3"}


def transcribe_audio_bytes(
    audio_bytes: bytes,
    filename: str = "question.wav",
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """High-accuracy voice transcription: WAV normalization -> ElevenLabs Scribe v2 -> Groq Whisper fallback.

    Specifically hardened for Indian English, Hindi, and Hinglish in noisy rooms:
    - Peak-normalizes quiet laptop mic audio & trims silence
    - Primary: ElevenLabs Scribe v2 (dramatically higher Hindi/Hinglish accuracy)
    - Rejects foreign-language misdetections (Japanese/Spanish/Urdu/Korean) and retries in Hindi/English
    - Falls back automatically to Groq whisper-large-v3 if Scribe is unavailable
    """
    if not audio_bytes or len(audio_bytes) < 2200:
        return {"ok": False, "text": "", "error": "Recording was too short. Please tap the mic and speak clearly."}

    clean_bytes, is_silent = _preprocess_wav_audio(audio_bytes)
    if is_silent:
        return {"ok": False, "text": "", "error": "Mic was too quiet — please speak a little closer to the mic."}

    junk = {
        "", "...", ".", ",", "you", "you.", "thank you.", "thank you",
        "thanks for watching.", "thank you for watching.", "bye.", "mbc",
        "gracias.", "gracias", "subtitles by",
    }

    # 1. Try ElevenLabs Scribe v2 first (best-in-class English + Hindi + Hinglish)
    scribe = _run_elevenlabs_scribe(clean_bytes, filename, language)
    if scribe and scribe["text"]:
        text = scribe["text"]
        lang = scribe["language"]
        # Guard against Scribe picking an unrelated language (e.g. Spanish/Japanese/Urdu) in room noise
        if not language and (_has_unexpected_script(text) or (lang and lang not in {"eng", "en", "hin", "hi"})):
            retry = _run_elevenlabs_scribe(clean_bytes, filename, "hi")
            if retry and retry["text"] and not _has_unexpected_script(retry["text"]):
                scribe = retry
                text = scribe["text"]
        if text.lower().strip() not in junk and len(text.strip()) >= 2:
            return {"ok": True, "text": text, "language": scribe["language"], "engine": scribe["engine"], "error": None}

    # 2. Fallback to Groq whisper-large-v3
    try:
        from rag_chain import get_llm

        client = get_llm()
        out = _run_whisper(client, clean_bytes, filename, language)
        text = out["text"]
        lang = out["language"]

        if not language and (_has_unexpected_script(text) or (lang and lang not in {"english", "hindi", "en", "hi"})):
            retry = _run_whisper(client, clean_bytes, filename, "hi")
            if retry["text"] and not _has_unexpected_script(retry["text"]):
                out = retry
                text = out["text"]

        if out["no_speech_prob"] > 0.78 and len(text.split()) <= 5:
            return {"ok": False, "text": "", "error": "Too much background noise — please speak closer to the mic."}
        if text.lower().strip() in junk or len(text.strip()) < 2:
            return {"ok": False, "text": "", "error": "Could not hear clear speech. Please try again."}

        return {"ok": True, "text": text, "language": out.get("language", ""), "engine": out["engine"], "error": None}
    except Exception as exc:
        return {"ok": False, "text": "", "error": f"Speech transcription failed: {exc}"}
