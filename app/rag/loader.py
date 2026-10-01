import os
from pathlib import Path
from typing import List, Dict, Any

class DocumentLoader:
    """Loads and chunks documents (.txt, .md, .pdf) for RAG indexing."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_file(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()

        if suffix in [".txt", ".md", ".markdown", ".csv", ".json"]:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        elif suffix == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path))
                pages = [page.extract_text() or "" for page in reader.pages]
                return "\n\n".join(pages)
            except ImportError:
                raise ImportError("pypdf is required to load PDF documents. Install with `pip install pypdf`.")

        else:
            # Fallback text read
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Splits text into overlapping chunks with metadata."""
        if not text:
            return []

        metadata = metadata or {}
        chunks = []
        step = max(1, self.chunk_size - self.chunk_overlap)

        # Paragraph/sentence aware splitting
        paragraphs = text.split("\n\n")
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If paragraph itself is larger than chunk_size, split by characters
                if len(para) > self.chunk_size:
                    for i in range(0, len(para), step):
                        sub_chunk = para[i:i + self.chunk_size]
                        if sub_chunk:
                            chunks.append(sub_chunk)
                    current_chunk = ""
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        # Build chunk dictionaries
        return [
            {
                "text": chunk,
                "metadata": {
                    **metadata,
                    "chunk_index": idx,
                    "chunk_length": len(chunk)
                }
            }
            for idx, chunk in enumerate(chunks)
        ]

document_loader = DocumentLoader()
