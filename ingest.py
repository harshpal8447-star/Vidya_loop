import hashlib
import io
import json
import math
import os
import re
import shutil
import tempfile


class Document:
    """Lightweight document container (avoids heavy langchain_core cold import)."""

    __slots__ = ("page_content", "metadata")

    def __init__(self, page_content="", metadata=None):
        self.page_content = page_content
        self.metadata = metadata if metadata is not None else {}


DB_DIR = "db"
UPLOAD_DIR = "uploads"
INDEX_FILE = os.path.join(DB_DIR, "second_brain_index.json")

_WIN_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
_INDEX_CACHE = {"mtime": None, "records": [], "bm25": None}


def _tokenize_words(text):
    """Extract lowercase word tokens (length >= 2) for exact-word BM25 matching."""
    return [w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) >= 2]


def _build_bm25_stats(records):
    """Precompute per-record token frequencies and corpus IDF once per index load (<50ms)."""
    n_docs = len(records)
    if n_docs == 0:
        return {"df": {}, "idf": {}, "tf_list": [], "doc_lens": [], "avg_len": 1.0, "vocab_hints": []}

    df = {}
    tf_list = []
    doc_lens = []
    bigram_counts = {}

    for rec in records:
        tokens = _tokenize_words(rec.get("text", ""))
        doc_lens.append(len(tokens))
        tf = {}
        for tok in tokens:
            tf[tok] = tf.get(tok, 0) + 1
        tf_list.append(tf)
        for tok in tf:
            df[tok] = df.get(tok, 0) + 1
        # Track distinctive non-stopword bigrams for phonetic repair hints
        for i in range(len(tokens) - 1):
            a, b = tokens[i], tokens[i + 1]
            if len(a) > 3 and len(b) > 3 and a not in STOP_WORDS and b not in STOP_WORDS:
                bg = f"{a} {b}"
                bigram_counts[bg] = bigram_counts.get(bg, 0) + 1

    idf = {tok: math.log((n_docs + 1.0) / (freq + 1.0)) + 1.0 for tok, freq in df.items()}
    avg_len = sum(doc_lens) / max(1, n_docs)

    # Top domain phrases across uploaded documents (helpful hints for ASR typo correction)
    top_bigrams = [bg for bg, cnt in sorted(bigram_counts.items(), key=lambda x: x[1], reverse=True) if cnt >= 2][:40]
    return {
        "df": df,
        "idf": idf,
        "tf_list": tf_list,
        "doc_lens": doc_lens,
        "avg_len": avg_len,
        "vocab_hints": top_bigrams,
    }


def get_vocab_hints():
    """Return top recurring domain phrases from indexed docs for voice typo repair."""
    _load_index()
    bm25 = _INDEX_CACHE.get("bm25") or {}
    return bm25.get("vocab_hints", [])


def normalize_source_path(file_path):
    """Normalize stored paths with POSIX slashes so Windows & Linux match."""
    return str(file_path or "").replace("\\", "/")


def source_basename(file_path):
    """Extract filename across both Windows and POSIX separators."""
    return os.path.basename(normalize_source_path(file_path))


