"""Borderless Full-Screen Animated AI Teacher (Ma'am) with Smooth Morphing Lip-Sync & Natural Motion.

Uses 4 pixel-locked feathered WebP frames (idle, blink, speak-mid, speak-open)
with continuous layered alpha-blending (zero flicker/pop), calm grounded posture
(zero torso wobble), organic breathing, subtle speaking micro-nods, soft 72-bar
voice aura, and floating conversational caption bubbles.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, Optional

import streamlit as st
import streamlit.components.v1 as components

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
AVATAR_VERSION = 3
_FRAME_CACHE: Optional[Dict[str, str]] = None


def _load_frames_b64() -> Dict[str, str]:
    """Load & cache the 4 feathered WebP animation frames once in memory."""
    global _FRAME_CACHE
    if _FRAME_CACHE is not None:
        return _FRAME_CACHE
    frames: Dict[str, str] = {}
    mapping = {
        "idle": "tutor_idle.webp",
        "blink": "tutor_blink.webp",
        "mid": "tutor_mid.webp",
        "open": "tutor_open.webp",
    }
    for key, filename in mapping.items():
        path = os.path.join(ASSETS_DIR, filename)
        if os.path.exists(path):
            with open(path, "rb") as f:
                frames[key] = "data:image/webp;base64," + base64.b64encode(f.read()).decode("ascii")
        else:
            frames[key] = ""
    _FRAME_CACHE = frames
    return frames


def _safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def render_tutor_stage(
    persona_name: str,
    persona_meta: Dict[str, str],
    lesson: Dict[str, Any],
    audio_payload: Optional[Dict[str, Any]] = None,
    user_question: str = "",
    autoplay: bool = True,
    height: int = 560,
) -> None:
    """Render the full-screen borderless animated Ma'am AI teacher with speech-bubble captions."""
    frames = _load_frames_b64()
    accent = persona_meta.get("accent", "#70e5ff")
    accent2 = persona_meta.get("accent_secondary", "#a78bfa")

    spoken_text = (audio_payload or {}).get("spoken_text") or lesson.get("spoken_script", "")
    audio_b64 = (audio_payload or {}).get("audio_base64") or ""
    words = (audio_payload or {}).get("words") or []
    visemes = (audio_payload or {}).get("visemes") or []
    audio_ok = bool((audio_payload or {}).get("ok") and audio_b64)
    audio_error = (audio_payload or {}).get("error") or ""

    stage_data = {
        "accent": accent,
        "accent2": accent2,
        "userQuestion": (user_question or "").strip(),
        "spokenText": spoken_text,
        "audioB64": audio_b64 if audio_ok else "",
        "audioOk": audio_ok,
        "audioError": audio_error,
        "words": words,
        "visemes": visemes,
        "autoplay": bool(autoplay and audio_ok),
    }

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root {{
    --accent: {accent};
    --accent2: {accent2};
    --bg: #060b16;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0; padding: 0; width: 100%; height: 100%;
    background: var(--bg);
    color: #f0f7ff;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    overflow: hidden;
  }}
  .stage {{
    position: relative;
    width: 100%;
    height: {height - 4}px;
    background: var(--bg);
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  #bgCanvas {{
    position: absolute; inset: 0; width: 100%; height: 100%;
    pointer-events: none; z-index: 0;
  }}

  /* Steady, grounded hero anchor — zero bobblehead wobble */
  .maam-anchor {{
    position: relative;
    z-index: 2;
    width: min(520px, 86vw);
    height: min(520px, {height - 32}px);
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  #auraCanvas {{
    position: absolute;
    left: 50%; top: 47%;
    transform: translate(-50%, -50%);
    width: 520px; height: 520px;
    pointer-events: none;
    z-index: 1;
  }}
  .portrait-stack {{
    position: relative;
    z-index: 2;
    width: 100%;
    height: 100%;
    max-width: 495px;
    max-height: 495px;
    transform-origin: 50% 92%;
    will-change: transform;
  }}
  /* Layered pixel-locked frames for silky continuous alpha-blended lip-sync & blinking */
  .frame-img {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;
    pointer-events: none;
    user-select: none;
    will-change: opacity;
  }}
  #fIdle {{ opacity: 1; z-index: 1; }}
  #fMid  {{ opacity: 0; z-index: 2; }}
  #fOpen {{ opacity: 0; z-index: 3; }}
  #fBlink {{ opacity: 0; z-index: 4; }}

  /* Floating Speech Bubbles */
  .bubble-layer {{
    position: absolute;
    inset: 0;
    z-index: 5;
    pointer-events: none;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 10px 18px 12px;
  }}
  .student-bubble-wrap {{
    display: flex;
    justify-content: flex-start;
    align-items: flex-start;
  }}
  .student-bubble {{
    display: none;
    max-width: min(340px, 42vw);
    padding: 10px 16px;
    border-radius: 20px 20px 20px 6px;
    background: rgba(167, 139, 250, 0.16);
    border: 1px solid rgba(167, 139, 250, 0.42);
    backdrop-filter: blur(14px);
    color: #efe9ff;
    font-size: 14px;
    line-height: 1.45;
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
    animation: popIn 0.28s cubic-bezier(.2,.9,.3,1);
  }}
  .student-bubble.show {{ display: inline-block; }}

  .maam-bubble-dock {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    pointer-events: auto;
  }}
  .speech-bubble {{
    position: relative;
    max-width: min(680px, 92vw);
    min-width: min(260px, 76vw);
    padding: 14px 22px;
    border-radius: 24px;
    background: rgba(11, 22, 44, 0.82);
    border: 1px solid rgba(112, 229, 255, 0.38);
    backdrop-filter: blur(18px);
    box-shadow: 0 14px 38px rgba(0, 0, 0, 0.48), 0 0 28px rgba(112, 229, 255, 0.1);
    text-align: center;
    animation: popIn 0.3s cubic-bezier(.2,.9,.3,1);
  }}
  .speech-bubble::before {{
    content: "";
    position: absolute;
    top: -10px;
    left: 50%;
    transform: translateX(-50%);
    border-left: 11px solid transparent;
    border-right: 11px solid transparent;
    border-bottom: 10px solid rgba(112, 229, 255, 0.42);
  }}
  .speech-bubble::after {{
    content: "";
    position: absolute;
    top: -8.5px;
    left: 50%;
    transform: translateX(-50%);
    border-left: 10px solid transparent;
    border-right: 10px solid transparent;
    border-bottom: 9px solid rgba(11, 22, 44, 0.94);
  }}
  .cap-text {{
    max-height: 76px;
    overflow-y: auto;
    font-size: 16px;
    line-height: 1.52;
    font-weight: 500;
    color: #cfe4f8;
    scroll-behavior: smooth;
    scrollbar-width: none;
  }}
  .cap-text::-webkit-scrollbar {{ display: none; }}
  .cap-word {{
    display: inline;
    padding: 1px 3px;
    border-radius: 6px;
    transition: color 0.08s ease, background 0.08s ease;
  }}
  .cap-word.spoken {{ color: #eef7ff; }}
  .cap-word.now {{
    color: #06101f;
    background: var(--accent);
    font-weight: 800;
    box-shadow: 0 0 14px rgba(112, 229, 255, 0.65);
  }}

  .mini-bar {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 5px 10px;
    border-radius: 999px;
    background: rgba(9, 18, 36, 0.78);
    border: 1px solid rgba(145, 208, 255, 0.22);
    backdrop-filter: blur(12px);
  }}
  .pill-btn {{
    border: none;
    background: rgba(255, 255, 255, 0.08);
    color: #eaf5ff;
    border-radius: 999px;
    padding: 5px 13px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    transition: 0.16s ease;
  }}
  .pill-btn:hover {{
    background: rgba(112, 229, 255, 0.2);
    transform: translateY(-1px);
  }}
  .pill-btn.play {{
    background: linear-gradient(110deg, var(--accent), var(--accent2));
    color: #06101f;
  }}
  .pill-btn.play.pulse {{
    animation: pulseGlow 1.4s ease-in-out infinite;
  }}
  .live-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 10px var(--accent);
  }}
  .live-dot.speaking {{
    background: #79f3c1;
    box-shadow: 0 0 14px #79f3c1;
    animation: pulseDot 0.6s ease-in-out infinite;
  }}

  @keyframes popIn {{
    from {{ opacity: 0; transform: translateY(8px) scale(0.97); }}
    to {{ opacity: 1; transform: translateY(0) scale(1); }}
  }}
  @keyframes pulseDot {{
    0%, 100% {{ transform: scale(1); opacity: 1; }}
    50% {{ transform: scale(1.45); opacity: 0.65; }}
  }}
  @keyframes pulseGlow {{
    0%, 100% {{ box-shadow: 0 0 0 0 rgba(112, 229, 255, 0.55); }}
    50% {{ box-shadow: 0 0 0 8px rgba(112, 229, 255, 0); }}
  }}
