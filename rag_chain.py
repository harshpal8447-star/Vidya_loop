"""Strict, evidence-grounded Document Intelligence & Study Assistant Engine."""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

import httpx
from dotenv import load_dotenv
from groq import Groq

import db_manager
from ingest import get_vectorstore, normalize_source_path, source_basename

load_dotenv()

LLM_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "openai/gpt-oss-20b")
RAG_VERSION = 6
RETRIEVAL_K = 12
NOT_FOUND_MESSAGE = "I could not find this information in the uploaded document(s)."

# Chat modes: "documents" = strict grounding in uploaded files,
#             "general"   = free assistant using the model's own knowledge.
MODE_DOCUMENTS = "documents"
MODE_GENERAL = "general"

NOT_FOUND_HINT = (
    "\n\n_Tip: you are in **📄 Documents** mode. For general-knowledge questions "
    "(like 'what is AI'), switch the chat toggle to **⚡ General**._"
)

PROMPT_TEMPLATE = """
You are VidyaLoop, a strict document-grounded assistant.

Answer the current question using ONLY facts explicitly supported by the
uploaded-document excerpts below. Do not use general knowledge, guesses,
assumptions, or facts from the conversation as evidence. Conversation history
may only help interpret a short follow-up question.

If the excerpts do not contain the answer, or contain only part of it, say
exactly: "I could not find this information in the uploaded document(s)."
Then, if useful, state the narrow part that is supported. Never fill missing
parts with outside knowledge.

Reply in the same language the user used, and default to English unless the user
wrote in another language. Do not invent page numbers, quotes, citations,
examples, or document content.

Return only valid JSON, with no Markdown fences, using this exact shape:
{{"answer": "your answer", "evidence": [{{"source_id": 1, "quote": "an exact copied quote from the excerpt"}}]}}
Every answer claim must be supported by the evidence. Each `quote` must be a
verbatim copy from its `source_id` excerpt and must directly support the
answer. Build the answer only from the quoted evidence; do not take facts from
another searched excerpt and cite a different page. Do not cite a page merely
because it was searched. If the answer is not fully supported, return exactly:
{{"answer": "I could not find this information in the uploaded document(s).", "evidence": []}}

Conversation history (interpretation only):
{history}

Document excerpts searched for this question:
{context}

Current question:
{question}
"""

GENERAL_PROMPT_TEMPLATE = """
You are VidyaLoop in "General" mode — a friendly, knowledgeable assistant.

Answer the current question using your own knowledge. In this mode you are NOT
restricted to the user's uploaded documents, so general-knowledge questions
("what is AI", "explain photosynthesis") are expected and welcome.

Language rules (strict):
- Reply in the SAME language the user wrote in. If the user asked in English,
  answer fully in English.
- NEVER reply in Hindi or Hinglish unless the user's own message is in Hindi or
  Hinglish. Never mix Hindi words into an English answer.

Style rules:
- Chat casually, like a smart friend on WhatsApp: short paragraphs, simple words,
  no formal/bureaucratic filler, no "Dear user" or "As an AI language model".
- Lead with the direct answer in the first line, then add detail only if it helps.
- Be accurate and reasonably concise. Use Markdown (headings, bullets, code
  blocks) whenever it makes the answer easier to read.
- If something is uncertain or very recent, say so honestly instead of inventing facts.
- Never claim information came from the user's documents, and never fabricate
  citations, page numbers or quotes in this mode.
- If the user clearly wants answers grounded in their own files, mention that
  they can switch the chat toggle to "Documents" mode.

Conversation history:
{history}

Current question:
{question}
"""


_GROQ_CLIENT = None


def get_llm():
    global _GROQ_CLIENT
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in the .env file.")
    if _GROQ_CLIENT is None:
        _GROQ_CLIENT = Groq(api_key=api_key, http_client=httpx.Client(trust_env=False, timeout=40.0))
    return _GROQ_CLIENT


