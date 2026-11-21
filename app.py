import base64
import hashlib
import importlib
import inspect
import os
from datetime import date, timedelta
from html import escape

import streamlit as st
import streamlit.components.v1 as components

import auth
import db_manager
import tutor_avatar
import voice_service
from utils import (
    clear_uploads,
    get_available_documents,
    get_file_size_mb,
    get_kb_analytics,
    reset_database,
    resolve_upload_path,
    source_basename,
)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
LOGO_FULL_PATH = os.path.join(ASSETS_DIR, "vidyaloop_logo.png")
LOGO_ICON_PATH = os.path.join(ASSETS_DIR, "vidyaloop_icon.png")

st.set_page_config(
    page_title="VidyaLoop | Learn, Practice, Improve, Repeat.",
    page_icon=LOGO_ICON_PATH if os.path.exists(LOGO_ICON_PATH) else "🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def inject_styles(fullscreen_tutor=False):
    container_css = (
        ".block-container { max-width: 100%!important; padding: 0.35rem 1.25rem 0.9rem!important; }"
        if fullscreen_tutor
        else ".block-container { max-width: 1260px; padding-top: 1.4rem; padding-bottom: 2.8rem; }"
    )
    st.markdown(f"""<style>
    :root {{
        --ink: #eaf5ff;
        --muted: #94a8bd;
        --line: rgba(175,217,255,.14);
        --cyan: #70e5ff;
        --purple: #a78bfa;
        --gold: #f6ad55;
        --green: #79f3c1;
        --red: #ff8787;
    }}
    .stApp {{ background: #060b16; color: var(--ink); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    .stApp::before, .stApp::after {{ display: none; }}
    #MainMenu, footer, header {{ visibility: hidden; }}
    {container_css}
    [data-testid="stSidebar"] {{ background: rgba(5,11,23,.96)!important; border-right: 1px solid var(--line); }}
    [data-testid="stSidebar"] > div:first-child {{ padding-top: 1rem; }}

    /* Buttons */
    .stButton > button {{
        border-radius: 12px!important;
        font-weight: 700!important;
        min-height: 39px;
        border: 1px solid rgba(150,200,255,.18)!important;
        background: rgba(255,255,255,.035)!important;
        color: #dcecff!important;
        transition: .16s ease!important;
    }}
    .stButton > button:hover {{
        transform: translateY(-1px);
        border-color: rgba(112,229,255,.68)!important;
        color: white!important;
        background: rgba(112,229,255,.12)!important;
    }}
    .stButton > button[kind="primary"] {{
        background: linear-gradient(110deg,#75e8ff,#9194ff)!important;
        border: 0!important;
        color: #07101e!important;
        box-shadow: 0 8px 22px rgba(102,178,255,.28)!important;
    }}

    /* Prominent glowing Mic control below Ma'am */
    [data-testid="stAudioInput"] > div {{
        background: linear-gradient(120deg, rgba(112,229,255,0.14), rgba(167,139,250,0.16))!important;
        border: 1.5px solid rgba(112,229,255,0.58)!important;
        border-radius: 999px!important;
        box-shadow: 0 0 24px rgba(112,229,255,0.22)!important;
        padding: 4px 12px!important;
        min-height: 48px!important;
    }}
    [data-testid="stAudioInput"] button {{
        color: #70e5ff!important;
    }}

    /* Inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {{
        border-radius: 14px!important;
        background: rgba(255,255,255,.05)!important;
        border: 1px solid var(--line)!important;
        color: white!important;
    }}
    .stTextInput label, .stTextArea label, .stSelectbox label, .stFileUploader label, .stRadio label {{
        color: #b8c8dc!important;
        font-weight: 600!important;
    }}
    [data-testid="stFileUploaderDropzone"] {{
        border: 1px dashed rgba(112,229,255,.45)!important;
        border-radius: 16px!important;
        background: rgba(89,144,255,.045)!important;
        padding: 1.1rem!important;
    }}
    [data-testid="stChatMessage"] {{
        border: 1px solid var(--line);
        background: rgba(12,22,40,.65);
        border-radius: 18px;
    }}

    /* Typography & brand */
    .brand-lockup {{ display: flex; align-items: center; gap: 11px; padding: 0 0 1rem; }}
    .brand-mark {{
        width: 34px; height: 34px; border-radius: 11px; position: relative;
        background: conic-gradient(from 180deg,#70e5ff,#7a72ff,#d298ff,#70e5ff);
        box-shadow: 0 0 22px rgba(112,229,255,.32);
    }}
    .brand-mark:after {{ content: ""; position: absolute; inset: 7px; border-radius: 8px; background: #081323; }}
    .brand-mark:before {{ content: "✦"; position: absolute; z-index: 1; inset: 5px; text-align: center; color: #dffbff; font-size: 17px; }}
    .eyebrow {{ color: #74e4ff; font: 600 .68rem ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .16em; text-transform: uppercase; }}
    .brand-name {{ color: white; font-size: .95rem; font-weight: 800; letter-spacing: .05em; }}
    .nav-caption {{ color: #6d849d; font: 600 .68rem ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .12em; margin: .9rem 0 .35rem; text-transform: uppercase; }}

    .page-kicker {{ color: #77e5ff; font: 600 .74rem ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .15em; text-transform: uppercase; }}
    .page-title {{ font-size: clamp(1.7rem, 3.2vw, 2.35rem); letter-spacing: -.04em; margin: .25rem 0 .35rem; color: #f5f9ff; font-weight: 800; }}
    .page-subtitle {{ color: var(--muted); max-width: 720px; line-height: 1.55; margin-bottom: 1.25rem; font-size: .94rem; }}

    /* Glass card container */
    .glass-card {{
        background: linear-gradient(145deg, rgba(21,34,59,.72), rgba(8,16,31,.72));
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 1.3rem;
        box-shadow: inset 0 1px rgba(255,255,255,.035), 0 16px 45px rgba(0,0,0,.18);
        margin-bottom: 1rem;
    }}
    .metric-label {{ color: #9bb0c9; font: 600 .68rem ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .12em; text-transform: uppercase; }}
    .metric-value {{ font-size: 1.95rem; font-weight: 800; letter-spacing: -.06em; color: white; margin-top: .25rem; }}
    .metric-hint {{ color: #70e5ff; font-size: .78rem; margin-top: .2rem; }}

    /* Badges */
    .badge-doc {{
        display: inline-block; padding: 3px 9px; border-radius: 999px;
        background: rgba(112, 229, 255, 0.12); color: #70e5ff;
        border: 1px solid rgba(112, 229, 255, 0.28); font-size: .74rem; font-weight: 600;
    }}
    .badge-memory {{
        display: inline-block; padding: 3px 9px; border-radius: 999px;
        background: rgba(167, 139, 250, 0.14); color: #c4b5fd;
        border: 1px solid rgba(167, 139, 250, 0.32); font-size: .74rem; font-weight: 600;
    }}
    .badge-voice {{
        display: inline-block; padding: 3px 10px; border-radius: 999px;
        background: rgba(167, 139, 250, 0.2); color: #ddd6fe;
        border: 1px solid rgba(167, 139, 250, 0.45); font-size: .75rem; font-weight: 700;
    }}
    .badge-ok {{
        display: inline-block; padding: 3px 9px; border-radius: 999px;
        background: rgba(121, 243, 193, 0.16); color: #79f3c1;
        border: 1px solid rgba(121, 243, 193, 0.38); font-size: .75rem; font-weight: 700;
    }}
    .badge-warn {{
        display: inline-block; padding: 3px 9px; border-radius: 999px;
        background: rgba(246, 173, 85, 0.2); color: #fbd38d;
        border: 1px solid rgba(246, 173, 85, 0.45); font-size: .75rem; font-weight: 700;
    }}
    .badge-weak {{
        display: inline-block; padding: 4px 10px; border-radius: 999px;
        background: rgba(255, 107, 107, 0.15); color: #ff8787;
        border: 1px solid rgba(255, 107, 107, 0.35); font-size: .76rem; font-weight: 600; margin: 3px 4px 3px 0;
    }}
    .source-chip {{
        display: inline-block; margin: 3px 6px 3px 0; padding: 3px 9px;
        color: #8deaff; background: rgba(112,229,255,.08);
        border: 1px solid rgba(112,229,255,.2); border-radius: 999px; font-size: .73rem;
    }}
    .empty-state {{ text-align: center; padding: 2.6rem 1rem; color: #9cb0c6; }}
    .brain-visual {{ margin: 0 auto .8rem; color: #b7f5ff; font-size: 3.6rem; filter: drop-shadow(0 0 16px rgba(112,229,255,.68)); }}
    .file-row {{ padding: .75rem .1rem; border-bottom: 1px solid rgba(175,217,255,.1); }}
    .file-name {{ color: #e8f4ff; font-weight: 700; font-size: .91rem; }}
    .file-meta {{ color: #8298b1; font-size: .76rem; margin-top: 3px; }}

    .quiz-question-box {{
        background: rgba(16, 28, 52, 0.6);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
    }}
    .quiz-question-title {{ color: #f1f7ff; font-weight: 700; font-size: 1.05rem; margin-bottom: .8rem; }}
    .score-banner {{
        text-align: center;
        padding: 1.8rem;
        border-radius: 20px;
        background: linear-gradient(135deg, rgba(28,57,116,.7), rgba(15,28,56,.7));
        border: 1px solid rgba(112,229,255,.35);
        margin-bottom: 1.5rem;
    }}
    </style>""", unsafe_allow_html=True)


def _nav_to(view_name):
    st.session_state.current_view = view_name


def _logout():
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.session_state.current_view = "VirtualTutor"


def init_state():
    defaults = {
        "boot_complete": False,
        "authenticated": False,
        "current_user": None,
        "current_view": "VirtualTutor",
        "chat_history": [],
        "active_quiz": [],
        "quiz_submitted": False,
        "quiz_score": 0,
        "user_answers": {},
        "quiz_weak_topics": [],
        "quiz_topic_prefill": "",
        "open_pdf": None,
        # AI Virtual Tutor & ElevenLabs Voice state
        "voice_audio_cache": {},
        "tutor_persona": list(voice_service.TUTOR_PERSONAS.keys())[0],
        "tutor_model_label": list(voice_service.ELEVENLABS_MODELS.keys())[0],
        "tutor_mic_lang": "Auto (English + Hindi)",
        "tutor_style": "Simple & Friendly",
        "tutor_mode": "documents",
        "tutor_history": [],
        "tutor_current_lesson": None,
        "tutor_current_audio": None,
        "tutor_last_question": "",
        "tutor_last_mic_digest": None,
        "ask_mode": "documents",
        "where_learned_result": None,
        "teach_me_last": None,
        "exam_mode_last": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "files_ingested" not in st.session_state:
        st.session_state.files_ingested = get_available_documents()


_LOGO_B64_CACHE = {}


def _load_logo_uri(path):
    if path in _LOGO_B64_CACHE:
        return _LOGO_B64_CACHE[path]
    if os.path.exists(path):
        with open(path, "rb") as f:
            uri = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
    else:
        uri = ""
    _LOGO_B64_CACHE[path] = uri
    return uri


def brand_lockup():
    icon_uri = _load_logo_uri(LOGO_ICON_PATH)
    icon_html = (
        f"<img src='{icon_uri}' alt='VidyaLoop' style='width:42px;height:42px;object-fit:contain;filter:drop-shadow(0 0 12px rgba(112,229,255,.45));'/>"
        if icon_uri
        else "<div class='brand-mark'></div>"
    )
    st.markdown(
        f"<div class='brand-lockup'>{icon_html}"
        "<div><div class='brand-name'>VIDYALOOP</div>"
        "<div class='eyebrow' style='font-size:.62rem;letter-spacing:.08em;'>Learn, Practice, Improve, Repeat.</div></div></div>",
        unsafe_allow_html=True,
    )


def page_heading(kicker, title, subtitle):
    st.markdown(
        f"<div class='page-kicker'>{escape(kicker)}</div>"
        f"<h1 class='page-title'>{escape(title)}</h1>"
        f"<div class='page-subtitle'>{escape(subtitle)}</div>",
        unsafe_allow_html=True,
    )


def render_pdf_page(file_path, page_number, caption):
    """Render one PDF page with PyMuPDF (safe cross-platform path + bounds check)."""
    import fitz
    resolved = resolve_upload_path(file_path)
    document = fitz.open(resolved)
    try:
        if page_number < 0 or page_number >= len(document):
            st.warning(f"Page {page_number + 1} is out of range ({len(document)} pages).")
            return
        pixmap = document[page_number].get_pixmap(matrix=fitz.Matrix(1.35, 1.35), alpha=False)
        st.image(pixmap.tobytes("png"), caption=caption, use_container_width=True)
    finally:
        document.close()


def render_pptx_slide(file_path, slide_number, caption):
    """Render a PowerPoint slide's extracted text & speaker notes cleanly."""
    from pptx import Presentation
    resolved = resolve_upload_path(file_path)
    prs = Presentation(resolved)
    if slide_number < 0 or slide_number >= len(prs.slides):
        st.warning(f"Slide {slide_number + 1} is out of range ({len(prs.slides)} slides).")
        return
    slide = prs.slides[slide_number]
    lines = []
    for shape in slide.shapes:
        if getattr(shape, "has_text_frame", False) and shape.text_frame:
            txt = shape.text_frame.text.strip()
            if txt:
                lines.append(txt)
        if getattr(shape, "has_table", False) and shape.table:
            for row in shape.table.rows:
                cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
                if cells:
                    lines.append(" | ".join(cells))
    notes = ""
    try:
        if slide.has_notes_slide and slide.notes_slide and slide.notes_slide.notes_text_frame:
            notes = slide.notes_slide.notes_text_frame.text.strip()
    except Exception:
        pass
    body = "\n\n".join(lines) if lines else "(No text on this slide)"
    st.markdown(
        f"<div class='glass-card' style='border-color:rgba(167,139,250,0.45);'>"
        f"<div class='eyebrow'>📊 {escape(caption)}</div>"
        f"<pre style='white-space:pre-wrap;font-family:Manrope,sans-serif;color:#eaf5ff;font-size:.9rem;margin:.6rem 0 0;background:transparent;border:0;'>{escape(body)}</pre>"
        + (f"<div style='margin-top:.7rem;padding-top:.6rem;border-top:1px solid rgba(175,217,255,0.14);color:#9db4cc;font-size:.82rem;'><strong>Speaker Notes:</strong> {escape(notes)}</div>" if notes else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def render_pptx_document(file_path):
    """Provide a lightweight slide-by-slide PowerPoint viewer."""
    try:
        from pptx import Presentation
        resolved = resolve_upload_path(file_path)
        prs = Presentation(resolved)
        slide_count = len(prs.slides)
        if not slide_count:
            st.warning("This presentation has no slides to display.")
            return
        slide_num = st.number_input(
            "Slide", min_value=1, max_value=slide_count, value=1, step=1,
            key=f"pptx_viewer_slide_{source_basename(resolved)}",
        )
        render_pptx_slide(resolved, int(slide_num) - 1, f"{source_basename(resolved)} — Slide {slide_num} of {slide_count}")
        with open(resolved, "rb") as ppt_file:
            st.download_button(
                "Download PPTX", ppt_file.read(),
                file_name=source_basename(resolved),
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                key=f"download_pptx_{source_basename(resolved)}",
            )
    except Exception as error:
        st.error(f"Could not display this presentation: {error}")


def get_cached_voice_audio(text, voice_id=None, model_id=None, max_chars=1100):
    """Fetch ElevenLabs audio + timestamps with session caching to save credits."""
    persona_meta = voice_service.TUTOR_PERSONAS.get(
        st.session_state.get("tutor_persona", ""),
        next(iter(voice_service.TUTOR_PERSONAS.values())),
    )
    vid = voice_id or persona_meta["voice_id"]
    mid = model_id or voice_service.ELEVENLABS_MODELS.get(
        st.session_state.get("tutor_model_label", ""),
        voice_service.DEFAULT_MODEL_ID,
    )
    cache_key = voice_service.make_cache_key(text, vid, mid)
    cache = st.session_state.setdefault("voice_audio_cache", {})
    if cache_key in cache:
        return cache[cache_key]
    result = voice_service.synthesize_speech_with_timestamps(
        text, voice_id=vid, model_id=mid, max_chars=max_chars
    )
    if result.get("ok"):
        cache[cache_key] = result
    return result


def render_voice_player(text, key, label="🔊 Listen (ElevenLabs)"):
    """Reusable on-demand ElevenLabs audio button + cached inline player."""
    if not text or not text.strip():
        return
    state_key = f"voice_ready_{key}"
    c_btn, c_audio = st.columns([1.2, 2.8])
    with c_btn:
        if st.button(label, key=f"btn_voice_{key}", use_container_width=True):
            with st.spinner("Synthesizing ElevenLabs voice…"):
                audio_res = get_cached_voice_audio(text)
            st.session_state[state_key] = audio_res
    with c_audio:
        audio_res = st.session_state.get(state_key)
        if audio_res:
            if audio_res.get("ok") and audio_res.get("audio_bytes"):
                st.audio(audio_res["audio_bytes"], format="audio/mpeg")
            elif audio_res.get("error"):
                st.warning(audio_res["error"])


def render_pdf_document(file_path):
    """Provide a lightweight, page-by-page PDF viewer."""
    try:
        import fitz
        resolved = resolve_upload_path(file_path)
        document = fitz.open(resolved)
        page_count = len(document)
        document.close()
        if not page_count:
            st.warning("This PDF has no pages to display.")
            return
        page = st.number_input(
            "Page", min_value=1, max_value=page_count, value=1, step=1,
            key=f"pdf_viewer_page_{source_basename(resolved)}",
        )
        render_pdf_page(resolved, int(page) - 1, f"Page {page} of {page_count}")
        with open(resolved, "rb") as pdf_file:
            st.download_button(
                "Download PDF", pdf_file.read(),
                file_name=source_basename(resolved),
                mime="application/pdf",
                key=f"download_{source_basename(resolved)}",
            )
    except Exception as error:
        st.error(f"Could not display this PDF: {error}")


def render_searched_pages(source_details, key):
    """Show document pages/slides cited for an answer with expandable preview."""
    source_details = [d for d in source_details if d.get("source")]
    if not source_details:
        return
    with st.expander(f"📚 Sources & Citations ({len(source_details)})", expanded=False):
        previewable = []
        for d in source_details:
            resolved = resolve_upload_path(d.get("source", ""))
            lower = resolved.lower()
            if (lower.endswith(".pdf") or lower.endswith(".pptx")) and isinstance(d.get("page"), int) and os.path.exists(resolved):
                previewable.append({**d, "resolved_source": resolved})

        if not previewable:
            for detail in source_details:
                st.write(f"• {detail.get('label', 'Document excerpt')}")
            return

        st.caption("Click a source to inspect verified quotes and preview the original page or slide:")
        selected_key = f"{key}_selected_page"
        cols = st.columns(min(3, len(previewable)))
        for idx, detail in enumerate(previewable):
            page_id = f"{detail['resolved_source']}::{detail['page']}"
            with cols[idx % len(cols)]:
                if st.button(detail["label"], key=f"{key}_btn_{idx}", use_container_width=True):
                    st.session_state[selected_key] = page_id

        selected_id = st.session_state.get(selected_key)
        selected = next((d for d in previewable if f"{d['resolved_source']}::{d['page']}" == selected_id), None)
        if selected:
            for quote in selected.get("evidence", []):
                st.caption("Verbatim Quote Verified:")
                st.code(quote, language=None)
            try:
                if selected["resolved_source"].lower().endswith(".pptx"):
                    render_pptx_slide(selected["resolved_source"], selected["page"], selected["label"])
                else:
                    render_pdf_page(selected["resolved_source"], selected["page"], selected["label"])
            except Exception as e:
                st.warning(f"Preview unavailable: {e}")


# ==================== BOOT & AUTH ====================

def render_boot():
    if st.query_params.get("enter") == "1":
        st.session_state.boot_complete = True
        st.query_params.clear()
        st.rerun()

    logo_uri = _load_logo_uri(LOGO_FULL_PATH)
    logo_block = (
        f"<img class='logo-hero' src='{logo_uri}' alt='VidyaLoop — Learn, Practice, Improve, Repeat.' />"
        if logo_uri
        else "<h1 class='title'>VIDYALOOP</h1><p class='kicker'>Learn, Practice, Improve, Repeat.</p>"
    )
    boot_html = f"""
    <!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>
    *{{box-sizing:border-box}}body{{margin:0;background:#060b16;color:#f6fbff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;overflow:hidden}}.stage{{min-height:530px;padding:34px 24px;display:grid;place-items:center;text-align:center;position:relative;isolation:isolate;background:radial-gradient(circle at 50% 42%,rgba(45,92,190,.42) 0%,rgba(16,28,62,.52) 36%,#060b16 74%)}}.stage:before{{content:"";position:absolute;inset:0;opacity:.34;background-image:linear-gradient(rgba(149,220,255,.1) 1px,transparent 1px),linear-gradient(90deg,rgba(149,220,255,.1) 1px,transparent 1px);background-size:48px 48px;mask-image:radial-gradient(circle,black,transparent 72%);z-index:-1}}.logo-hero{{width:min(440px,84vw);height:auto;margin:0 auto 18px;display:block;filter:drop-shadow(0 0 28px rgba(112,229,255,.45));animation:floatY 3.4s ease-in-out infinite}}.kicker{{font:700 12px monospace;letter-spacing:.2em;color:#8cecff;text-transform:uppercase;margin-bottom:10px}}.tagline{{margin:10px auto 0;color:#c4d7ec;font-size:clamp(15px,2vw,18px);line-height:1.6;max-width:560px}}@keyframes floatY{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-7px)}}}}
    </style></head><body><main class="stage"><section><div class="kicker">AI Virtual Tutor &amp; Smart Study Companion</div>{logo_block}<p class="tagline">Talk live with your animated AI teacher grounded in your PDFs &amp; slides.<br><strong style="color:#8cecff">Learn, Practice, Improve, Repeat.</strong></p></section></main></body></html>
    """
    if hasattr(st, "iframe"):
        st.iframe(boot_html, width="stretch", height=540)
    else:
        components.html(boot_html, height=540, scrolling=False)
    _, entry_col, _ = st.columns([1.2, 1, 1.2])
    with entry_col:
        if st.button("Enter VidyaLoop  →", type="primary", use_container_width=True, key="splash_entry"):
            st.session_state.boot_complete = True
            st.rerun()


def render_auth():
    logo_uri = _load_logo_uri(LOGO_FULL_PATH)
    logo_img = (
        f"<img src='{logo_uri}' alt='VidyaLoop' style='width:min(310px,82%);margin-top:1.2rem;filter:drop-shadow(0 0 20px rgba(112,229,255,.38));'/>"
        if logo_uri
        else ""
    )
    left, right = st.columns([1.08, .92], gap="large")
    with left:
        st.markdown(
            f"""<div class='glass-card' style='padding:2.4rem;min-height:430px;'>
            <div class='eyebrow'>VidyaLoop · Learn, Practice, Improve, Repeat.</div>
            <h1 style='font-size:2.1rem;letter-spacing:-.05em;margin-top:.75rem'>Your Notes, Taught Live by an AI Virtual Teacher.</h1>
            <p style='color:#a7bbd2;line-height:1.68'>Upload PDFs, PowerPoint slides, and lecture notes. Ask questions by voice or text, learn with live captions, practice grounded quizzes, and verify every answer with exact page references.</p>
            <div style='margin-top:1.1rem;'>
                <span class='badge-doc'>PDF &amp; PPTX Grounded RAG</span> &nbsp;
                <span class='badge-voice'>ElevenLabs Animated AI Tutor</span>
            </div>
            <div style='text-align:center;'>{logo_img}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown("<div class='glass-card' style='padding:2rem;'>", unsafe_allow_html=True)
        brand_lockup()
        st.markdown("<h2 style='margin:0;letter-spacing:-.05em'>Student Sign In</h2><p style='color:#95aac1;margin:6px 0 1.2rem'>Access your virtual classroom &amp; study vault</p>", unsafe_allow_html=True)
        sign_in, register = st.tabs(["Sign in", "Create account"])
        with sign_in:
            username = st.text_input("Username", key="login_user", placeholder="Enter your username")
            password = st.text_input("Password", key="login_pwd", type="password", placeholder="Your password")
            if st.button("Access Workspace", type="primary", use_container_width=True):
                if auth.verify_user(username.strip(), password):
                    st.session_state.authenticated = True
                    st.session_state.current_user = username.strip()
                    st.session_state.current_view = "VirtualTutor"
                    st.rerun()
                st.error("Invalid username or password.")
        with register:
            new_username = st.text_input("Choose a username", key="register_user")
            new_password = st.text_input("Create a password", key="register_password", type="password")
            if st.button("Create Account", type="primary", use_container_width=True):
                if len(new_username.strip()) < 3 or len(new_password) < 6:
                    st.error("Username must be 3+ characters and password 6+ characters.")
                elif auth.create_user(new_username.strip(), new_password):
                    st.success("Account created successfully! Please sign in.")
                else:
                    st.error("That username already exists.")
        st.markdown("<div style='color:#8ca5be;font-size:.8rem;margin-top:1.2rem'>🔒 Private Document Vault · Evidence-Grounded Citations</div></div>", unsafe_allow_html=True)


# ==================== SIDEBAR ====================

def render_sidebar():
    with st.sidebar:
        brand_lockup()

        st.markdown("<div class='nav-caption'>Virtual Classroom</div>", unsafe_allow_html=True)
        st.button(
            "👩‍🏫  AI Virtual Tutor",
            key="nav_VirtualTutor",
            type="primary",
            use_container_width=True,
            on_click=_nav_to,
            args=("VirtualTutor",),
        )

        st.markdown("<div class='nav-caption'>Study &amp; RAG Tools</div>", unsafe_allow_html=True)
        study_views = [
            ("🏠  Dashboard", "Dashboard"),
            ("💬  Ask VidyaLoop", "Ask"),
            ("📍  Where Did I Learn This?", "WhereLearned"),
            ("🎓  Teach Me Mode", "TeachMe"),
            ("🎯  Exam Mode", "ExamMode"),
            ("❓  Question Generator", "QuestionGen"),
            ("🧪  Interactive Quiz", "QuizMode"),
            ("📝  Smart Notes", "SmartNotes"),
            ("⚖  Compare Documents", "Compare"),
            ("🗺  Knowledge Map", "KnowledgeMap"),
            ("📅  Study Planner", "StudyPlanner"),
            ("🧠  My Memory", "Memory"),
        ]
        for label, v in study_views:
            st.button(label, key=f"nav_{v}", use_container_width=True, on_click=_nav_to, args=(v,))

        st.markdown("<div class='nav-caption'>Vault &amp; Workspace</div>", unsafe_allow_html=True)
        st.button("📚  My Documents (Vault)", key="nav_Vault", use_container_width=True, on_click=_nav_to, args=("Vault",))
        st.button("⚙  Settings", key="nav_Settings", use_container_width=True, on_click=_nav_to, args=("Settings",))

        st.divider()
        voice_badge = (
            "<span class='badge-ok'>🎙 ElevenLabs Active</span>"
            if voice_service.is_voice_configured()
            else "<span class='badge-warn'>🎙 Voice Key Not Set</span>"
        )
        st.markdown(voice_badge, unsafe_allow_html=True)
        user = st.session_state.current_user or "Student"
        st.caption(f"LOGGED IN AS  ·  {user.upper()}")
        st.button("Log out", use_container_width=True, on_click=_logout)


# ==================== FEATURED VIEW: AI VIRTUAL TUTOR (FULL-SCREEN MA'AM) ====================

def _run_tutor_turn(question, doc_filter, style, mode, persona_name, model_id):
    """Execute one fast AI Virtual Tutor turn: existing RAG -> ElevenLabs timestamps TTS."""
    import ingest
    import rag_chain
    if not hasattr(ingest, "get_vocab_hints"):
        importlib.reload(ingest)
    if getattr(rag_chain, "RAG_VERSION", 0) < 6:
        importlib.reload(rag_chain)
    generate_tutor_lesson = rag_chain.generate_tutor_lesson

    persona_meta = voice_service.TUTOR_PERSONAS[persona_name]
    history = st.session_state.get("tutor_history", [])
    lesson = generate_tutor_lesson(
        question,
        chat_history=history,
        doc_filter=doc_filter,
        style=style,
        mode=mode,
        username=st.session_state.current_user,
    )
    audio_res = get_cached_voice_audio(
        lesson["spoken_script"],
        voice_id=persona_meta["voice_id"],
        model_id=model_id,
        max_chars=750,
    )
    st.session_state.tutor_current_lesson = lesson
    st.session_state.tutor_current_audio = audio_res
    st.session_state.tutor_last_question = question
    st.session_state.tutor_history.append({"role": "user", "content": question})
    st.session_state.tutor_history.append({
        "role": "assistant",
        "content": lesson["detailed_notes"],
        "spoken_script": lesson["spoken_script"],
        "board_title": lesson["board_title"],
        "sources": lesson.get("sources", []),
        "source_details": lesson.get("source_details", []),
    })


def render_virtual_tutor():
    from rag_chain import MODE_DOCUMENTS, MODE_GENERAL, TUTOR_STYLE_GUIDES

    if getattr(voice_service, "VOICE_VERSION", 0) < 6:
        importlib.reload(voice_service)

    docs = get_available_documents()
    persona_names = list(voice_service.TUTOR_PERSONAS.keys())
    model_labels = list(voice_service.ELEVENLABS_MODELS.keys())
    mic_lang_labels = list(voice_service.MIC_LANGUAGES.keys())
    style_names = list(TUTOR_STYLE_GUIDES.keys())

    if st.session_state.tutor_persona not in persona_names:
        st.session_state.tutor_persona = persona_names[0]
    if st.session_state.tutor_model_label not in model_labels:
        st.session_state.tutor_model_label = model_labels[0]
    if st.session_state.tutor_mic_lang not in mic_lang_labels:
        st.session_state.tutor_mic_lang = mic_lang_labels[0]
    if st.session_state.tutor_style not in style_names:
        st.session_state.tutor_style = style_names[0]

    # Minimal floating top-right utility strip: Source + History + Settings (zero clutter!)
    history_turns = [
        (st.session_state.tutor_history[i], st.session_state.tutor_history[i + 1])
        for i in range(0, len(st.session_state.tutor_history) - 1, 2)
    ]
    hist_label = f"🕘 History ({len(history_turns)})" if history_turns else "🕘 History"

    _, top_scope, top_hist, top_gear = st.columns([3.1, 1.35, 0.95, 0.55])
    with top_scope:
        scope_options = ["📚 My Notes", "⚡ General"] + [f"📄 {d}" for d in docs]
        scope_choice = st.selectbox("Source", scope_options, index=0, label_visibility="collapsed", key="vt_scope")
        if scope_choice == "⚡ General":
            mode = MODE_GENERAL
            doc_filter = None
        elif scope_choice == "📚 My Notes":
            mode = MODE_DOCUMENTS
            doc_filter = None
        else:
            mode = MODE_DOCUMENTS
            doc_filter = scope_choice.replace("📄 ", "", 1)
        st.session_state.tutor_mode = mode
    with top_hist:
        with st.popover(hist_label, use_container_width=True):
            if not history_turns:
                st.caption("No conversation yet — say hi or ask Ma'am a doubt!")
            else:
                st.markdown("**Recent Tutor Conversation**")
                for t_idx, (u_msg, a_msg) in enumerate(reversed(history_turns)):
                    real_idx = len(history_turns) - 1 - t_idx
                    st.markdown(
                        f"<div style='background:rgba(167,139,250,0.12);border:1px solid rgba(167,139,250,0.28);"
                        f"border-radius:12px;padding:7px 10px;margin-bottom:4px;font-size:.82rem;color:#eee8ff;'>"
                        f"<strong>You:</strong> {escape(u_msg.get('content', ''))}</div>"
                        f"<div style='background:rgba(112,229,255,0.08);border:1px solid rgba(112,229,255,0.22);"
                        f"border-radius:12px;padding:7px 10px;margin-bottom:5px;font-size:.82rem;color:#dcf2ff;'>"
                        f"<strong>Ma'am:</strong> {escape(a_msg.get('spoken_script') or a_msg.get('content', ''))}</div>",
                        unsafe_allow_html=True,
                    )
                    if a_msg.get("sources"):
                        st.caption("📄 " + " · ".join(a_msg["sources"][:2]))
                    if st.button("🔊 Replay on Stage", key=f"vt_replay_hist_{real_idx}", use_container_width=True):
                        p_meta = voice_service.TUTOR_PERSONAS[st.session_state.tutor_persona]
                        m_id = voice_service.ELEVENLABS_MODELS[st.session_state.tutor_model_label]
                        spoken = a_msg.get("spoken_script") or a_msg.get("content", "")
                        st.session_state.tutor_last_question = u_msg.get("content", "")
                        st.session_state.tutor_current_lesson = {
                            "spoken_script": spoken,
                            "board_title": a_msg.get("board_title", ""),
                            "board_points": [],
                            "detailed_notes": a_msg.get("content", spoken),
                            "check_question": "",
                            "sources": a_msg.get("sources", []),
                            "source_details": a_msg.get("source_details", []),
                        }
                        st.session_state.tutor_current_audio = get_cached_voice_audio(
                            spoken, voice_id=p_meta["voice_id"], model_id=m_id, max_chars=750
                        )
                        st.rerun()
                    st.divider()
                if st.button("🗑 Clear History", key="vt_clear_hist_btn", use_container_width=True):
                    st.session_state.tutor_history = []
                    st.session_state.tutor_current_lesson = None
                    st.session_state.tutor_current_audio = None
                    st.session_state.tutor_last_question = ""
                    st.rerun()
    with top_gear:
        with st.popover("⚙", use_container_width=True):
            persona_name = st.selectbox(
                "Voice (Ma'am):",
                persona_names,
                index=persona_names.index(st.session_state.tutor_persona),
                key="vt_persona_pop",
            )
            st.session_state.tutor_persona = persona_name

            style = st.selectbox(
                "Speaking Style:",
                style_names,
                index=style_names.index(st.session_state.tutor_style),
                key="vt_style_pop",
            )
            st.session_state.tutor_style = style

            model_label = st.selectbox(
                "Voice Speed / Language:",
                model_labels,
                index=model_labels.index(st.session_state.tutor_model_label),
                key="vt_model_pop",
            )
            st.session_state.tutor_model_label = model_label

            mic_lang_label = st.selectbox(
                "Mic Listening Language:",
                mic_lang_labels,
                index=mic_lang_labels.index(st.session_state.tutor_mic_lang),
                key="vt_mic_lang_pop",
            )
            st.session_state.tutor_mic_lang = mic_lang_label

            quota = voice_service.fetch_elevenlabs_quota()
            if quota:
                st.caption(f"⚡ Voice credits left: {quota['remaining']:,} / {quota['limit']:,}")
            if st.button("Clear Session", use_container_width=True, key="vt_reset_pop"):
                st.session_state.tutor_history = []
                st.session_state.tutor_current_lesson = None
                st.session_state.tutor_current_audio = None
                st.session_state.tutor_last_question = ""
                st.rerun()

    persona_name = st.session_state.tutor_persona
    persona_meta = voice_service.TUTOR_PERSONAS[persona_name]
    style = st.session_state.tutor_style
    model_id = voice_service.ELEVENLABS_MODELS[st.session_state.tutor_model_label]

    current_lesson = st.session_state.get("tutor_current_lesson")
    current_audio = st.session_state.get("tutor_current_audio")
    is_fresh = current_lesson is None
    if is_fresh:
        current_lesson = {
            "spoken_script": "Hi! Tap the mic below and ask me anything.",
            "board_title": "",
            "board_points": [],
            "detailed_notes": "",
            "check_question": "",
            "sources": [],
            "source_details": [],
        }

    # FULL-SCREEN BORDERLESS PIXAR-3D MA'AM + SPEECH BUBBLE CAPTIONS
    # Auto-reload tutor_avatar if Streamlit cached an older version across live edits
    if getattr(tutor_avatar, "AVATAR_VERSION", 0) < 3:
        importlib.reload(tutor_avatar)
    tutor_avatar.render_tutor_stage(
        persona_name=persona_name,
        persona_meta=persona_meta,
        lesson=current_lesson,
        audio_payload=current_audio,
        user_question="" if is_fresh else st.session_state.get("tutor_last_question", ""),
        autoplay=not is_fresh,
        height=560,
    )

    # CLEARLY VISIBLE MIC + CLEAN ASK BAR CENTERED DIRECTLY BELOW MA'AM
    _, mic_col, txt_col, _ = st.columns([0.45, 1.35, 2.75, 0.45], gap="small", vertical_alignment="center")
    with mic_col:
        mic_audio = st.audio_input("🎙️ Speak", key="vt_mic_input", label_visibility="collapsed")
        if mic_audio is not None:
            raw_bytes = mic_audio.getvalue()
            mic_digest = hashlib.sha256(raw_bytes).hexdigest()[:16]
            if mic_digest != st.session_state.get("tutor_last_mic_digest"):
                st.session_state.tutor_last_mic_digest = mic_digest
                mic_lang_code = voice_service.MIC_LANGUAGES.get(st.session_state.tutor_mic_lang)
                with st.spinner("Listening carefully…"):
                    stt = voice_service.transcribe_audio_bytes(
                        raw_bytes, filename="student_voice.wav", language=mic_lang_code
                    )
                if stt.get("ok") and stt.get("text"):
                    st.toast(f"🎙 Heard: {stt['text']}")
                    with st.spinner("Thinking…"):
                        _run_tutor_turn(stt["text"], doc_filter, style, mode, persona_name, model_id)
                    st.rerun()
                else:
                    st.warning(stt.get("error", "Could not hear clearly. Please speak closer to the mic."))

    with txt_col:
        with st.form("vt_question_form", clear_on_submit=True):
            q_col, b_col = st.columns([4.2, 1.0])
            with q_col:
                typed_q = st.text_input(
                    "Ask",
                    placeholder="Ask a doubt or say Hi…",
                    label_visibility="collapsed",
                )
            with b_col:
                ask_submitted = st.form_submit_button("Send →", type="primary", use_container_width=True)
        if ask_submitted and typed_q.strip():
            with st.spinner("Thinking…"):
                _run_tutor_turn(typed_q.strip(), doc_filter, style, mode, persona_name, model_id)
            st.rerun()

    # Only show cited PDF/PPTX page previews when sources exist (zero extra text!)
    if not is_fresh:
        details = current_lesson.get("source_details", [])
        if details:
            _, src_mid, _ = st.columns([0.45, 4.1, 0.45])
            with src_mid:
                render_searched_pages(details, key=f"vt_sources_{len(st.session_state.tutor_history)}")


# ==================== DASHBOARD ====================

def render_dashboard():
    user = st.session_state.current_user
    metrics = db_manager.get_dashboard_metrics(user)
    analytics = get_kb_analytics()

    page_heading(
        "VidyaLoop · Learn, Practice, Improve, Repeat.",
        f"Welcome back, {user.capitalize()}",
        "Your uploaded PDFs & PPTs, interactive AI Virtual Tutor, practice quizzes, and study progress in one place.",
    )

    # Featured AI Virtual Tutor Launch Card
    t_left, t_right = st.columns([3.1, 1.1], vertical_alignment="center")
    with t_left:
        st.markdown(
            "<div class='glass-card' style='border-color:rgba(112,229,255,.45);background:linear-gradient(125deg,rgba(20,44,86,.82),rgba(18,22,52,.82));margin-bottom:.6rem;'>"
            "<div style='display:flex;gap:8px;align-items:center;'>"
            "<span class='badge-doc'>Interactive Classroom</span>"
            "<span class='badge-voice'>ElevenLabs Voice + Live Captions</span>"
            "</div>"
            "<h3 style='margin:.45rem 0 .2rem;color:#f5fbff;'>👩‍🏫 Learn Live with Your AI Virtual Tutor</h3>"
            "<p style='color:#bcd0e4;font-size:.88rem;margin:0;'>Speak or type your doubts and learn from an animated AI Ma'am grounded in your uploaded PDFs &amp; PowerPoint slides.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
    with t_right:
        st.button("👩‍🏫 Start Virtual Class →", type="primary", use_container_width=True, key="dash_open_tutor", on_click=_nav_to, args=("VirtualTutor",))

    # 4 Core Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"<div class='glass-card'><div class='metric-label'>DOCUMENTS IN VAULT</div>"
            f"<div class='metric-value'>{analytics['total_files']}</div>"
            f"<div class='metric-hint'>{analytics['total_size_mb']} MB indexed</div></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div class='glass-card'><div class='metric-label'>QUESTIONS &amp; SESSIONS</div>"
            f"<div class='metric-value'>{metrics['questions_asked']}</div>"
            f"<div class='metric-hint'>Tutor &amp; RAG queries</div></div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"<div class='glass-card'><div class='metric-label'>QUIZ AVERAGE</div>"
            f"<div class='metric-value' style='color:#79f3c1;'>{metrics['avg_quiz_score']}%</div>"
            f"<div class='metric-hint'>{metrics['quizzes_completed']} quizzes completed</div></div>",
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"<div class='glass-card'><div class='metric-label'>STUDY PROGRESS</div>"
            f"<div class='metric-value'>{metrics['study_progress']}%</div>"
            f"<div class='metric-hint'>{metrics['saved_memories']} saved memory notes</div></div>",
            unsafe_allow_html=True,
        )

    col_left, col_right = st.columns([1.15, 0.85], gap="large")
    with col_left:
        st.markdown("<div class='glass-card'><div class='eyebrow'>Quick Study Tools</div><h3 style='margin:.35rem 0 .8rem;'>Jump Right In</h3>", unsafe_allow_html=True)
        q1, q2 = st.columns(2)
        with q1:
            st.button("💬 Ask Across Documents", use_container_width=True, on_click=_nav_to, args=("Ask",))
            st.button("🧪 Take Practice Quiz", use_container_width=True, on_click=_nav_to, args=("QuizMode",))
            st.button("📝 Generate Smart Notes", use_container_width=True, on_click=_nav_to, args=("SmartNotes",))
        with q2:
            st.button("📚 Upload PDFs & PPTs", use_container_width=True, on_click=_nav_to, args=("Vault",))
            st.button("🎯 Exam Mode Answers", use_container_width=True, on_click=_nav_to, args=("ExamMode",))
            st.button("📅 Open Study Planner", use_container_width=True, on_click=_nav_to, args=("StudyPlanner",))
        st.markdown("</div>", unsafe_allow_html=True)

        weak_topics = metrics.get("weak_topics", [])
        if weak_topics:
            st.markdown("<div class='glass-card'><div class='eyebrow'>Focus Areas</div><h3 style='margin:.35rem 0 .6rem;'>Topics to Review</h3>", unsafe_allow_html=True)
            chips = "".join(f"<span class='badge-weak'>⚠ {escape(w)}</span>" for w in weak_topics)
            st.markdown(chips, unsafe_allow_html=True)
            st.markdown("<div style='height:.6rem;'></div>", unsafe_allow_html=True)
            if st.button("🎯 Practice Weak Areas Now →", type="primary", use_container_width=True):
                st.session_state.quiz_topic_prefill = ", ".join(weak_topics[:3])
                st.session_state.current_view = "QuizMode"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("<div class='glass-card'><div class='eyebrow'>Recent Activity</div><h3 style='margin:.35rem 0 .8rem;'>Your Study Trail</h3>", unsafe_allow_html=True)
        recent = metrics.get("recent_activity", [])
        if recent:
            for act in recent:
                st.markdown(
                    f"<div style='font-size:.82rem;padding:6px 0;border-bottom:1px solid rgba(175,217,255,.08);'>"
                    f"<span style='color:#70e5ff;'>{escape(act['action'].replace('_', ' ').title())}</span>: {escape(act['detail'])} "
                    f"<span style='color:#6d849d;font-size:.72rem;'>({escape(str(act['timestamp'])[:16])})</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Your questions, quizzes, and tutor sessions will appear here.")
        st.markdown("</div>", unsafe_allow_html=True)


# ==================== INTERACTIVE QUIZ MODE ====================

def render_quiz_mode():
    from rag_chain import generate_quiz

    page_heading(
        "Grounded Assessment & Active Recall",
        "Interactive Quiz Mode",
        "Generate document-grounded multiple-choice quizzes with exact page/slide citations, instant feedback, and weak-topic tracking.",
    )

    docs = get_available_documents()
    prefill = st.session_state.get("quiz_topic_prefill", "")

    if prefill:
        st.info(f"🎯 Focus Topic Selected: **{prefill}**")

    if not st.session_state.active_quiz:
        c1, c2, c3, c4 = st.columns([2, 1.3, 1, 1])
        with c1:
            quiz_topic = st.text_input("Quiz Topic / Concept:", value=prefill, placeholder="e.g. Cyber Crime, Cryptography, Networking")
        with c2:
            doc_choice = st.selectbox("Source Document:", ["All Documents"] + docs)
            doc_filter = None if doc_choice == "All Documents" else doc_choice
        with c3:
            q_count = st.select_slider("Questions:", options=[3, 5, 8, 10], value=5)
        with c4:
            diff_choice = st.selectbox("Difficulty:", ["Easy", "Medium", "Hard"], index=1)

        if st.button("Generate Practice Quiz", type="primary"):
            with st.spinner("Generating document-grounded MCQs with citations…"):
                quiz = generate_quiz(
                    quiz_topic.strip(),
                    count=q_count,
                    doc_filter=doc_filter,
                    difficulty=diff_choice,
                )

            if not quiz:
                st.error("Could not generate quiz. Please check document selection or specify a broader topic.")
                return

            st.session_state.active_quiz = quiz
            st.session_state.quiz_submitted = False
            st.session_state.quiz_score = 0
            st.session_state.user_answers = {}
            st.session_state.quiz_weak_topics = []
            st.session_state.quiz_topic_prefill = ""
            st.rerun()

    else:
        quiz = st.session_state.active_quiz
        st.markdown(f"<div class='eyebrow'>Interactive Quiz ({len(quiz)} Questions)</div>", unsafe_allow_html=True)

        if not st.session_state.quiz_submitted:
            with st.form("quiz_form"):
                for idx, q in enumerate(quiz):
                    src_name = q.get("source_doc", "Vault")
                    unit = "Slide" if str(src_name).lower().endswith(".pptx") else "Page"
                    st.markdown(
                        f"<div class='quiz-question-box'>"
                        f"<div style='display:flex;justify-content:space-between;margin-bottom:6px;'>"
                        f"<span class='badge-doc'>📄 {escape(str(src_name))} ({unit} {q.get('page', 1)})</span>"
                        f"<span style='color:#70e5ff;font-size:.76rem;'>{escape(str(q.get('difficulty', 'Medium')))}</span>"
                        f"</div>"
                        f"<div class='quiz-question-title'>Q{idx+1}. {escape(q.get('question', ''))}</div>",
                        unsafe_allow_html=True,
                    )
                    options = q.get("options", ["A", "B", "C", "D"])
                    ans = st.radio(
                        f"Select answer for Q{idx+1}:",
                        options,
                        key=f"q_{idx}",
                        index=None,
                        label_visibility="collapsed",
                    )
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.session_state.user_answers[idx] = ans

                submitted = st.form_submit_button("Submit Quiz", type="primary")
                if submitted:
                    score = 0
                    weak_topics = []
                    for idx, q in enumerate(quiz):
                        user_ans = st.session_state.user_answers.get(idx)
                        correct_idx = q.get("answer_index", 0)
                        options = q.get("options", [])
                        correct_text = options[correct_idx] if options and correct_idx < len(options) else ""
                        if user_ans == correct_text:
                            score += 1
                        else:
                            t = q.get("topic", "General")
                            if t and t not in weak_topics:
                                weak_topics.append(t)

                    st.session_state.quiz_submitted = True
                    st.session_state.quiz_score = score
                    st.session_state.quiz_weak_topics = weak_topics

                    user = st.session_state.current_user
                    topic_label = quiz[0].get("topic", "Quiz")
                    db_manager.save_quiz_result(user, topic_label, quiz[0].get("source_doc", "Vault"), score, len(quiz), weak_topics)
                    st.rerun()

        else:
            score = st.session_state.quiz_score
            total = len(quiz)
            percentage = round((score / total) * 100, 1)

            st.markdown(
                f"<div class='score-banner'>"
                f"<div class='eyebrow'>Quiz Completed</div>"
                f"<h1 style='font-size:3.2rem;margin:.4rem 0;color:#70e5ff;'>{score} / {total}</h1>"
                f"<div style='font-size:1.1rem;color:#e8f4ff;'>Accuracy: <strong>{percentage}%</strong></div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            weak = st.session_state.quiz_weak_topics
            if weak:
                st.markdown("<div class='glass-card'><div class='eyebrow'>Review Suggestions</div><h3 style='margin:.3rem 0 .7rem'>Weak Areas Detected:</h3>", unsafe_allow_html=True)
                chips = "".join(f"<span class='badge-weak'>⚠ {escape(w)}</span>" for w in weak)
                st.markdown(chips, unsafe_allow_html=True)
                st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
                if st.button("🎯 Practice My Weak Areas Now", type="primary", use_container_width=True):
                    st.session_state.quiz_topic_prefill = ", ".join(weak)
                    st.session_state.active_quiz = []
                    st.session_state.quiz_submitted = False
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("### Answer Review & Grounded Sources:")
            for idx, q in enumerate(quiz):
                user_ans = st.session_state.user_answers.get(idx)
                correct_idx = q.get("answer_index", 0)
                options = q.get("options", [])
                correct_text = options[correct_idx] if correct_idx < len(options) else ""
                is_correct = user_ans == correct_text
                src_name = str(q.get("source_doc", "Document"))
                unit = "Slide" if src_name.lower().endswith(".pptx") else "Page"

                card_border = "rgba(121,243,193,.4)" if is_correct else "rgba(255,107,107,.4)"
                status_badge = "✅ Correct" if is_correct else "❌ Incorrect"
                st.markdown(
                    f"<div class='glass-card' style='border-color:{card_border};'>"
                    f"<div style='display:flex;justify-content:space-between;'>"
                    f"<strong>Q{idx+1}. {escape(q.get('question', ''))}</strong>"
                    f"<span>{status_badge}</span></div>"
                    f"<div style='margin-top:.7rem;font-size:.88rem;'>"
                    f"Your answer: <code style='color:{'#79f3c1' if is_correct else '#ff8787'}'>{escape(str(user_ans))}</code><br>"
                    f"Correct answer: <code style='color:#79f3c1'>{escape(correct_text)}</code></div>"
                    f"<div style='margin-top:.7rem;color:#b2c7dc;font-size:.85rem;background:rgba(0,0,0,.25);padding:8px 12px;border-radius:10px;'>"
                    f"<strong>Explanation:</strong> {escape(q.get('explanation', ''))}<br>"
                    f"<span style='color:#70e5ff;font-size:.76rem;'>Source: 📄 {escape(src_name)} ({unit} {q.get('page', 'N/A')})</span></div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Ask AI Virtual Tutor About Mistakes →", type="primary", use_container_width=True):
                    st.session_state.current_view = "VirtualTutor"
                    st.rerun()
            with col_b:
                if st.button("Take Another Quiz", use_container_width=True):
                    st.session_state.active_quiz = []
                    st.session_state.quiz_submitted = False
                    st.rerun()


# ==================== ASK VIDYALOOP ====================

def render_ask_brain():
    from rag_chain import MODE_DOCUMENTS, MODE_GENERAL, ask_question

    page_heading("VidyaLoop · Learn, Practice, Improve, Repeat.", "Ask VidyaLoop", "Query across all uploaded PDFs, PPTs, and notes simultaneously. Verified citations, page previews, and ElevenLabs voice playback included.")

    docs = get_available_documents()
    filter_col, mode_col, info_col = st.columns([1.2, 1.1, 1.1])
    with filter_col:
        doc_options = ["All Documents"] + docs
        selected_doc = st.selectbox("Search Scope:", doc_options, index=0)
        doc_filter = None if selected_doc == "All Documents" else selected_doc
    with mode_col:
        ask_mode_label = st.radio(
            "Chat Mode:",
            ["📄 Documents", "⚡ General"],
            index=0 if st.session_state.ask_mode == MODE_DOCUMENTS else 1,
            horizontal=True,
            key="ask_mode_radio",
        )
        ask_mode = MODE_DOCUMENTS if ask_mode_label.startswith("📄") else MODE_GENERAL
        st.session_state.ask_mode = ask_mode
    with info_col:
        st.markdown(
            f"<div style='margin-top:1.7rem;'><span class='badge-doc'>Scope: {escape(selected_doc)}</span> &nbsp;"
            f"<span style='color:#8ba3be;font-size:.82rem;'>{len(docs)} file(s) in vault</span></div>",
            unsafe_allow_html=True,
        )

    if not st.session_state.chat_history:
        st.markdown(
            "<div class='glass-card empty-state'><div class='brain-visual'>🧠</div>"
            "<h3 style='color:#f0f7ff;margin:0'>Ask anything about your documents</h3>"
            "<p>Example: 'What is the classification of cyber crime?' or switch to ⚡ General for open Q&amp;A.</p></div>",
            unsafe_allow_html=True,
        )

    for idx, message in enumerate(st.session_state.chat_history):
        with st.chat_message(message["role"], avatar="🧠" if message["role"] == "assistant" else "👤"):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                verified_details = [d for d in message.get("source_details", []) if d.get("evidence") or d.get("source")]
                if verified_details:
                    st.markdown("".join(f"<span class='source-chip'>{escape(d['label'])}</span>" for d in verified_details), unsafe_allow_html=True)
                    render_searched_pages(verified_details, key=f"chat_msg_{idx}")
                render_voice_player(message["content"], key=f"chat_voice_{idx}")

    if prompt := st.chat_input("Ask anything across your knowledge base…"):
        prior_history = list(st.session_state.chat_history)
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("Searching documents and verifying citations…"):
                result = ask_question(
                    prompt,
                    chat_history=prior_history,
                    doc_filter=doc_filter,
                    username=st.session_state.current_user,
                    mode=ask_mode,
                )

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result.get("sources", []),
            "source_details": result.get("source_details", []),
        })
        st.rerun()


# ==================== WHERE DID I LEARN THIS? ====================

def render_where_learned():
    from rag_chain import where_did_i_learn

    page_heading("Knowledge Origin Finder", "Where Did I Learn This?", "Search your notes, books, and lecture slides to find exact filenames, sections, and pages where a concept is taught.")

    docs = get_available_documents()
    c1, c2 = st.columns([2.2, 1])
    with c1:
        concept_query = st.text_input("Concept or Topic:", placeholder="e.g. Credit Card Fraud, Salami Attack, Karma Yoga...")
    with c2:
        doc_choice = st.selectbox("Search In:", ["All Documents"] + docs)
        doc_filter = None if doc_choice == "All Documents" else doc_choice

    if st.button("Find Knowledge Origin", type="primary"):
        if not concept_query.strip():
            st.warning("Please enter a concept or topic.")
            return

        with st.spinner(f"Locating '{concept_query}' across your document vault…"):
            st.session_state.where_learned_result = where_did_i_learn(concept_query.strip(), doc_filter=doc_filter)

    result = st.session_state.get("where_learned_result")
    if result:
        if not result.get("found") or not result.get("locations"):
            st.info(result.get("message", "No mentions found in uploaded materials."))
            return

        st.markdown(f"<div class='glass-card' style='border-color:rgba(112,229,255,.4)'><div class='eyebrow'>Search Summary</div><p style='font-size:1.05rem;color:#e8f4ff;margin:.3rem 0 0;'>{escape(result.get('summary', ''))}</p></div>", unsafe_allow_html=True)

        locations = result.get("locations", [])
        st.markdown(f"### Found in {len(locations)} Location(s):")
        for idx, loc in enumerate(locations):
            doc_name = source_basename(loc.get("document", "Unknown"))
            page_num = loc.get("page", "N/A")
            section = loc.get("section", "Section")
            snippet = loc.get("snippet", "")
            takeaway = loc.get("takeaway", "")
            unit = "Slide" if doc_name.lower().endswith(".pptx") else "Page"

            with st.container():
                st.markdown(
                    f"""<div class='glass-card'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <span class='badge-doc'>📄 {escape(doc_name)}</span>
                        <span class='source-chip'>{unit} {escape(str(page_num))}</span>
                    </div>
                    <h4 style='color:#70e5ff;margin:.6rem 0 .3rem;'>📌 {escape(section)}</h4>
                    <p style='color:#c5d8ed;font-size:.9rem;line-height:1.6;font-style:italic;background:rgba(0,0,0,.25);padding:8px 12px;border-radius:10px;'>"{escape(snippet)}"</p>
                    <p style='color:#8ca5be;font-size:.85rem;margin:0;'><strong>Takeaway:</strong> {escape(takeaway)}</p>
                    </div>""",
                    unsafe_allow_html=True,
                )
                file_path = resolve_upload_path(os.path.join(UPLOAD_DIR, doc_name))
                if os.path.exists(file_path) and isinstance(page_num, int):
                    if doc_name.lower().endswith(".pdf"):
                        if st.checkbox(f"Preview {doc_name} — Page {page_num}", key=f"preview_loc_{idx}"):
                            render_pdf_page(file_path, page_num - 1, f"{doc_name} (Page {page_num})")
                    elif doc_name.lower().endswith(".pptx"):
                        if st.checkbox(f"Preview {doc_name} — Slide {page_num}", key=f"preview_loc_ppt_{idx}"):
                            render_pptx_slide(file_path, page_num - 1, f"{doc_name} (Slide {page_num})")


# ==================== TEACH ME MODE ====================

def render_teach_me():
    from rag_chain import teach_me

    page_heading("Pedagogical AI", "Teach Me Mode", "Beginner-friendly explanations that progressively become technical, grounded strictly in your study materials.")

    docs = get_available_documents()
    col1, col2 = st.columns([2, 1])
    with col1:
        topic = st.text_input("What topic would you like me to teach?", placeholder="e.g. SQL Injection, Phishing, Cyber Stalking")
    with col2:
        doc_choice = st.selectbox("Base on Document:", ["Auto-detect across all documents"] + docs)
        doc_filter = None if doc_choice == "Auto-detect across all documents" else doc_choice

    if st.button("Teach Me This Topic", type="primary"):
        if not topic.strip():
            st.warning("Please specify a topic.")
            return

        with st.spinner(f"Preparing a structured masterclass on '{topic}'…"):
            st.session_state.teach_me_last = {
                "topic": topic.strip(),
                "content": teach_me(topic.strip(), doc_filter=doc_filter),
            }

    last_teach = st.session_state.get("teach_me_last")
    if last_teach:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown(last_teach["content"])
        st.markdown("</div>", unsafe_allow_html=True)
        render_voice_player(last_teach["content"], key=f"teach_me_{last_teach['topic'][:24]}", label="🔊 Listen to Masterclass (ElevenLabs)")


# ==================== EXAM MODE ====================

def render_exam_mode():
    from rag_chain import generate_exam_answer

    page_heading("Exam Ready Answers", "Exam Mode", "Generate high-scoring, structured university answers tailored precisely for 2, 5, 7, or 10 marks.")

    docs = get_available_documents()
    c1, c2, c3 = st.columns([2, 1.2, 1])
    with c1:
        topic = st.text_input("Exam Question or Topic:", placeholder="e.g. Classification of Cyber Crime, Malware Types")
    with c2:
        marks = st.radio("Target Marks:", [2, 5, 7, 10], index=2, horizontal=True)
    with c3:
        doc_choice = st.selectbox("Syllabus Source:", ["All Documents"] + docs)
        doc_filter = None if doc_choice == "All Documents" else doc_choice

    if st.button(f"Generate {marks}-Mark Exam Answer", type="primary"):
        if not topic.strip():
            st.warning("Please enter an exam question or topic.")
            return

        with st.spinner(f"Writing {marks}-mark university answer for '{topic}'…"):
            st.session_state.exam_mode_last = {
                "topic": topic.strip(),
                "marks": marks,
                "content": generate_exam_answer(topic.strip(), marks=marks, doc_filter=doc_filter),
            }

    last_exam = st.session_state.get("exam_mode_last")
    if last_exam:
        st.markdown(f"<div class='glass-card'><div class='eyebrow'>Exam Response · {last_exam['marks']} Marks</div>", unsafe_allow_html=True)
        st.markdown(last_exam["content"])
        st.markdown("</div>", unsafe_allow_html=True)
        render_voice_player(last_exam["content"], key=f"exam_{last_exam['marks']}_{last_exam['topic'][:20]}", label="🔊 Listen to Exam Answer (ElevenLabs)")


# ==================== QUESTION GENERATOR ====================

def render_question_generator():
    from rag_chain import generate_questions

    page_heading("Exam Prep & Question Paper Studio", "Automatic Question Generator", "Generate customized examination questions, test papers, or viva questions from your documents.")

    docs = get_available_documents()
    c1, c2, c3 = st.columns([1.5, 1.2, 1])
    with c1:
        topic = st.text_input("Topic or Unit Focus:", placeholder="e.g. Cyber Crime Unit 1, Network Security")
    with c2:
        q_type = st.selectbox("Question Type:", ["MCQs", "2-mark questions", "5-mark questions", "7-mark questions", "Viva questions"])
    with c3:
        count = st.slider("Count:", min_value=3, max_value=12, value=5)

    doc_choice = st.selectbox("Target Document:", ["All Uploaded Documents"] + docs)
    doc_filter = None if doc_choice == "All Uploaded Documents" else doc_choice

    if st.button("Generate Questions", type="primary"):
        with st.spinner(f"Generating {count} {q_type}…"):
            output = generate_questions(topic.strip(), question_type=q_type, count=count, doc_filter=doc_filter)

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown(output)
        st.markdown("</div>", unsafe_allow_html=True)


# ==================== SMART NOTES ====================

def render_smart_notes():
    from rag_chain import generate_smart_notes

    page_heading("Document Intelligence", "Smart Notes", "Structured, high-yield academic summaries capturing key definitions, frameworks, examples, and exam questions.")

    docs = get_available_documents()
    if not docs:
        st.warning("No documents in your vault yet. Please upload files in My Documents first.")
        return

    c1, c2 = st.columns([1.5, 1])
    with c1:
        doc_choice = st.selectbox("Choose Document:", docs)
    with c2:
        topic_focus = st.text_input("Optional Topic Focus:", placeholder="Leave empty for full summary")

    if st.button("Generate Smart Notes", type="primary"):
        with st.spinner(f"Distilling notes for '{doc_choice}'…"):
            notes = generate_smart_notes(doc_choice, topic=topic_focus.strip() or None)

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown(notes)
        st.download_button(
            "Download Smart Notes (.md)",
            data=notes,
            file_name=f"Smart_Notes_{os.path.splitext(doc_choice)[0]}.md",
            mime="text/markdown",
        )
        st.markdown("</div>", unsafe_allow_html=True)


# ==================== COMPARE DOCUMENTS ====================

def render_compare():
    from rag_chain import compare_documents

    page_heading("Comparative Analysis", "Compare Documents", "Identify commonalities, sharp differences, unique concepts, and knowledge gaps between two documents.")

    docs = get_available_documents()
    if len(docs) < 2:
        st.warning("Please upload at least 2 documents in 'My Documents' to compare them.")
        return

    c1, c2, c3 = st.columns([1, 1, 1.2])
    with c1:
        doc_a = st.selectbox("Document A:", docs, index=0)
    with c2:
        doc_b = st.selectbox("Document B:", docs, index=min(1, len(docs) - 1))
    with c3:
        topic = st.text_input("Comparison Focus (Optional):", placeholder="e.g. Architecture, Security Controls, Key Concepts")

    if st.button("Run Comparative Analysis", type="primary"):
        if doc_a == doc_b:
            st.warning("Please choose two different documents to compare.")
            return

        with st.spinner(f"Comparing '{doc_a}' vs '{doc_b}'…"):
            result = compare_documents(doc_a, doc_b, topic=topic.strip() or None)

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown(result)
        st.markdown("</div>", unsafe_allow_html=True)


# ==================== PERSONAL MEMORY ====================

def render_memory():
    user = st.session_state.current_user
    page_heading("Personal Knowledge Layer", "My Memory", "Save personal notes, formulas, and facts separate from uploaded documents. Search and recall them at any time.")

    tab_browse, tab_add = st.tabs(["📖 Browse & Recall Memories", "➕ Save New Memory"])

    with tab_add:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        m_title = st.text_input("Title / Topic:", placeholder="e.g. OSI Model Layers, Encryption Formula")
        m_content = st.text_area("Memory Content / Fact:", placeholder="Enter your note, definition, or key takeaway here...", height=120)
        m_tags = st.text_input("Tags (comma separated):", placeholder="e.g. security, exam, formula")

        if st.button("Save to My Memory", type="primary"):
            if not m_content.strip():
                st.warning("Please enter note content.")
            else:
                db_manager.save_memory(user, m_content, title=m_title, tags=m_tags)
                st.success(f"Saved to My Memory: '{m_title or 'Note'}'")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_browse:
        search_query = st.text_input("Search My Memory:", placeholder="Filter by keyword, title, or tag...")
        memories = db_manager.get_memories(user, search_query=search_query)

        if not memories:
            st.markdown(
                "<div class='empty-state'><div class='brain-visual' style='font-size:3rem;'>🧠</div>"
                "<p>No personal memories found. Add one in the 'Save New Memory' tab!</p></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"<span class='badge-memory'>Showing {len(memories)} Saved Memory Item(s)</span>", unsafe_allow_html=True)
            for mem in memories:
                with st.container():
                    c_text, c_del = st.columns([5, 1])
                    with c_text:
                        tag_html = f"<div style='font-size:.75rem;color:#70e5ff;'>🏷 Tags: {escape(mem['tags'])}</div>" if mem.get("tags") else ""
                        st.markdown(
                            f"<div class='glass-card' style='margin-bottom:.6rem;'>"
                            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                            f"<span class='badge-memory'>🧠 {escape(mem['title'])}</span>"
                            f"<span style='color:#758da4;font-size:.75rem;'>{escape(str(mem['created_at'])[:16])}</span>"
                            f"</div>"
                            f"<p style='color:#e4f1ff;margin:.6rem 0;line-height:1.6;'>{escape(mem['content'])}</p>"
                            f"{tag_html}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    with c_del:
                        if st.button("Delete", key=f"del_mem_{mem['id']}"):
                            db_manager.delete_memory(user, mem["id"])
                            st.toast("Memory deleted.")
                            st.rerun()


# ==================== KNOWLEDGE MAP ====================

def render_knowledge_map():
    from rag_chain import extract_concept_graph

    page_heading("Visual Concept Map", "Knowledge Map", "Extract important concepts and their interrelationships from your uploaded documents.")

    docs = get_available_documents()
    c1, c2 = st.columns([1.5, 1.2])
    with c1:
        doc_choice = st.selectbox("Select Document:", ["All Documents"] + docs)
        doc_filter = None if doc_choice == "All Documents" else doc_choice
    with c2:
        topic_focus = st.text_input("Focus Topic (Optional):", placeholder="e.g. Cyber Crime, Security Attacks")

    if st.button("Generate Concept Graph", type="primary"):
        with st.spinner("Extracting concepts and relationship ontology…"):
            graph_data = extract_concept_graph(doc_name=doc_filter, focus_topic=topic_focus.strip() or None)

        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        if not nodes:
            st.info("No concepts extracted. Please upload documents with rich textual content.")
            return

        st.markdown(f"### 🌐 Extracted {len(nodes)} Concepts & {len(edges)} Relationships:")

        mermaid_lines = [
            "graph TD",
            "classDef root fill:#1c3974,stroke:#70e5ff,stroke-width:2px,color:#fff;",
            "classDef branch fill:#10254c,stroke:#9194ff,stroke-width:1.5px,color:#fff;",
            "classDef leaf fill:#0c1933,stroke:#6688aa,stroke-width:1px,color:#dcecff;",
        ]

        clean_id_map = {}
        for idx, node in enumerate(nodes):
            safe_id = f"node_{idx}"
            label = node.get("label", "").replace('"', "").replace("'", "")
            category = node.get("category", "branch")
            clean_id_map[node.get("id", safe_id)] = (safe_id, label, category)
            mermaid_lines.append(f'{safe_id}["{label}"]:::{category}')

        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            rel = edge.get("relationship", "relates_to").replace("_", " ")
            if src in clean_id_map and tgt in clean_id_map:
                mermaid_lines.append(f"{clean_id_map[src][0]} -->|{rel}| {clean_id_map[tgt][0]}")

        mermaid_code = "\n".join(mermaid_lines)
        st.markdown(f"```mermaid\n{mermaid_code}\n```")

        with st.expander("View Concept & Relationship Table"):
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.markdown("**Identified Concepts:**")
                for n in nodes:
                    st.write(f"• **{n.get('label')}** ({n.get('category', 'concept')})")
            with t_col2:
                st.markdown("**Relationships:**")
                for e in edges:
                    st.write(f"• `{e.get('source')}` → *{e.get('relationship', '')}* → `{e.get('target')}`")


# ==================== STUDY PLANNER ====================

def render_study_planner():
    from rag_chain import generate_study_plan_schedule

    user = st.session_state.current_user
    page_heading("Exam Strategist", "Study Planner", "Analyze uploaded syllabus materials and generate an active day-by-day study schedule with milestone tracking.")

    latest_plan = db_manager.get_latest_study_plan(user)
    docs = get_available_documents()

    tab_active, tab_create = st.tabs(["📅 Current Study Plan", "⚡ Create New Plan"])

    with tab_create:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        subject = st.text_input("Subject / Course Name:", placeholder="e.g. Cyber Security, Computer Networks")
        exam_date = st.date_input("Target Exam Date:", min_value=date.today() + timedelta(days=1), value=date.today() + timedelta(days=7))
        daily_hours = st.slider("Available Study Hours Per Day:", min_value=1.0, max_value=10.0, value=3.0, step=0.5)
        selected_materials = st.multiselect("Select Course Documents from Vault:", docs, default=docs[:2] if len(docs) >= 2 else docs)

        if st.button("Generate AI Study Schedule", type="primary"):
            if not subject.strip():
                st.warning("Please enter a subject name.")
            else:
                with st.spinner(f"Crafting optimized study plan for '{subject}'…"):
                    schedule = generate_study_plan_schedule(subject.strip(), exam_date, daily_hours, doc_names=selected_materials)

                if schedule:
                    db_manager.save_study_plan(user, subject.strip(), exam_date, daily_hours, schedule)
                    st.success("Study plan created and saved!")
                    st.rerun()
                else:
                    st.error("Could not generate schedule. Please check document content or input.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_active:
        if not latest_plan or not latest_plan.get("schedule"):
            st.markdown(
                "<div class='glass-card empty-state'><div class='brain-visual' style='font-size:3rem;'>📅</div>"
                "<p>No active study plan found. Create one in the 'Create New Plan' tab!</p></div>",
                unsafe_allow_html=True,
            )
        else:
            schedule = latest_plan["schedule"]
            progress = latest_plan.get("progress", {})

            total_days = len(schedule)
            completed_count = sum(1 for v in progress.values() if v)
            percent = round((completed_count / total_days) * 100) if total_days > 0 else 0

            st.markdown(
                f"<div class='glass-card'>"
                f"<div class='eyebrow'>Active Schedule</div>"
                f"<h2 style='margin:.3rem 0 .2rem;'>{escape(latest_plan['subject'])}</h2>"
                f"<p style='color:#8ea7c1;font-size:.88rem;'>Target Exam Date: <strong>{latest_plan['exam_date']}</strong> &nbsp;|&nbsp; Daily Commitment: <strong>{latest_plan['daily_hours']} hrs/day</strong></p>"
                f"</div>",
                unsafe_allow_html=True,
            )

            st.progress(percent / 100.0, text=f"Progress: {completed_count} of {total_days} Days Completed ({percent}%)")

            updated = False
            for idx, day_info in enumerate(schedule):
                day_num = day_info.get("day", idx + 1)
                title = day_info.get("title", f"Day {day_num}")
                milestone = day_info.get("milestone", "")
                tasks = day_info.get("tasks", [])
                is_checked = progress.get(str(idx), False)

                with st.container():
                    c_chk, c_body = st.columns([0.08, 0.92])
                    with c_chk:
                        chk = st.checkbox(f"Complete Day {day_num}", value=is_checked, key=f"plan_task_{idx}", label_visibility="collapsed")
                        if chk != is_checked:
                            progress[str(idx)] = chk
                            updated = True
                    with c_body:
                        st.markdown(
                            f"<div style='background:rgba(255,255,255,0.03);padding:10px 14px;border-radius:12px;margin-bottom:8px;border:1px solid rgba(175,217,255,.1);'>"
                            f"<strong style='color:{'#79f3c1' if chk else '#e8f4ff'};'>Day {day_num}: {escape(title)}</strong>"
                            f"<div style='color:#70e5ff;font-size:.78rem;'>🎯 Milestone: {escape(milestone)}</div>"
                            f"<ul style='margin:6px 0 0;padding-left:20px;font-size:.84rem;color:#b2c8dc;'>"
                            + "".join(f"<li>{escape(t)}</li>" for t in tasks)
                            + "</ul></div>",
                            unsafe_allow_html=True,
                        )

            if updated:
                db_manager.update_plan_progress(latest_plan["id"], progress)
                st.rerun()


# ==================== VAULT / MY DOCUMENTS ====================

def ingest_uploaded_files(uploaded_files, progress_area):
    from ingest import ingest_file

    outcomes = []
    for uploaded_file in uploaded_files:
        safe_name = os.path.basename(uploaded_file.name)
        if safe_name in st.session_state.files_ingested:
            outcomes.append(("skipped", safe_name, "Already indexed"))
            continue
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        try:
            with open(file_path, "wb") as destination:
                destination.write(uploaded_file.getbuffer())
            progress_bar = progress_area.progress(0, text=f"Preparing {safe_name}…")

            def on_progress(stage, percentage):
                progress_bar.progress(min(max(int(percentage), 0), 100), text=f"{safe_name} · {stage}")

            chunk_count = ingest_file(file_path, progress_callback=on_progress)
            progress_bar.progress(100, text=f"{safe_name} · indexed successfully")
            st.session_state.files_ingested.append(safe_name)
            outcomes.append(("success", safe_name, f"{chunk_count} knowledge chunks indexed"))
        except Exception as error:
            if os.path.exists(file_path):
                os.remove(file_path)
            outcomes.append(("error", safe_name, str(error)))
    st.session_state.files_ingested.sort()
    return outcomes


def render_vault():
    from ingest import remove_file_from_index

    page_heading("Document Vault", "My Documents", "Upload PDFs, PowerPoint slides (PPTX), DOCX, and TXT files. Files are indexed locally and grounded for instant search.")

    upload_col, files_col = st.columns([0.9, 1.35], gap="large")
    with upload_col:
        st.markdown(
            "<div class='glass-card'><div class='eyebrow'>Add Knowledge</div>"
            "<h3 style='margin:.55rem 0 .3rem'>Drop Files into Vault</h3>"
            "<p style='color:#9badc4;font-size:.88rem;line-height:1.6'>Supports PDFs (with OCR fallback), PowerPoint (.pptx) decks with slide citations, DOCX, and TXT.</p>",
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader(
            "Choose files", type=["pdf", "pptx", "docx", "txt"],
            accept_multiple_files=True, label_visibility="collapsed",
        )
        progress_area = st.empty()
        if uploaded:
            for state, name, detail in ingest_uploaded_files(uploaded, progress_area):
                if state == "success":
                    st.success(f"{name} — {detail}")
                elif state == "error":
                    st.error(f"{name} could not be indexed: {detail}")
                else:
                    st.info(f"{name} — {detail}")
        st.markdown("<p style='color:#7890aa;font-size:.75rem;margin:1.1rem 0 0'>Supported: PDF, PPTX, DOCX, UTF-8 TXT · Page &amp; Slide citations preserved.</p></div>", unsafe_allow_html=True)

    with files_col:
        st.markdown("<div class='glass-card'><div class='eyebrow'>Indexed Vault Files</div><h3 style='margin:.55rem 0 1rem'>Your Documents</h3>", unsafe_allow_html=True)
        if not st.session_state.files_ingested:
            st.markdown("<div class='empty-state' style='padding:2.2rem 1rem;'><div class='brain-visual' style='font-size:3rem;'>🧠</div><p>No indexed documents yet.</p></div>", unsafe_allow_html=True)

        for name in list(st.session_state.files_ingested):
            path = os.path.join(UPLOAD_DIR, name)
            size = f"{get_file_size_mb(path):.2f} MB" if os.path.exists(path) else "File unavailable"
            row, view_action, action = st.columns([4.2, 1, 1])
            with row:
                st.markdown(f"<div class='file-row'><div class='file-name'>◫ &nbsp;{escape(name)}</div><div class='file-meta'>{size} · Ready for search</div></div>", unsafe_allow_html=True)
            with view_action:
                is_previewable = name.lower().endswith((".pdf", ".pptx"))
                if is_previewable and st.button("View", key=f"view_{name}", help=f"Open {name} in the app"):
                    st.session_state.open_pdf = None if st.session_state.get("open_pdf") == name else name
            with action:
                if st.button("Remove", key=f"remove_{name}", help=f"Remove {name} from index"):
                    try:
                        remove_file_from_index(path)
                        if os.path.exists(path):
                            os.remove(path)
                        st.session_state.files_ingested.remove(name)
                        st.toast(f"Removed {name} from vault")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Could not remove {name}: {error}")

            if st.session_state.get("open_pdf") == name and os.path.exists(path):
                st.markdown(f"<div style='height:.6rem'></div><div class='eyebrow'>Document Viewer · {escape(name)}</div>", unsafe_allow_html=True)
                if name.lower().endswith(".pptx"):
                    render_pptx_document(path)
                else:
                    render_pdf_document(path)
        st.markdown("</div>", unsafe_allow_html=True)


# ==================== SETTINGS ====================

def render_settings():
    page_heading("Workspace Management", "Settings", "Manage conversation history or reset the knowledge base.")

    st.markdown("<div class='glass-card'><div class='eyebrow'>Conversation</div><h3 style='margin:.5rem 0 .3rem;'>Start Fresh</h3><p style='color:#9badc4'>Clear active chat and virtual tutor history while keeping all your documents and memories intact.</p>", unsafe_allow_html=True)
    if st.button("Clear Chat & Tutor History"):
        st.session_state.chat_history = []
        st.session_state.tutor_history = []
        st.session_state.tutor_current_lesson = None
        st.session_state.tutor_current_audio = None
        st.success("Conversation history cleared.")

    st.markdown("</div><div style='height:1rem;'></div><div class='glass-card' style='border-color:rgba(255,117,141,.3);'><div class='eyebrow' style='color:#ff9aab'>Danger Zone</div><h3 style='margin:.5rem 0 .3rem;'>Reset Knowledge Vault</h3><p style='color:#bca4ad'>Permanently delete every uploaded document and the local search index.</p>", unsafe_allow_html=True)
    confirm = st.checkbox("I understand this permanently clears my local vault.")
    if st.button("Reset All Knowledge", disabled=not confirm):
        reset_database()
        clear_uploads()
        st.session_state.files_ingested = []
        st.session_state.chat_history = []
        st.session_state.tutor_history = []
        st.session_state.tutor_current_lesson = None
        st.session_state.tutor_current_audio = None
        st.success("Local knowledge vault reset.")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ==================== APP ROUTER ====================

init_state()
inject_styles(fullscreen_tutor=(st.session_state.authenticated and st.session_state.current_view == "VirtualTutor"))

if not st.session_state.boot_complete:
    render_boot()
elif not st.session_state.authenticated:
    render_auth()
else:
    render_sidebar()
    views = {
        "VirtualTutor": render_virtual_tutor,
        "Dashboard": render_dashboard,
        "Ask": render_ask_brain,
        "WhereLearned": render_where_learned,
        "TeachMe": render_teach_me,
        "ExamMode": render_exam_mode,
        "QuestionGen": render_question_generator,
        "QuizMode": render_quiz_mode,
        "SmartNotes": render_smart_notes,
        "Compare": render_compare,
        "KnowledgeMap": render_knowledge_map,
        "StudyPlanner": render_study_planner,
        "Memory": render_memory,
        "Vault": render_vault,
        "Settings": render_settings,
    }
    view_func = views.get(st.session_state.current_view, render_virtual_tutor)
    view_func()