</style>
</head>
<body>
<div class="stage">
  <canvas id="bgCanvas"></canvas>

  <!-- BIG CENTER-STAGE PIXAR-3D MA'AM (STEADY, NATURAL, NO BOX) -->
  <div class="maam-anchor">
    <canvas id="auraCanvas" width="520" height="520"></canvas>
    <div id="portraitStack" class="portrait-stack">
      <img id="fIdle" class="frame-img" src="{frames['idle']}" alt="VidyaLoop AI Teacher" />
      <img id="fMid" class="frame-img" src="{frames['mid']}" alt="" />
      <img id="fOpen" class="frame-img" src="{frames['open']}" alt="" />
      <img id="fBlink" class="frame-img" src="{frames['blink']}" alt="" />
    </div>
  </div>

  <!-- FLOATING SPEECH BUBBLES -->
  <div class="bubble-layer">
    <div class="student-bubble-wrap">
      <div id="studentBubble" class="student-bubble"></div>
    </div>

    <div class="maam-bubble-dock">
      <div class="speech-bubble">
        <div id="capBody" class="cap-text"></div>
      </div>
      <div class="mini-bar" id="miniBar">
        <span id="liveDot" class="live-dot"></span>
        <button id="playBtn" class="pill-btn play">▶ Play</button>
        <button id="replayBtn" class="pill-btn" title="Replay">↺</button>
        <button id="speedBtn" class="pill-btn" title="Speed">1.0x</button>
      </div>
    </div>
  </div>