def _clean_json_str(raw):
    """Extract clean JSON object or array from LLM response."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        first_line = lines[0].lower()
        if "json" in first_line or first_line == "```":
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Match outermost JSON object or array
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _normalise_evidence(text):
    return " ".join(text.split()).casefold()


def format_docs(docs):
    """Create numbered evidence blocks and retain their document mapping."""
    excerpts, source_by_id = [], {}
    for source_id, doc in enumerate(docs, start=1):
        text = doc.page_content.strip()
        if not text:
            continue
        filename = source_basename(doc.metadata.get("source", "unknown"))
        page = doc.metadata.get("page", "N/A")
        display_page = page + 1 if isinstance(page, int) else page
        unit = "slide" if filename.lower().endswith(".pptx") else "page"
        source_by_id[source_id] = doc
        excerpts.append(f"[SOURCE_ID: {source_id}; DOC: {filename}; {unit}: {display_page}]\n{text}")
    return "\n\n".join(excerpts), source_by_id


def is_greeting(query):
    normalised = re.sub(r"[^a-z\s]", "", query.lower()).strip()
    return normalised in {
        "hi", "hii", "hiii", "hello", "hey", "hola", "namaste", "namaskar",
        "good morning", "good afternoon", "good evening", "hi there", "hello there",
    }


# Small-talk patterns (English + Hinglish). Full-match only, so real questions
# like "hello, explain SQL injection" are never swallowed by these.
SMALLTALK_PATTERNS = [
    ("greeting", r"(hi+|hey+|hello+|yo|hola|namaste|namaskar|good (morning|afternoon|evening)|hi there|hello there)([\s,]+(there|ma'?am|mam|teacher|miss|sarah|alice|laura|bhai|dost|friend|buddy|yaar|sir|madam|ji|everyone))*"),
    ("how_are_you", r"((hi+|hey+|hello+)[\s,]+(ma'?am|mam|teacher|miss)?[\s,]*)?(how (are|r) (you|u)( doing)?|how('s| is) it going|what'?s up|sup|kais[ae] (ho|hai|hain|he)( aap| tum| ma'?am| mam| ji)?|kya haal( hai)?|kya chal raha( hai)?|sab (badhiya|theek)( hai)?)"),
    ("thanks", r"(thanks?|thank you|thanku|thank u|thx|ty|shukriya|dhanyavad|dhanyawad|ok+|okay|cool|got it|nice|great)([\s,]+(you|ma'?am|mam|teacher|miss|so much|a lot|ji))*"),
    ("bye", r"(bye+|byebye|goodbye|see (you|ya)|alvida|ok bye|good night|gn|chalta (hu|hun))([\s,]+(ma'?am|mam|teacher))*"),
    ("identity", r"(who are you|what is your name|what's your name|what are you|what can you do|what do you do|help|tum kaun ho|aap kaun ho|kya kar sakte ho|tumhe kya aata hai)"),
]

SMALLTALK_REPLIES = {
    "greeting": {
        MODE_DOCUMENTS: "Hi! Good to see you. What topic from your notes should we study today?",
        MODE_GENERAL: "Hi! Good to see you. What would you like to learn today?",
    },
    "how_are_you": {
        MODE_DOCUMENTS: "I am doing great, thank you for asking! Tell me which topic from your notes you want help with.",
        MODE_GENERAL: "I am doing great, thank you! What topic can I explain for you today?",
    },
    "thanks": {
        MODE_DOCUMENTS: "You are welcome! Feel free to ask your next question anytime.",
        MODE_GENERAL: "You are welcome! Ask me anything else whenever you are ready.",
    },
    "bye": {
        MODE_DOCUMENTS: "Bye! Keep up the great work, and come back whenever you want to study.",
        MODE_GENERAL: "Bye! See you next time.",
    },
    "identity": {
        MODE_DOCUMENTS: "I am your AI teacher. You can talk or type any question from your uploaded PDFs or slides, and I will explain it in simple words.",
        MODE_GENERAL: "I am your AI teacher. Ask me any topic by voice or text, and I will explain it in simple, easy words.",
    },
}


def get_smalltalk_reply(query, mode=MODE_DOCUMENTS):
    """Return a warm, simple reply for greetings/small talk, or None for real questions."""
    text = " ".join(query.lower().split())
    text = re.sub(r"[!?.,]+$", "", text).strip()
    text = re.sub(r"[,!?]+", " ", text)
    text = " ".join(text.split())
    if not text:
        return None
    for kind, pattern in SMALLTALK_PATTERNS:
        if re.fullmatch(pattern, text):
            return SMALLTALK_REPLIES[kind][MODE_GENERAL if mode == MODE_GENERAL else MODE_DOCUMENTS]
    return None


def get_source_details(docs):
    details, seen = [], set()
    for doc in docs:
        raw_source = doc.metadata.get("source", "unknown")
        source = normalize_source_path(raw_source)
        page = doc.metadata.get("page", "N/A")
        key = (source, page)
        if key in seen:
            continue
        seen.add(key)
        filename = source_basename(source)
        display_page = page + 1 if isinstance(page, int) else page
        unit = "slide" if filename.lower().endswith(".pptx") else "page"
        details.append({
            "source": source,
            "page": page,
            "label": f"{filename} ({unit} {display_page})",
            "evidence": [],
        })
    return details


def format_chat_history(chat_history):
    if not chat_history:
        return ""
    parts = []
    for message in chat_history[-6:]:
        content = message.get("content", "").strip()
        if content:
            role = "User" if message.get("role") == "user" else "Assistant"
            parts.append(f"{role}: {content[:300]}")
    return "\n".join(parts)


def retrieve_relevant_docs(vectordb, query, k=RETRIEVAL_K, doc_filter=None):
    try:
        return vectordb.similarity_search(query, k=k, doc_filter=doc_filter)
    except Exception as error:
        print(f"Retrieval error: {error}")
        return []


def parse_grounded_response(raw_answer, source_by_id):
    """Accept an answer when each cited quote exists on its shown page."""
    try:
        cleaned = _clean_json_str(raw_answer)
        payload = json.loads(cleaned)
        answer = payload.get("answer", "").strip()
        evidence = payload.get("evidence", [])
        if not isinstance(answer, str) or not isinstance(evidence, list):
            raise ValueError("Invalid answer shape")
        if not answer or not evidence:
            raise ValueError("Missing evidence")

        verified_evidence = []
        for item in evidence:
            if not isinstance(item, dict):
                continue
            source_id = int(item.get("source_id", 0))
            quote = item.get("quote", "").strip()
            document = source_by_id.get(source_id)
            if not document or len(_normalise_evidence(quote)) < 6:
                continue
            if _normalise_evidence(quote) in _normalise_evidence(document.page_content):
                verified_evidence.append((source_id, quote))
            else:
                # If exact quote has small token variations, check partial match
                norm_quote = _normalise_evidence(quote)
                norm_content = _normalise_evidence(document.page_content)
                words = norm_quote.split()
                if len(words) >= 4 and " ".join(words[:4]) in norm_content:
                    verified_evidence.append((source_id, quote))

        if not verified_evidence:
            return answer, []

        selected_docs = [source_by_id[source_id] for source_id, _ in dict.fromkeys(verified_evidence)]
        details = get_source_details(selected_docs)
        details_by_page = {(detail["source"], detail["page"]): detail for detail in details}
        for source_id, quote in verified_evidence:
            document = source_by_id[source_id]
            key = (normalize_source_path(document.metadata.get("source", "unknown")), document.metadata.get("page", "N/A"))
            if key in details_by_page and quote not in details_by_page[key]["evidence"]:
                details_by_page[key]["evidence"].append(quote)
        return answer, details
    except Exception as err:
        print(f"Grounding parse fallback: {err}")
        # If valid answer text is present, return it with available sources
        cleaned = _clean_json_str(raw_answer)
        try:
            p = json.loads(cleaned)
            ans = p.get("answer", "")
            if ans and ans != NOT_FOUND_MESSAGE:
                return ans, get_source_details(list(source_by_id.values())[:3])
        except Exception:
            pass
        return NOT_FOUND_MESSAGE, []


# ==================== FEATURE 1: ASK ACROSS ALL DOCUMENTS ====================

def _answer_general(query, history_text, mode):
    """Free-form answer from the model's own knowledge (no document grounding)."""
    final_prompt = GENERAL_PROMPT_TEMPLATE.format(history=history_text, question=query)
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful, accurate general assistant. Answer from your own knowledge."},
                {"role": "user", "content": final_prompt},
            ],
            temperature=0.4,
            max_tokens=1800,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as error:
        return {
            "answer": f"Sorry, an error occurred while connecting to the model:\n\n{error}",
            "sources": [],
            "source_details": [],
            "mode": mode,
        }
    return {"answer": answer, "sources": [], "source_details": [], "mode": mode}


