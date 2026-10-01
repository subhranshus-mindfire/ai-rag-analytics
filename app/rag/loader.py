import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any

class DocumentLoader:
    """Loads and chunks documents (.pdf, .docx, .txt, .md) for RAG indexing."""

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
                raise ImportError("pypdf is required to load PDF documents.")

        elif suffix == ".docx":
            # Extract plain text from DOCX (standard library XML parsing)
            try:
                with zipfile.ZipFile(str(path)) as docx:
                    xml_content = docx.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                    paragraphs = []
                    for p in tree.findall(".//w:p", ns):
                        texts = [node.text for node in p.findall(".//w:t", ns) if node.text]
                        if texts:
                            paragraphs.append("".join(texts))
                    return "\n\n".join(paragraphs)
            except Exception as e:
                # Fallback to python-docx if installed
                try:
                    import docx
                    doc = docx.Document(str(path))
                    return "\n\n".join([p.text for p in doc.paragraphs if p.text])
                except Exception:
                    raise RuntimeError(f"Failed to read DOCX file {path.name}: {str(e)}")

        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Splits text into overlapping chunks with metadata."""
        if not text:
            return []

        metadata = metadata or {}
        chunks = []
        step = max(1, self.chunk_size - self.chunk_overlap)

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

    def list_supported_files(self, directory_path: str) -> List[Path]:
        """Returns all supported document paths in a directory."""
        dir_path = Path(directory_path)
        if not dir_path.exists():
            return []

        supported_exts = {".txt", ".md", ".markdown", ".pdf", ".docx"}
        return [
            p for p in dir_path.iterdir()
            if p.is_file() and p.suffix.lower() in supported_exts and not p.name.startswith(".")
        ]

document_loader = DocumentLoader()
