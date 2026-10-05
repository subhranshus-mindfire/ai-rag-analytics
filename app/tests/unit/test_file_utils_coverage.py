"""
Unit tests covering DocumentLoader multi-format support and chunking edge cases.
"""
import unittest
import tempfile
from pathlib import Path
from app.utils.core_utils.file_utils import DocumentLoader


class TestFileUtilsCoverage(unittest.TestCase):
    def setUp(self):
        self.loader = DocumentLoader(chunk_size=120, chunk_overlap=20)

    def test_load_markdown_and_json(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
            f.write("# Title\n\nContent paragraph.")
            md_path = f.name

        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as f:
            f.write('{"key": "value"}')
            json_path = f.name

        try:
            self.assertIn("# Title", self.loader.load_file(md_path))
            self.assertIn('"key"', self.loader.load_file(json_path))
        finally:
            Path(md_path).unlink(missing_ok=True)
            Path(json_path).unlink(missing_ok=True)

    def test_load_nonexistent_file_raises_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.loader.load_file("non_existent_file_path.txt")

    def test_chunking_empty_and_oversized_text(self):
        # Empty text
        self.assertEqual(self.loader.chunk_text(""), [])

        # Long paragraph exceeding chunk_size
        long_para = "A" * 350
        chunks = self.loader.chunk_text(long_para)
        self.assertTrue(len(chunks) >= 3)
        self.assertTrue(all(len(c["text"]) <= 120 for c in chunks))

    def test_list_supported_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            (p / "doc1.txt").write_text("Hello")
            (p / "doc2.md").write_text("World")
            (p / "ignored.exe").write_text("Bin")
            (p / ".hidden.txt").write_text("Hidden")

            files = self.loader.list_supported_files(tmpdir)
            filenames = [f.name for f in files]
            self.assertIn("doc1.txt", filenames)
            self.assertIn("doc2.md", filenames)
            self.assertNotIn("ignored.exe", filenames)
            self.assertNotIn(".hidden.txt", filenames)


if __name__ == "__main__":
    unittest.main()