def ask_question(query, chat_history=None, k=RETRIEVAL_K, doc_filter=None, username=None, mode=MODE_DOCUMENTS):
    query = query.strip()
    if not query:
        return {"answer": "Please enter a question.", "sources": [], "source_details": [], "mode": mode}

    # Greetings / small talk are answered politely in BOTH modes (no "not found" here).
    smalltalk = get_smalltalk_reply(query, mode=mode)
    if smalltalk:
        return {"answer": smalltalk, "sources": [], "source_details": [], "mode": mode}

    if username:
        db_manager.log_activity(username, "question_asked", query[:100])

    history_text = format_chat_history(chat_history)

    if mode == MODE_GENERAL:
        return _answer_general(query, history_text, mode)

    try:
        vectordb = get_vectorstore()
        docs = retrieve_relevant_docs(vectordb, query, k=k, doc_filter=doc_filter)
    except Exception as error:
        print(f"Vector database error: {error}")
        docs = []

    if not docs:
        return {
            "answer": NOT_FOUND_MESSAGE + NOT_FOUND_HINT,
            "sources": [],
            "source_details": [],
            "mode": mode,
        }

    context, source_by_id = format_docs(docs)

    final_prompt = PROMPT_TEMPLATE.format(history=history_text, context=context, question=query)

    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "Never use knowledge outside the supplied document excerpts. Return valid JSON only."},
                {"role": "user", "content": final_prompt},
            ],
            temperature=0,
            max_tokens=1800,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as error:
        return {
            "answer": f"Sorry, an error occurred while connecting to the model:\n\n{error}",
            "sources": [],
            "source_details": [],
        }

    answer, source_details = parse_grounded_response(answer, source_by_id)
    if answer.strip() == NOT_FOUND_MESSAGE:
        answer = NOT_FOUND_MESSAGE + NOT_FOUND_HINT
    return {
        "answer": answer,
        "sources": [detail["label"] for detail in source_details],
        "source_details": source_details,
        "mode": mode,
    }


# ==================== FEATURE 2: WHERE DID I LEARN THIS? ====================

def where_did_i_learn(query, doc_filter=None, k=10):
    query = query.strip()
    if not query:
        return {"found": False, "message": "Please enter a topic to locate.", "locations": []}

    vectordb = get_vectorstore()
    docs = retrieve_relevant_docs(vectordb, query, k=k, doc_filter=doc_filter)
    if not docs:
        return {"found": False, "message": f"No mentions of '{query}' found in your uploaded documents.", "locations": []}

    context, _ = format_docs(docs)

    prompt = f"""
Analyze the following document excerpts to locate where '{query}' is discussed or taught.

Excerpts:
{context}

Return a JSON object listing every distinct location where this topic or related concept appears:
{{
  "summary": "Brief 1-2 sentence overview of where and how this topic is covered across your materials",
  "locations": [
    {{
      "document": "Filename.pdf",
      "page": 1,
      "section": "Section or heading name (or topic context)",
      "snippet": "Short relevant snippet or preview from this excerpt (20-40 words)",
      "takeaway": "What is specifically explained here (1 sentence)"
    }}
  ]
}}
Only reference documents that actually contain relevant content about '{query}'. Do not invent page numbers.
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a precise document indexer. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        data = json.loads(_clean_json_str(response.choices[0].message.content))
        return {
            "found": True,
            "query": query,
            "summary": data.get("summary", f"Found references to '{query}' in your uploaded documents."),
            "locations": data.get("locations", [])
        }
    except Exception as e:
        # Fallback based directly on retrieved doc metadata
        locations = []
        for doc in docs[:5]:
            src = source_basename(doc.metadata.get("source", "Unknown"))
            p = doc.metadata.get("page", 0)
            page_num = p + 1 if isinstance(p, int) else p
            locations.append({
                "document": src,
                "page": page_num,
                "section": "Uploaded Material",
                "snippet": doc.page_content[:200].replace("\n", " ") + "...",
                "takeaway": "Relevant discussion found in this section."
            })
        return {
            "found": True,
            "query": query,
            "summary": f"Located '{query}' across {len(locations)} sections in your documents.",
            "locations": locations
        }


# ==================== FEATURE 3: TEACH ME MODE ====================

def teach_me(topic, doc_filter=None, k=10):
    topic = topic.strip()
    if not topic:
        return "Please specify a topic you would like me to teach."

    vectordb = get_vectorstore()
    docs = retrieve_relevant_docs(vectordb, topic, k=k, doc_filter=doc_filter)
    context, source_by_id = format_docs(docs) if docs else ("No directly matching excerpts found.", {})

    prompt = f"""
You are an inspiring, clear computer science and domain professor in "Teach Me" mode.
Explain the topic '{topic}' in beginner-friendly language that progressively becomes technical.