</div>

<script>
(() => {{
  const DATA = {_safe_json(stage_data)};

  const studentBubble = document.getElementById("studentBubble");
  if (DATA.userQuestion) {{
    studentBubble.textContent = "“" + DATA.userQuestion + "”";
    studentBubble.classList.add("show");
  }}

  const capBody = document.getElementById("capBody");
  let wordSpans = [];
  if (DATA.words && DATA.words.length > 0) {{
    DATA.words.forEach((wObj, idx) => {{
      const sp = document.createElement("span");
      sp.className = "cap-word";
      sp.textContent = wObj.w + " ";
      capBody.appendChild(sp);
      wordSpans.push({{ el: sp, s: wObj.s, e: wObj.e, idx }});
    }});
  }} else {{
    const tokens = (DATA.spokenText || "").split(/\\s+/).filter(Boolean);
    tokens.forEach((tok, idx) => {{
      const sp = document.createElement("span");
      sp.className = "cap-word";
      sp.textContent = tok + " ";
      capBody.appendChild(sp);
      wordSpans.push({{ el: sp, s: -1, e: -1, idx }});
    }});
  }}

  const liveDot = document.getElementById("liveDot");
  const playBtn = document.getElementById("playBtn");
  const replayBtn = document.getElementById("replayBtn");
  const speedBtn = document.getElementById("speedBtn");

  let audio = null;
  let audioCtx = null;
  let analyser = null;
  let freqData = null;
  let isPlaying = false;
  let usingFallback = false;
  let fallbackWordIdx = 0;
  let fallbackEnergy = 0;
  const speeds = [1.0, 1.15, 1.25, 0.9];
  let speedIdx = 0;

  if (DATA.audioOk && DATA.audioB64) {{
    audio = new Audio("data:audio/mpeg;base64," + DATA.audioB64);
    audio.preload = "auto";
  }}

  function ensureAudioCtx() {{
    if (!audio || audioCtx) return;
    try {{
      const AC = window.AudioContext || window.webkitAudioContext;
      audioCtx = new AC();
      const src = audioCtx.createMediaElementSource(audio);
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 128;
      analyser.smoothingTimeConstant = 0.78;
      src.connect(analyser);
      analyser.connect(audioCtx.destination);
      freqData = new Uint8Array(analyser.frequencyBinCount);
    }} catch (e) {{
      analyser = null;
    }}
  }}

  function setUiState(state) {{
    liveDot.classList.toggle("speaking", state === "speaking");
    if (state === "speaking") {{
      playBtn.textContent = "⏸ Pause";
      playBtn.classList.remove("pulse");
    }} else if (state === "paused") {{
      playBtn.textContent = "▶ Resume";
    }} else {{
      playBtn.textContent = "▶ Play";
    }}
  }}

  function startFallback() {{
    if (!("speechSynthesis" in window) || !DATA.spokenText) return;
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(DATA.spokenText);
    utt.rate = speeds[speedIdx];
    utt.pitch = 1.08;
    const voices = window.speechSynthesis.getVoices() || [];
    const fem = voices.find(v => /female|zira|samantha|aria|jenny|google us english/i.test(v.name));
    if (fem) utt.voice = fem;
    usingFallback = true;
    fallbackWordIdx = 0;
    utt.onstart = () => {{ isPlaying = true; setUiState("speaking"); }};
    utt.onboundary = () => {{
      fallbackEnergy = 0.75;
      fallbackWordIdx = Math.min(wordSpans.length - 1, fallbackWordIdx + 1);
    }};
    utt.onend = () => {{ isPlaying = false; usingFallback = false; fallbackEnergy = 0; setUiState("ready"); }};
    utt.onerror = () => {{ isPlaying = false; usingFallback = false; fallbackEnergy = 0; setUiState("ready"); }};
    window.speechSynthesis.speak(utt);
  }}

  async function togglePlay() {{
    if (audio) {{
      ensureAudioCtx();
      if (audioCtx && audioCtx.state === "suspended") {{
        try {{ await audioCtx.resume(); }} catch (e) {{}}
      }}
      if (isPlaying) {{
        audio.pause();
        isPlaying = false;
        setUiState("paused");
      }} else {{
        try {{
          await audio.play();
          isPlaying = true;
          setUiState("speaking");
        }} catch (e) {{
          playBtn.classList.add("pulse");
          playBtn.textContent = "▶ Tap to Hear";
        }}
      }}
    }} else {{
      if (isPlaying) {{
        window.speechSynthesis.cancel();
        isPlaying = false;
        usingFallback = false;
        setUiState("ready");
      }} else {{
        startFallback();
      }}
    }}
  }}

  playBtn.addEventListener("click", togglePlay);
  replayBtn.addEventListener("click", async () => {{
    if (audio) {{
      audio.currentTime = 0;
      isPlaying = false;
      await togglePlay();
    }} else {{
      window.speechSynthesis.cancel();
      startFallback();
    }}
  }});
  speedBtn.addEventListener("click", () => {{
    speedIdx = (speedIdx + 1) % speeds.length;
    const r = speeds[speedIdx];
    speedBtn.textContent = r.toFixed(2).replace(/\\.00$/, ".0") + "x";
    if (audio) audio.playbackRate = r;
  }});

  if (audio) {{
    audio.addEventListener("ended", () => {{ isPlaying = false; setUiState("ready"); }});
    if (DATA.autoplay) {{
      setTimeout(() => {{
        ensureAudioCtx();
        audio.play().then(() => {{
          isPlaying = true;
          setUiState("speaking");
        }}).catch(() => {{
          playBtn.classList.add("pulse");
          playBtn.textContent = "▶ Tap to Hear";
        }});
      }}, 120);
    }}
  }} else if (!DATA.userQuestion) {{
    document.getElementById("miniBar").style.opacity = "0.75";
  }}

  // ============ SILKY NATURAL LIP-SYNC, BLINK & CALM MOTION ENGINE ============
  const fMid = document.getElementById("fMid");
  const fOpen = document.getElementById("fOpen");
  const fBlink = document.getElementById("fBlink");
  const portraitStack = document.getElementById("portraitStack");

  function getViseme(t) {{
    if (!DATA.visemes || DATA.visemes.length === 0) return "mid";
    let v = "mid";
    for (let i = 0; i < DATA.visemes.length; i++) {{
      if (DATA.visemes[i].t <= t) v = DATA.visemes[i].v;
      else break;
    }}
    return v;
  }}

  // Natural smooth blink state (175ms soft sine curve)
  let nextBlinkAt = performance.now() + 2400;
  let blinkStart = -1;
  const BLINK_MS = 175;

  // Smoothly interpolated motion & lip states (eliminates jitter & wobble!)
  let smoothEnergy = 0;
  let lipMidAlpha = 0;
  let lipOpenAlpha = 0;
  let smoothNod = 0;
  let smoothTilt = 0;
  let lastScrolledWord = -1;

  // Canvas refs
  const bgCanvas = document.getElementById("bgCanvas");
  const bgCtx = bgCanvas.getContext("2d");
  const auraCanvas = document.getElementById("auraCanvas");
  const aCtx = auraCanvas.getContext("2d");

  function resizeBg() {{
    const rect = bgCanvas.getBoundingClientRect();
    bgCanvas.width = Math.max(320, rect.width);
    bgCanvas.height = Math.max(320, rect.height);
  }}
  resizeBg();
  window.addEventListener("resize", resizeBg);

  const particles = Array.from({{ length: 26 }}, () => ({{
    x: Math.random(),
    y: Math.random(),
    r: 1.2 + Math.random() * 2.1,
    vx: (Math.random() - 0.5) * 0.00014,
    vy: -0.0001 - Math.random() * 0.0002,
    a: 0.14 + Math.random() * 0.28,
  }}));

  function loop(now) {{
    const sec = now * 0.001;
    let rawEnergy = 0;
    let currentT = 0;
    let duration = 0;

    if (audio && isPlaying) {{
      currentT = audio.currentTime || 0;
      duration = isFinite(audio.duration) ? audio.duration : 0;
      if (analyser && freqData) {{
        analyser.getByteFrequencyData(freqData);
        let sum = 0;
        for (let i = 2; i < 26; i++) sum += freqData[i];
        rawEnergy = Math.min(1, sum / (24 * 148));
      }} else {{
        rawEnergy = 0.28 + Math.abs(Math.sin(sec * 8.5)) * 0.38;
      }}
    }} else if (usingFallback && isPlaying) {{
      fallbackEnergy *= 0.90;
      rawEnergy = Math.max(0.12, fallbackEnergy + Math.abs(Math.sin(sec * 7.5)) * 0.18);
    }}

    // Smooth energy damping
    smoothEnergy = smoothEnergy * 0.74 + rawEnergy * 0.26;

    // 1. Silky Continuous Alpha-Blended Lip-Sync (infinite smooth mouth positions!)
    let targetMid = 0;
    let targetOpen = 0;
    if (isPlaying && smoothEnergy > 0.04) {{
      const vis = (audio && DATA.visemes && DATA.visemes.length) ? getViseme(currentT) : "mid";
      if (vis === "closed" || vis === "rest") {{
        targetMid = 0.08 * smoothEnergy;
        targetOpen = 0;
      }} else if (vis === "open" || vis === "round") {{
        targetMid = 0.85;
        targetOpen = Math.min(1, 0.35 + smoothEnergy * 0.95);
      }} else if (vis === "wide" || vis === "fv") {{
        targetMid = Math.min(1, 0.45 + smoothEnergy * 0.75);
        targetOpen = Math.max(0, (smoothEnergy - 0.52) * 0.85);
      }} else {{
        targetMid = Math.min(1, 0.28 + smoothEnergy * 0.9);
        targetOpen = Math.max(0, (smoothEnergy - 0.42) * 0.95);
      }}
    }}
    // Organic attack/release smoothing (natural muscle inertia)
    const attack = 0.34, release = 0.22;
    lipMidAlpha += (targetMid - lipMidAlpha) * (targetMid > lipMidAlpha ? attack : release);
    lipOpenAlpha += (targetOpen - lipOpenAlpha) * (targetOpen > lipOpenAlpha ? attack : release);
    fMid.style.opacity = lipMidAlpha.toFixed(3);
    fOpen.style.opacity = lipOpenAlpha.toFixed(3);

    // 2. Smooth Sine-Eased Natural Blinking (softly suppressed when mouth wide open)
    if (now >= nextBlinkAt && blinkStart < 0) {{
      blinkStart = now;
    }}
    let blinkAlpha = 0;
    if (blinkStart >= 0) {{
      const elapsed = now - blinkStart;
      if (elapsed < BLINK_MS) {{
        // Smooth bell curve 0 -> 1 -> 0
        blinkAlpha = Math.sin((elapsed / BLINK_MS) * Math.PI);
        // Only blink cleanly when mouth isn't wide open (so eyes & mouth never clash)
        if (lipOpenAlpha > 0.45) blinkAlpha *= 0.25;
      }} else {{
        blinkStart = -1;
        // Occasional natural double blink, otherwise 3–5.5s interval
        nextBlinkAt = now + (Math.random() < 0.14 ? 320 : (3000 + Math.random() * 2600));
      }}
    }}
    fBlink.style.opacity = blinkAlpha.toFixed(3);

    // 3. Calm, Realistic Human Posture & Breathing (ZERO wobble!)
    // Slow 4.8-second chest breath + ultra-subtle grounded emphasis settle
    const breathY = Math.sin(sec * 1.28) * 1.8;
    const breathScale = 1 + Math.sin(sec * 1.28 - 0.4) * 0.0045;
    // Ultra-gentle, heavily damped speaking presence (max 1.1px downward nod, max 0.38 deg drift)
    const targetNod = isPlaying ? (smoothEnergy * 1.2) : 0;
    const targetTilt = isPlaying
      ? Math.sin(sec * 0.65) * 0.38
      : Math.sin(sec * 0.35) * 0.22;
    smoothNod += (targetNod - smoothNod) * 0.07;
    smoothTilt += (targetTilt - smoothTilt) * 0.04;

    const totalY = breathY + smoothNod;
    portraitStack.style.transform =
      `translate3d(0, ${{totalY.toFixed(2)}}px, 0) scale(${{breathScale.toFixed(4)}}) rotate(${{smoothTilt.toFixed(3)}}deg)`;

    // 4. Word-synced caption bubble highlighting
    if (isPlaying && wordSpans.length > 0) {{
      let activeIdx = -1;
      if (audio && DATA.words && DATA.words.length > 0) {{
        for (let i = 0; i < wordSpans.length; i++) {{
          if (currentT >= wordSpans[i].s && currentT <= wordSpans[i].e + 0.14) {{
            activeIdx = i; break;
          }}
          if (currentT > wordSpans[i].e) activeIdx = i;
        }}
      }} else if (audio && duration > 0) {{
        activeIdx = Math.min(wordSpans.length - 1, Math.floor((currentT / duration) * wordSpans.length));
      }} else if (usingFallback) {{
        activeIdx = fallbackWordIdx;
      }}

      if (activeIdx >= 0) {{
        for (let i = 0; i < wordSpans.length; i++) {{
          wordSpans[i].el.className = i < activeIdx ? "cap-word spoken" : (i === activeIdx ? "cap-word now" : "cap-word");
        }}
        if (activeIdx !== lastScrolledWord && wordSpans[activeIdx]) {{
          lastScrolledWord = activeIdx;
          const el = wordSpans[activeIdx].el;
          const top = el.offsetTop - capBody.offsetTop;
          if (top > capBody.clientHeight * 0.45) {{
            capBody.scrollTop = top - capBody.clientHeight * 0.25;
          }}
        }}
      }}
    }}

    // 5. Soft Glowing Voice Aura Ring behind Ma'am
    aCtx.clearRect(0, 0, 520, 520);
    const cx = 260, cy = 246;
    const glowR = 198 + smoothEnergy * 34;
    const grad = aCtx.createRadialGradient(cx, cy, 48, cx, cy, glowR);
    grad.addColorStop(0, isPlaying ? "rgba(112, 229, 255, 0.21)" : "rgba(112, 229, 255, 0.10)");
    grad.addColorStop(0.55, isPlaying ? "rgba(167, 139, 250, 0.11)" : "rgba(167, 139, 250, 0.05)");
    grad.addColorStop(1, "rgba(6, 11, 22, 0)");
    aCtx.fillStyle = grad;
    aCtx.fillRect(0, 0, 520, 520);

    const bars = 72, baseR = 180;
    for (let i = 0; i < bars; i++) {{
      const ang = (i / bars) * Math.PI * 2 - Math.PI / 2 + sec * 0.08;
      let mag = 0.05 + Math.sin(sec * 1.6 + i * 0.35) * 0.035;
      if (isPlaying) {{
        mag = (freqData && analyser)
          ? (0.10 + (freqData[i % 32] / 255) * 0.88)
          : (0.15 + smoothEnergy * (0.35 + Math.abs(Math.sin(sec * 6.5 + i * 0.5)) * 0.55));
      }}
      const len = 4 + mag * 28;
      aCtx.beginPath();
      aCtx.moveTo(cx + Math.cos(ang) * baseR, cy + Math.sin(ang) * baseR);
      aCtx.lineTo(cx + Math.cos(ang) * (baseR + len), cy + Math.sin(ang) * (baseR + len));
      aCtx.strokeStyle = (i % 2 === 0) ? DATA.accent : DATA.accent2;
      aCtx.globalAlpha = isPlaying ? (0.32 + mag * 0.48) : 0.15;
      aCtx.lineWidth = 2.5;
      aCtx.lineCap = "round";
      aCtx.stroke();
    }}
    aCtx.globalAlpha = 1;

    // 6. Gentle background ambient particles
    const sw = bgCanvas.width, sh = bgCanvas.height;
    bgCtx.clearRect(0, 0, sw, sh);
    const boost = isPlaying ? (1.4 + smoothEnergy * 1.6) : 1.0;
    for (const p of particles) {{
      p.x += p.vx * boost;
      p.y += p.vy * boost;
      if (p.y < -0.02) {{ p.y = 1.02; p.x = Math.random(); }}
      if (p.x < 0) p.x = 1;
      if (p.x > 1) p.x = 0;
      bgCtx.beginPath();
      bgCtx.arc(p.x * sw, p.y * sh, p.r, 0, Math.PI * 2);
      bgCtx.fillStyle = p.r > 2.2 ? DATA.accent2 : DATA.accent;
      bgCtx.globalAlpha = p.a * (isPlaying ? 0.85 : 0.48);
      bgCtx.fill();
    }}
    bgCtx.globalAlpha = 1;

    requestAnimationFrame(loop);
  }}

  requestAnimationFrame(loop);
}})();
</script>
</body>
</html>"""

    if hasattr(st, "iframe"):
        st.iframe(html, width="stretch", height=height)
    else:
        components.html(html, height=height, scrolling=False)