class LocalHashEmbeddings:
    """Fast local keyword embeddings with no server or model dependency."""

    dimensions = 384

    def _embed(self, text):
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[\w']+", text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0 if digest[4] % 2 else -1.0
        magnitude = math.sqrt(sum(value * value for value in vector))
        return [value / magnitude for value in vector] if magnitude else vector

    def embed_documents(self, texts):
        return [self._embed(text) for text in texts]

    def embed_query(self, text):
        return self._embed(text)


def load_pdf_with_ocr(file_path):
    import fitz
    import pytesseract
    from PIL import Image

    if os.name == "nt" and os.path.exists(_WIN_TESSERACT):
        pytesseract.pytesseract.tesseract_cmd = _WIN_TESSERACT
    elif shutil.which("tesseract"):
        pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")

    try:
        pdf = fitz.open(file_path)
    except Exception as error:
        raise ValueError(f"Could not open PDF file: {error}") from error

    documents = []
    for page_number, page in enumerate(pdf):
        try:
            text = page.get_text().strip()
            if not text:
                pixmap = page.get_pixmap(dpi=180)
                text = pytesseract.image_to_string(Image.open(io.BytesIO(pixmap.tobytes("png"))))
            if text.strip():
                documents.append(Document(page_content=text, metadata={"source": normalize_source_path(file_path), "page": page_number}))
        except Exception:
            continue
    pdf.close()
    if not documents:
        raise ValueError("No readable text could be extracted from this PDF.")
    return documents


def load_pptx(file_path):
    """Extract slide text, tables, and speaker notes with 0-based slide indices."""
    try:
        from pptx import Presentation
    except ImportError as error:
        raise ValueError("python-pptx is required to process .pptx files.") from error

    try:
        prs = Presentation(file_path)
    except Exception as error:
        raise ValueError(f"Could not open PowerPoint file: {error}") from error

    documents = []
    norm_source = normalize_source_path(file_path)
    for slide_idx, slide in enumerate(prs.slides):
        parts = []
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False) and shape.text_frame:
                text = shape.text_frame.text.strip()
                if text:
                    parts.append(text)
            if getattr(shape, "has_table", False) and shape.table:
                for row in shape.table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text and cell.text.strip()]
                    if cells:
                        parts.append(" | ".join(cells))
        try:
            if slide.has_notes_slide and slide.notes_slide and slide.notes_slide.notes_text_frame:
                notes = slide.notes_slide.notes_text_frame.text.strip()
                if notes:
                    parts.append(f"Speaker Notes: {notes}")
        except Exception:
            pass

        slide_text = "\n".join(parts).strip()
        if slide_text:
            documents.append(
                Document(
                    page_content=slide_text,
                    metadata={"source": norm_source, "page": slide_idx, "file_type": "pptx"},
                )
            )

    if not documents:
        raise ValueError("No readable text could be extracted from this PowerPoint deck.")
    return documents


def load_file(file_path):
    extension = os.path.splitext(file_path)[1].lower()
    if extension == ".pdf":
        return load_pdf_with_ocr(file_path)
    if extension == ".pptx":
        return load_pptx(file_path)
    if extension == ".docx":
        from langchain_community.document_loaders import Docx2txtLoader
        return Docx2txtLoader(file_path).load()
    if extension == ".txt":
        from langchain_community.document_loaders import TextLoader
        return TextLoader(file_path, encoding="utf-8").load()
    raise ValueError(f"Unsupported file type: {file_path}")


def chunk_documents(documents, chunk_size=1000, chunk_overlap=150):
    from langchain_core.documents import Document as LCDocument
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    lc_docs = [
        d if isinstance(d, LCDocument) else LCDocument(page_content=d.page_content, metadata=d.metadata)
        for d in documents
    ]
    split = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap).split_documents(lc_docs)
    return [Document(page_content=d.page_content, metadata=dict(d.metadata)) for d in split]


def _emit_progress(callback, stage, percentage):
    if callback:
        callback(stage, percentage)


def _load_index():
    if not os.path.exists(INDEX_FILE):
        _INDEX_CACHE["mtime"] = None
        _INDEX_CACHE["records"] = []
        _INDEX_CACHE["bm25"] = None
        return []
    try:
        mtime = os.path.getmtime(INDEX_FILE)
        if _INDEX_CACHE["mtime"] == mtime and _INDEX_CACHE["records"]:
            return _INDEX_CACHE["records"]
        with open(INDEX_FILE, "r", encoding="utf-8") as index_file:
            data = json.load(index_file)
        records = data if isinstance(data, list) else []
        _INDEX_CACHE["mtime"] = mtime
        _INDEX_CACHE["records"] = records
        _INDEX_CACHE["bm25"] = _build_bm25_stats(records)
        return records
    except (OSError, json.JSONDecodeError):
        return []


def _save_index(records):
    os.makedirs(DB_DIR, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(prefix="second_brain_", suffix=".json", dir=DB_DIR)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as index_file:
            json.dump(records, index_file, ensure_ascii=False, separators=(",", ":"))
        os.replace(temporary_path, INDEX_FILE)
        try:
            _INDEX_CACHE["mtime"] = os.path.getmtime(INDEX_FILE)
            _INDEX_CACHE["records"] = records
            _INDEX_CACHE["bm25"] = _build_bm25_stats(records)
        except OSError:
            _INDEX_CACHE["mtime"] = None
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)