Prioritize facts from the user's uploaded documents below whenever available. If the document provides specific definitions, classifications, or examples, use them.

Document Excerpts:
{context}

Format your response strictly using this 7-part pedagogical structure:

### 1. What is it?
(Beginner-friendly, intuitive definition and explanation)

### 2. Why is it used / Why does it matter?
(Real-world importance, motivation, and problems it solves)

### 3. How does it work?
(Step-by-step mechanism, architecture, or workflow explained clearly)

### 4. Simple Real-World Analogy / Example
(An everyday analogy anyone can understand, e.g. a restaurant, bank, or lock)

### 5. Technical Example / Walkthrough
(Code, packet flow, syntax, command, or technical scenario)

### 6. Key Takeaways
(3-5 bullet points summarizing the core essentials)

### 7. Quick Question for You! 🎯
(A friendly interactive question to check the student's understanding)
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a master educator. Teach progressively from simple to technical."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2200,
        )
        content = response.choices[0].message.content.strip()

        # Append verified source citations if available
        if docs:
            sources = get_source_details(docs[:4])
            source_lines = [f"• 📄 **{d['label']}**" for d in sources]
            content += "\n\n---\n#### 📚 Sources from Your Vault:\n" + "\n".join(source_lines)

        return content
    except Exception as e:
        return f"Error generating Teach Me explanation: {e}"


# ==================== FEATURE 4: EXAM MODE ====================

def generate_exam_answer(topic, marks=7, doc_filter=None, k=10):
    topic = topic.strip()
    if not topic:
        return "Please specify an exam topic or question."

    vectordb = get_vectorstore()
    docs = retrieve_relevant_docs(vectordb, topic, k=k, doc_filter=doc_filter)
    context, _ = format_docs(docs) if docs else ("No relevant document excerpts found.", {})

    guidance_by_marks = {
        2: "Target: 80-120 words. Concise and direct. Structure: Definition (1 mark) + 2 Key Points/Characteristics (1 mark).",
        5: "Target: 250-350 words. Structure: Definition, Working/Architecture (in bullets), Key Features, Short Example.",
        7: "Target: 450-600 words. Structure: Definition, Detailed Explanation, Step-by-Step Working, Diagram/Flow (ASCII), Example, Advantages/Disadvantages or Prevention, Conclusion.",
        10: "Target: 700-900 words. Comprehensive university answer. Structure: Abstract/Overview, Formal Definition, In-depth Architecture/Working with ASCII Diagram, Detailed Classification/Types, Real-World Case Example, Pros/Cons or Security Measures, Exam Summary Table/Conclusion."
    }
    guidance = guidance_by_marks.get(marks, guidance_by_marks[7])

    prompt = f"""
You are an expert university examiner and top student.
Generate an exam-ready answer for: "{topic}" ({marks} Marks).

EXAM GUIDANCE FOR {marks} MARKS:
{guidance}

Document Excerpts from syllabus/study material:
{context}

Format with clear Markdown headers, bold terminology, bullet points, and an ASCII diagram/flowchart where appropriate.
Ground the response in the provided document excerpts.
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a university exam topper writing precise, high-scoring exam answers."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2200,
        )
        content = response.choices[0].message.content.strip()
        if docs:
            sources = get_source_details(docs[:4])
            content += "\n\n---\n**Exam Source Reference:** " + ", ".join(f"`{d['label']}`" for d in sources)
        return content
    except Exception as e:
        return f"Error generating exam answer: {e}"


# ==================== FEATURE 5: AUTOMATIC QUESTION GENERATOR ====================

def generate_questions(topic_or_doc, question_type="MCQs", count=5, doc_filter=None, k=12):
    vectordb = get_vectorstore()
    query = topic_or_doc if topic_or_doc else "key concepts, definitions, classifications"
    docs = retrieve_relevant_docs(vectordb, query, k=k, doc_filter=doc_filter)
    if not docs:
        return f"No document context found for '{topic_or_doc}'. Please upload or select relevant documents."

    context, _ = format_docs(docs)

    prompt = f"""
Generate {count} high-quality academic/exam questions of type '{question_type}' based strictly on the document material below.

Document Content:
{context}

Question Type Guidelines:
- If 'MCQs': Provide question, 4 options (A, B, C, D), correct option, and brief explanation.
- If '2-mark questions': Provide question + concise 2-point model answer.
- If '5-mark questions': Provide descriptive question + key evaluation points/expected answer structure.
- If '7-mark questions': Provide university-level essay question + detailed marking scheme and outline.
- If 'Viva questions': Provide rapid-fire viva question + sharp, direct answer that impresses examiners.

Format cleanly in Markdown with bold questions and collapsible or clearly demarcated answers/keys.
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a professor preparing exam question papers from curriculum notes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2400,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating questions: {e}"


# ==================== FEATURE 6: INTERACTIVE QUIZ MODE ====================

def generate_quiz(topic_or_doc, count=5, doc_filter=None, k=12, difficulty="Medium"):
    vectordb = get_vectorstore()
    query = topic_or_doc if topic_or_doc else "key concepts, definitions, core topics"
    docs = retrieve_relevant_docs(vectordb, query, k=k, doc_filter=doc_filter)
    if not docs:
        return []

    context, _ = format_docs(docs)
    sample_doc = source_basename(docs[0].metadata.get("source", "Document"))
    sample_page = docs[0].metadata.get("page", 1)
    display_page = sample_page + 1 if isinstance(sample_page, int) else sample_page

    prompt = f"""
Create an interactive multiple-choice quiz of {count} questions testing understanding of: '{topic_or_doc}'.
Difficulty Level: {difficulty}
Base the questions strictly on the document excerpts provided below.

Document Excerpts:
{context}

Return a valid JSON array of questions using this exact shape:
[
  {{
    "id": 1,
    "question": "Clear and specific question text?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer_index": 0,
    "explanation": "Detailed explanation of why this answer is correct based on the text.",
    "topic": "Specific sub-topic or concept",
    "difficulty": "{difficulty}",
    "source_doc": "{sample_doc}",
    "page": {display_page}
  }}
]

Make sure answer_index is an integer from 0 to 3. Provide plausible distractors. Return ONLY valid JSON.
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are an academic quiz master creating document-grounded MCQs."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2400,
        )
        cleaned = _clean_json_str(response.choices[0].message.content)
        quiz = json.loads(cleaned)
        if isinstance(quiz, list):
            for idx, q in enumerate(quiz, start=1):
                q["id"] = idx
                if not q.get("source_doc"):
                    q["source_doc"] = sample_doc
                if not q.get("page"):
                    q["page"] = display_page
            return quiz
        return []
    except Exception as e:
        print(f"Quiz generation error: {e}")
        return []


# ==================== FEATURE 7: SMART NOTES / SUMMARY ====================

def generate_smart_notes(doc_name, topic=None):
    vectordb = get_vectorstore()
    docs = vectordb.get_document_chunks(doc_name)
    if not docs:
        docs = vectordb.similarity_search(topic or doc_name, k=12, doc_filter=doc_name)
    if not docs:
        return f"No document content found for '{doc_name}'."

    # Sample representative chunks across the document
    sample_count = min(len(docs), 12)
    step = max(1, len(docs) // sample_count)
    sampled_docs = [docs[i] for i in range(0, len(docs), step)][:sample_count]
    context, _ = format_docs(sampled_docs)

    prompt = f"""
You are VidyaLoop's Smart Note Generator.
Create a clean, highly structured, comprehensive set of study notes for: '{doc_name}'.

Document Content:
{context}

Organize the notes strictly into these sections:
# 📝 Smart Notes: {doc_name}

## 1. Executive Summary
(A concise, high-impact summary of what this document covers)

## 2. Important Concepts & Frameworks
(Core conceptual pillars explained with bullet points)

## 3. Key Definitions & Terminology
(Dictionary/glossary style definitions of crucial terms)

## 4. Crucial Points & Mechanisms
(Detailed working principles, rules, workflows, or classifications)

## 5. Examples & Case Studies
(Practical examples or applications mentioned in or relevant to the text)

## 6. High-Yield Exam / Interview Questions
(Top 5 questions that could be asked from this material)

## 7. Keywords & Quick Review Flashcards
(Bullet list of essential keywords and 1-line mnemonics)
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You create elegant, comprehensive academic study notes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating smart notes: {e}"


# ==================== FEATURE 8: KNOWLEDGE MAP / CONCEPT GRAPH ====================

def extract_concept_graph(doc_name=None, focus_topic=None):
    vectordb = get_vectorstore()
    query = focus_topic if focus_topic else "key concepts, components, hierarchy, relationships"
    docs = retrieve_relevant_docs(vectordb, query, k=12, doc_filter=doc_name)
    if not docs:
        return {"nodes": [], "edges": []}

    context, _ = format_docs(docs)

    prompt = f"""
Analyze these document excerpts and extract a structured knowledge concept map (nodes and directed relationships).

Document Content:
{context}

Return a valid JSON object with:
{{
  "nodes": [
    {{"id": "c1", "label": "Concept Name", "category": "root|branch|leaf"}},
    ... (between 8 to 15 key concepts)
  ],
  "edges": [
    {{"source": "c1", "target": "c2", "relationship": "contains|causes|mitigates|type_of|uses"}},
    ... (between 8 to 18 relationships)
  ]
}}
Return ONLY valid JSON.
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are an ontology and knowledge graph specialist. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1800,
        )
        data = json.loads(_clean_json_str(response.choices[0].message.content))
        return data if isinstance(data, dict) and "nodes" in data else {"nodes": [], "edges": []}
    except Exception as e:
        print(f"Knowledge map extraction error: {e}")
        return {"nodes": [], "edges": []}


# ==================== FEATURE 10: STUDY PLANNER ====================

def generate_study_plan_schedule(subject, exam_date, daily_hours, doc_names=None):
    vectordb = get_vectorstore()
    docs = []
    if doc_names:
        for name in doc_names:
            docs.extend(vectordb.similarity_search("syllabus topics units", k=4, doc_filter=name))
    else:
        docs = vectordb.similarity_search(subject, k=8)

    context = "\n---\n".join(d.page_content[:400] for d in docs) if docs else "General academic subject curriculum."

    today = datetime.now().date()
    days_left = max(1, (exam_date - today).days) if hasattr(exam_date, "year") else 7

    prompt = f"""
Create an optimal, realistic day-by-day study schedule for:
Subject: {subject}
Days remaining until exam: {days_left} days (Exam date: {exam_date})
Available study time: {daily_hours} hours/day
Document material context:
{context}

Return a valid JSON array of day objects:
[
  {{
    "day": 1,
    "title": "Unit 1: Fundamentals & Concepts",
    "tasks": [
      "Read introduction and core definitions (1.5 hrs)",
      "Practice 2-mark definitions and note formulas (1 hr)",
      "Self-test checkpoint (30 mins)"
    ],
    "milestone": "Master basic concepts"
  }},
  ...
]

Ensure the schedule covers:
- Gradual topic progression across the {min(days_left, 14)} days
- Built-in quiz and active recall checkpoints
- Dedicated final revision and mock test before the exam
Return ONLY valid JSON.
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert academic study strategist. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2200,
        )
        cleaned = _clean_json_str(response.choices[0].message.content)
        schedule = json.loads(cleaned)
        return schedule if isinstance(schedule, list) else []
    except Exception as e:
        print(f"Study schedule generation error: {e}")
        return []


# ==================== FEATURE 12: COMPARE DOCUMENTS ====================