def remove_file_from_index(file_path):
    target_base = source_basename(file_path).lower()
    records = _load_index()
    _save_index([
        record for record in records
        if source_basename(record.get("metadata", {}).get("source", "")).lower() != target_base
    ])


def get_indexed_file_names():
    return sorted({
        source_basename(record["metadata"]["source"])
        for record in _load_index()
        if record.get("metadata", {}).get("source")
    })


STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're",
    "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
    "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with",
    "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've",
    "your", "yours", "yourself", "yourselves", "tell", "explain", "describe",
    "bta", "de", "kya", "hai", "me", "se", "ko", "ka", "ki", "ke"
}


class LocalVectorStore:
    def __init__(self):
        self.embeddings = LocalHashEmbeddings()

    def similarity_search(self, query, k=8, doc_filter=None):
        query_vector = self.embeddings.embed_query(query)
        q_tokens = [
            w for w in _tokenize_words(query)
            if w not in STOP_WORDS
        ]
        # Build adjacent query bigrams (e.g. "cyber crime", "salami attack")
        q_bigrams = [f"{q_tokens[i]} {q_tokens[i + 1]}" for i in range(len(q_tokens) - 1)]
        query_lower = " ".join(q_tokens)

        records = _load_index()
        bm25 = _INDEX_CACHE.get("bm25") or _build_bm25_stats(records)
        idf_map = bm25["idf"]
        tf_list = bm25["tf_list"]
        doc_lens = bm25["doc_lens"]
        avg_len = bm25["avg_len"]
        k1, b = 1.4, 0.55

        # Handle document filtering
        target_docs = None
        if doc_filter:
            if isinstance(doc_filter, str):
                target_docs = {source_basename(doc_filter).lower()}
            elif isinstance(doc_filter, (list, set, tuple)):
                target_docs = {source_basename(d).lower() for d in doc_filter}

        scored = []
        for idx, record in enumerate(records):
            source_path = record.get("metadata", {}).get("source", "")
            base_name = source_basename(source_path).lower()
            if target_docs and base_name not in target_docs:
                continue

            vector = record.get("embedding", [])
            vector_score = (
                sum(left * right for left, right in zip(query_vector, vector))
                if len(vector) == len(query_vector)
                else 0.0
            )

            tf_map = tf_list[idx] if idx < len(tf_list) else {}
            doc_len = doc_lens[idx] if idx < len(doc_lens) else 100
            norm_len = 1.0 - b + b * (doc_len / max(1.0, avg_len))

            # True BM25-IDF exact-word matching (fixes false substring hits like "ai" in "said")
            bm25_score = 0.0
            matched_terms = 0
            for token in set(q_tokens):
                freq = tf_map.get(token, 0)
                if freq == 0 and len(token) >= 5:
                    # Mild stem prefix fallback for plurals/forms (e.g. "attack" <-> "attacks", "classify" <-> "classification")
                    stem = token[: max(5, len(token) - 2)]
                    freq = sum(cnt for w, cnt in tf_map.items() if w.startswith(stem))
                    weight_mult = 0.65
                else:
                    weight_mult = 1.0
                if freq > 0:
                    matched_terms += 1
                    idf = idf_map.get(token, 3.5)
                    bm25_score += weight_mult * idf * ((freq * (k1 + 1.0)) / (freq + k1 * norm_len))

            # Strong bonus when chunk covers most/all distinctive query terms
            unique_q = max(1, len(set(q_tokens)))
            if matched_terms >= 2:
                bm25_score += (matched_terms / unique_q) * 4.5

            # Bigram & exact phrase match bonus (pins exact definitions & headings)
            text_lower = record["text"].lower()
            phrase_bonus = 0.0
            for bg in q_bigrams:
                if bg in text_lower:
                    phrase_bonus += 4.0
            if len(query_lower) > 6 and query_lower in text_lower:
                phrase_bonus += 5.5

            total_score = (vector_score * 1.5) + bm25_score + phrase_bonus
            scored.append((total_score, record, base_name))

        scored.sort(key=lambda item: item[0], reverse=True)

        # Multi-document balancing: If querying across all documents, prevent one single large document from crowding out others
        if not target_docs and len(scored) > k:
            doc_groups = {}
            for item in scored:
                doc_groups.setdefault(item[2], []).append(item)

            if len(doc_groups) > 1:
                # Interleave top chunks from distinct matching documents
                balanced = []
                # Allow max k//2 from any single document unless others are exhausted
                per_doc_limit = max(2, (k // len(doc_groups)) + 2)
                doc_counts = {doc: 0 for doc in doc_groups}

                for item in scored:
                    doc = item[2]
                    if doc_counts[doc] < per_doc_limit:
                        balanced.append(item)
                        doc_counts[doc] += 1
                    if len(balanced) >= k:
                        break

                # Fill remaining if needed
                if len(balanced) < k:
                    seen = set(id(item[1]) for item in balanced)
                    for item in scored:
                        if id(item[1]) not in seen:
                            balanced.append(item)
                            if len(balanced) >= k:
                                break
                scored = balanced

        return [Document(page_content=record["text"], metadata=record["metadata"]) for _, record, _ in scored[:k]]

    def get_document_chunks(self, doc_name):
        """Retrieve all text chunks belonging to a specific document."""
        target = source_basename(doc_name).lower()
        records = _load_index()
        docs = []
        for record in records:
            source = record.get("metadata", {}).get("source", "")
            if source_basename(source).lower() == target:
                docs.append(Document(page_content=record["text"], metadata=record["metadata"]))
        docs.sort(key=lambda d: d.metadata.get("page", 0))
        return docs

    def get_indexed_documents_summary(self):
        """Return information about all indexed documents."""
        records = _load_index()
        summary = {}
        for record in records:
            source = record.get("metadata", {}).get("source", "")
            if not source:
                continue
            name = source_basename(source)
            if name not in summary:
                summary[name] = {"source": normalize_source_path(source), "chunks": 0, "pages": set()}
            summary[name]["chunks"] += 1
            page = record.get("metadata", {}).get("page")
            if isinstance(page, int):
                summary[name]["pages"].add(page)

        return [
            {
                "name": name,
                "source": data["source"],
                "chunks": data["chunks"],
                "page_count": len(data["pages"]) if data["pages"] else 1
            }
            for name, data in summary.items()
        ]


def ingest_file(file_path, progress_callback=None):
    """Extract, embed, and persist a file without depending on Chroma services."""
    _emit_progress(progress_callback, "reading document", 12)
    documents = load_file(file_path)
    _emit_progress(progress_callback, "extracting text", 35)
    chunks = chunk_documents(documents)
    if not chunks:
        raise ValueError("No readable text chunks were created from this file.")
    norm_source = normalize_source_path(file_path)
    target_base = source_basename(file_path).lower()
    for chunk in chunks:
        chunk.metadata["source"] = norm_source

    _emit_progress(progress_callback, "preparing local search index", 50)
    embeddings = LocalHashEmbeddings()
    records = [
        record for record in _load_index()
        if source_basename(record.get("metadata", {}).get("source", "")).lower() != target_base
    ]
    total_chunks, batch_size = len(chunks), 48
    for start in range(0, total_chunks, batch_size):
        batch = chunks[start:start + batch_size]
        vectors = embeddings.embed_documents([chunk.page_content for chunk in batch])
        records.extend({"text": chunk.page_content, "metadata": chunk.metadata, "embedding": vector} for chunk, vector in zip(batch, vectors))
        completed = min(start + len(batch), total_chunks)
        _emit_progress(progress_callback, f"indexing {completed:,} of {total_chunks:,} knowledge chunks", 55 + int((completed / total_chunks) * 40))

    _emit_progress(progress_callback, "saving your local search index", 97)
    _save_index(records)
    _emit_progress(progress_callback, "finalizing local index", 99)
    return total_chunks


def get_vectorstore():
    return LocalVectorStore()