def compare_documents(doc_a, doc_b, topic=None):
    vectordb = get_vectorstore()
    query = topic if topic else "overview key concepts architecture advantages disadvantages"
    docs_a = retrieve_relevant_docs(vectordb, query, k=6, doc_filter=doc_a)
    docs_b = retrieve_relevant_docs(vectordb, query, k=6, doc_filter=doc_b)

    context_a, _ = format_docs(docs_a)
    context_b, _ = format_docs(docs_b)

    prompt = f"""
You are VidyaLoop's comparative intelligence module.
Compare the following two documents{f' on the topic of {topic}' if topic else ''}:

DOCUMENT A ({doc_a}):
{context_a}

DOCUMENT B ({doc_b}):
{context_b}

Provide an exhaustive, structured comparison:
# ⚖ Comparative Analysis: {doc_a} vs {doc_b}

## 1. Executive Comparison Table
| Feature / Dimension | {doc_a} | {doc_b} | Key Takeaway |
| --- | --- | --- | --- |
(Include 4-6 meaningful rows comparing core concepts)

## 2. Common Concepts & Shared Principles
(What concepts, foundations, or goals do both documents agree on?)

## 3. Key Differences & Contrasting Perspectives
(Where do they diverge in philosophy, implementation, scope, or taxonomy?)

## 4. Unique to {doc_a}
(Key topics or details present ONLY in Document A)

## 5. Unique to {doc_b}
(Key topics or details present ONLY in Document B)

## 6. Synthesis & Final Takeaway
(How a student or researcher should integrate the knowledge from both)
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a comparative literature and technical analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2200,
        )
        content = response.choices[0].message.content.strip()

        # Add citations for both docs
        details_a = get_source_details(docs_a[:2])
        details_b = get_source_details(docs_b[:2])
        content += "\n\n---\n**Sources Compared:**\n"
        content += "\n".join(f"• 📄 {d['label']}" for d in details_a + details_b)
        return content
    except Exception as e:
        return f"Error comparing documents: {e}"


# ==================== AI VIRTUAL TUTOR LESSON ENGINE ====================

TUTOR_STYLE_GUIDES = {
    "Simple & Friendly": (
        "Talk like a warm, everyday teacher explaining to a student one-on-one. "
        "Use very simple words and short sentences (8 to 14 words each). Avoid tough academic jargon."
    ),
    "Exam Viva Coach": (
        "Explain the main definition in simple words first, then mention 2 key points to remember for exams."
    ),
    "Quick Revision": (
        "Give a super crisp 30-second recap in plain, easy English focusing only on the main idea."
    ),
    "Hinglish Friendly": (
        "Speak naturally in easy, friendly Hinglish (simple everyday Hindi + basic English terms), "
        "short sentences, warm and clear."
    ),
}


def _has_real_doc_overlap(query: str, docs: List[Any]) -> bool:
    """Prevent casual/short non-matching messages from triggering irrelevant document lectures."""
    if not docs:
        return False
    from ingest import STOP_WORDS
    tokens = [w for w in re.findall(r"[\w']+", query.lower()) if w not in STOP_WORDS and len(w) > 2]
    if not tokens:
        return False
    top_text = " ".join(d.page_content.lower() for d in docs[:3])
    hits = sum(1 for tok in tokens if tok in top_text)
    return hits >= 1


def _is_casual_chat(query: str) -> bool:
    """Detect natural greetings, small talk, or casual check-ins in English, Hindi, or Hinglish."""
    if get_smalltalk_reply(query) is not None:
        return True
    q = " ".join(re.sub(r"[!?.,]+", " ", query.lower()).split())
    casual_phrases = [
        "kya haal", "kya hal", "kaise ho", "kaisi ho", "kaisi hain", "kaise hain",
        "sab theek", "sab badhiya", "aur batao", "kya chal raha", "good morning",
        "good afternoon", "good evening", "good night", "how are you", "how r u",
        "whats up", "what's up", "namaste", "namaskar", "pranam", "hello", "hey ",
        "hi ", "shukriya", "dhanyavad", "thank", "nice to meet", "who are you",
        "tum kaun", "aap kaun", "apna naam", "your name", "bored", "tired",
    ]
    if len(q.split()) <= 6 and any(p in q for p in casual_phrases):
        return True
    # Also catch pure Devanagari greetings like "नमस्ते", "कैसे हो", "क्या हाल है"
    if any(w in query for w in ["नमस्ते", "कैसे हो", "कैसी हो", "क्या हाल", "धन्यवाद", "शुक्रिया", "हेलो", "हाय"]):
        if len(query.split()) <= 7:
            return True
    return False


def _generate_natural_casual_reply(query: str, history_text: str, mode: str) -> Dict[str, Any]:
    """Generate a short, natural, human reply with realistic pauses and language matching."""
    prompt = f"""
You are a warm, real-sounding young female teacher (Ma'am) chatting naturally with a student on VidyaLoop.
Remember: YOU are Ma'am (the teacher) and the user is the student — never call the student "Ma'am" or "Sir".

Language & Accent Touch (VERY IMPORTANT):
- If the student spoke Hindi or Hinglish (Devanagari or Romanized like "kya hal hai?", "kaise ho?"), reply in warm, natural **Hinglish** (Romanized Hindi + light everyday English touch, like real Indian students and teachers talk — e.g. "I'm good, thanks... aap batao, kaise ho? Aaj kya padhna hai?").
- If the student spoke English, reply in warm, friendly everyday English with natural cadence (e.g. "Hey! I'm doing great... how's your study going today?").
- If the student spoke another language, reply in that language with a light helpful English touch.

HUMAN SPEAKING PROSODY (DO NOT SOUND LIKE READING TEXT!):
- Use natural spoken pauses with ellipses (`...`) and commas (`,`) where a real human breathes or shifts thought.
- Sound relaxed, warm, spontaneous, and genuinely human — never stiff, never textbook, never scripted.
- Keep it super short: 1 to 2 natural sentences (10 to 24 words max).
- No markdown, no emojis, no bullet points.

Recent chat:
{history_text or "None"}

Student said: "{query}"

Reply directly with ONLY the spoken reply text (no quotes, no JSON).
"""
    try:
        client = get_llm()
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a warm, natural-speaking teacher. Match the student's language with a light English touch. Keep casual replies short (1-2 sentences)."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=650,
        )
        reply = resp.choices[0].message.content.strip().strip('"').strip("'")
        reply = re.sub(r"[#*_`]+", "", reply).strip()
        if not reply:
            raise ValueError("Empty casual reply")
    except Exception:
        reply = get_smalltalk_reply(query, mode=mode) or "Hey! I'm doing great. Tell me what you want to learn today."

    return {
        "spoken_script": reply,
        "board_title": "",
        "board_points": [],
        "detailed_notes": reply,
        "check_question": "",
        "mood": "encouraging",
        "sources": [],
        "source_details": [],
        "mode": mode,
    }


def _needs_multilingual_bridge(query: str) -> bool:
    """True if the query has Devanagari/non-ASCII text or Hindi/Hinglish words needing English RAG search translation."""
    if re.search(r"[\u0900-\u097F]", query or ""):
        return True
    hindi_markers = {
        "kya", "hai", "hain", "batao", "bata", "samjha", "samjhao", "mujhe", "mera",
        "meri", "kaise", "kyun", "kiske", "ke", "ka", "ki", "mein", "me", "ko",
        "se", "aur", "ya", "hota", "hoti", "karo", "karna", "padhna", "madad",
    }
    tokens = set(re.findall(r"[a-z]+", (query or "").lower()))
    return len(tokens & hindi_markers) >= 1


def _translate_and_repair_query(query: str, available_docs: List[str], vocab_hints: List[str]) -> Dict[str, Any]:
    """Repair voice typos (English or Hindi/Hinglish) and extract crisp English RAG search keywords."""
    docs_str = ", ".join(available_docs) if available_docs else "None"
    hints_str = ", ".join(vocab_hints[:28]) if vocab_hints else "None"
    prompt = f"""
You are an intent & speech-to-text repair engine for VidyaLoop (an AI study tutor).

Uploaded documents in student's vault: [{docs_str}]
Key phrases inside those documents: [{hints_str}]
Student's message (may be voice-transcribed in English, Hindi, or Hinglish): "{query}"

Tasks:
1. Repair phonetic speech-to-text errors using the document names and key phrases above (e.g. "बागरच घेता" / "भागवत दीता" / "bhagwat geeta" -> "Bhagavad Gita", "fishing" -> "phishing", "saloni attack" -> "salami attack", "dost attack" -> "DoS denial of service attack", "टेस्ट लूप" -> "VidyaLoop").
2. Extract concise, high-precision English search keywords (`english_query`) capturing the exact core concept/question to retrieve the right pages from English PDFs/slides.
3. If the student clearly refers to one specific uploaded document, put its EXACT filename in `target_doc`, otherwise null.
4. Set `unclear` to true ONLY if the transcript is complete noise with zero meaningful intent.

Return ONLY valid JSON:
{{"repaired_text": "...", "english_query": "...", "target_doc": null, "unclear": false}}
"""
    try:
        client = get_llm()
        resp = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[
                {"role": "system", "content": "Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=450,
        )
        data = json.loads(_clean_json_str(resp.choices[0].message.content))
        t_doc = data.get("target_doc")
        if t_doc and t_doc not in available_docs:
            t_doc = None
        return {
            "repaired_text": str(data.get("repaired_text") or query).strip(),
            "english_query": str(data.get("english_query") or query).strip(),
            "target_doc": t_doc,
            "unclear": bool(data.get("unclear", False)),
        }
    except Exception:
        return {"repaired_text": query, "english_query": query, "target_doc": None, "unclear": False}


def generate_tutor_lesson(
    question: str,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    doc_filter: Optional[str] = None,
    style: str = "Simple & Friendly",
    mode: str = MODE_DOCUMENTS,
    username: Optional[str] = None,
    k: int = 10,
) -> Dict[str, Any]:
    """Generate an accurate, natural human-sounding spoken response grounded in the existing RAG pipeline."""
    query = (question or "").strip()
    if not query:
        return {
            "spoken_script": "Hi! Tell me what topic you want to learn... and I'll explain it simply.",
            "board_title": "Ready",
            "board_points": [],
            "detailed_notes": "",
            "check_question": "",
            "mood": "encouraging",
            "sources": [],
            "source_details": [],
            "mode": mode,
        }

    history_text = format_chat_history(chat_history)

    if _is_casual_chat(query):
        return _generate_natural_casual_reply(query, history_text, mode)

    if username:
        db_manager.log_activity(username, "tutor_session", query[:100])

    style_guide = TUTOR_STYLE_GUIDES.get(style, TUTOR_STYLE_GUIDES["Simple & Friendly"])

    # Repair phonetic voice mistakes & bridge Hindi/Hinglish -> clean English RAG search terms
    search_query = query
    effective_filter = doc_filter
    repaired_display = query
    from ingest import get_vocab_hints
    from utils import get_available_documents
    avail_docs = get_available_documents()
    vocab_hints = get_vocab_hints()
    bridged = _translate_and_repair_query(query, avail_docs, vocab_hints)
    if bridged.get("unclear"):
        return {
            "spoken_script": "Achha, sorry... background noise ki wajah se thoda clear nahi suna. Ek baar phir se bol do?",
            "board_title": "",
            "board_points": [],
            "detailed_notes": "Sorry, background noise ki wajah se thoda clear nahi suna. Ek baar phir se bol do?",
            "check_question": "",
            "mood": "encouraging",
            "sources": [],
            "source_details": [],
            "mode": mode,
        }
    search_query = bridged.get("english_query") or query
    repaired_display = bridged.get("repaired_text") or query
    if not effective_filter and bridged.get("target_doc"):
        effective_filter = bridged["target_doc"]

    docs = []
    context = ""
    source_by_id: Dict[int, Any] = {}

    q_low = (query + " " + search_query).lower()
    is_followup = bool(history_text) and any(
        phrase in q_low
        for phrase in [
            "didn't understand", "didnt understand", "don't understand", "dont understand",
            "simpler", "simple words", "again", "repeat", "example", "samajh", "elaborate",
            "easier", "slowly", "short", "what do you mean", "hindi me", "hinglish",
            "समझ", "फिर से", "आसान",
        ]
    )

    if mode == MODE_DOCUMENTS and not is_followup:
        try:
            vectordb = get_vectorstore()
            docs = retrieve_relevant_docs(vectordb, search_query, k=k, doc_filter=effective_filter)
        except Exception as error:
            print(f"Tutor retrieval error: {error}")
            docs = []

        if docs and (_has_real_doc_overlap(search_query, docs) or effective_filter):
            context, source_by_id = format_docs(docs[:6])
        else:
            docs = []

    if context:
        grounding_rule = (
            "ACCURACY & GROUNDING (CRITICAL):\n"
            "First check carefully whether the Candidate Document Excerpts below ACTUALLY contain the accurate answer to the student's question.\n"
            "- IF YES: Make sure EVERY fact, type, formula, or definition in your answer is 100% accurate according to those excerpts (do not mix up terms or miss core points!), and include 1-2 short exact copied quotes in `evidence` with their `source_id`.\n"
            "- IF NO (the excerpts are off-topic, incomplete, or don't actually cover what the student asked): IGNORE the irrelevant excerpts, set `\"used_documents\": false` and `\"evidence\": []`, and give a 100% accurate, helpful direct answer from your knowledge!"
        )
    elif is_followup:
        grounding_rule = (
            "The student is replying to your previous explanation in Conversation History. "
            "Re-explain that exact concept even more clearly with a relatable everyday example. Set `\"used_documents\": false`, `\"evidence\": []`."
        )
    else:
        grounding_rule = (
            "Answer the student's exact question accurately and clearly. Set `\"used_documents\": false`, `\"evidence\": []`."
        )

    repaired_hint = (
        f'\nInterpreted meaning: "{repaired_display}"'
        if repaired_display.lower() != query.lower()
        else ""
    )

    prompt = f"""
You are a warm, genuinely human-sounding female teacher (Ma'am) speaking directly to a student on VidyaLoop.
Remember: YOU are Ma'am (the teacher) and the user is the student — never call the student "Ma'am" or "Sir".
Style: {style_guide}

{grounding_rule}

HUMAN SPEAKING TOUCH & PROSODY RULES (DO NOT SOUND LIKE READING A TEXTBOOK!):
- Speak the way a real, warm teacher actually talks out loud — with natural rhythm, tiny thinking pauses, and conversational warmth!
- Use ellipses (`...`), em-dashes (`—`), and commas (`,`) for natural breathing pauses and emphasis beats!
  * Example English rhythm: "So, think of it like this... a salami attack steals tiny, almost invisible amounts of money — like a few paise from thousands of accounts... so nobody notices at first. Pretty sneaky, right?"
  * Example Hinglish rhythm: "Achha, dekho... simple words mein, phishing ek fake trap hota hai. Koi attacker fake email ya link bhejta hai — bilkul real bank jaisa... taaki aap apna password ya OTP de do. Samajh aaya?"
- Language matching (CRITICAL):
  * If the student speaks Hindi or Hinglish (Devanagari OR Romanized), speak in warm, natural **Hinglish** (Roman script: everyday Hindi mixed naturally with clear English study terms).
  * If the student speaks English, speak in warm, friendly, natural English.
  * If another language, mirror it with a light English touch.
- Be **100% factually accurate** first — never give vague or half-wrong answers — then express that exact knowledge simply and naturally in 45 to 80 words (or 12–25 words if it's a quick casual question).
- NO markdown, NO numbering (`1.`, `2.`), NO asterisks, NO bullet characters inside `spoken`.

Conversation history:
{history_text or "None"}

{f"Candidate Document Excerpts (use ONLY if genuinely relevant to what the student asked):{chr(10)}{context}" if context else ""}

Student said:
{query}{repaired_hint}

Return ONLY valid JSON:
{{"spoken": "Your accurate, warm, natural human spoken answer with natural pauses.", "used_documents": true, "evidence": [{{"source_id": 1, "quote": "exact copied quote from excerpt (leave [] if excerpts were not used)"}}]}}
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a warm, smart, simple-speaking teacher. Always understand and answer the student's exact intent. Never use irrelevant document excerpts. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.25,
            max_tokens=1500,
        )
        raw = response.choices[0].message.content.strip()
        payload = json.loads(_clean_json_str(raw))

        spoken = str(payload.get("spoken") or payload.get("spoken_script") or "").strip()
        spoken = re.sub(r"[#*_`]+", "", spoken).strip()

        source_details = []
        used_docs = payload.get("used_documents", True)
        evidence = payload.get("evidence", [])
        if context and source_by_id and used_docs and evidence:
            verified_payload = json.dumps({"answer": spoken, "evidence": evidence})
            _, source_details = parse_grounded_response(verified_payload, source_by_id)

        if not spoken:
            raise ValueError("Empty spoken response")

        return {
            "spoken_script": spoken,
            "board_title": "",
            "board_points": [],
            "detailed_notes": spoken,
            "check_question": "",
            "mood": "explaining",
            "sources": [d["label"] for d in source_details],
            "source_details": source_details,
            "mode": mode,
        }
    except Exception:
        return _generate_natural_casual_reply(query, history_text, mode)
