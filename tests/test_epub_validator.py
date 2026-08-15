from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "bin" / "news-epub-validate"

CONTAINER_XML = """<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
"""

PACKAGE = """<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">urn:test</dc:identifier><dc:title>Test</dc:title><dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="article" href="article.xhtml" media-type="application/xhtml+xml"/>
    <item id="css" href="style.css" media-type="text/css"/>
    {extra_manifest}
  </manifest>
  <spine><itemref idref="article"/></spine>
</package>
"""

NAV = """<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><nav xmlns:epub="http://www.idpf.org/2007/ops" epub:type="toc"><ol><li><a href="article.xhtml#story">Story</a></li></ol></nav></body></html>
"""

ARTICLE = """<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><link rel="stylesheet" href="style.css"/></head><body><article id="story"><h1>Headline</h1><p>Body.</p>{extra}</article></body></html>
"""


def build_epub(path: Path, *, article_extra: str = "", css: str = "p { margin: 0; }", extra_manifest: str = "", extra_files: dict[str, bytes] | None = None) -> None:
    files = {
        "META-INF/container.xml": CONTAINER_XML.encode(),
        "EPUB/package.opf": PACKAGE.format(extra_manifest=extra_manifest).encode(),
        "EPUB/nav.xhtml": NAV.encode(),
        "EPUB/article.xhtml": ARTICLE.format(extra=article_extra).encode(),
        "EPUB/style.css": css.encode(),
    }
    files.update(extra_files or {})
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for name, data in files.items():
            archive.writestr(name, data)


class ValidatorTests(unittest.TestCase):
    def run_validator(self, epub: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [os.fspath(VALIDATOR), "--require-epub3", os.fspath(epub)],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_accepts_minimal_local_epub3(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "valid.epub"
            build_epub(path)
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("version=3.0", result.stdout)

    def test_rejects_remote_image_resource(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "remote.epub"
            build_epub(path, article_extra='<img src="https://tracker.example/pixel.gif" alt=""/>')
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 65)
            self.assertIn("external publication resource", result.stderr)

    def test_rejects_missing_manifest_resource(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.epub"
            build_epub(path, extra_manifest='<item id="image" href="missing.jpg" media-type="image/jpeg"/>')
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 65)
            self.assertIn("manifest resource is missing", result.stderr)

    def test_rejects_script_element(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "script.epub"
            build_epub(path, article_extra="<script>location.href='https://example.invalid'</script>")
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 65)
            self.assertIn("active element <script>", result.stderr)

    def test_rejects_broken_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fragment.epub"
            build_epub(path, article_extra='<a href="#missing">Broken</a>')
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 65)
            self.assertIn("missing fragment target", result.stderr)

    def test_rejects_unsafe_hyperlink_scheme(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scheme.epub"
            build_epub(path, article_extra='<a href="javascript:alert(1)">Bad</a>')
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 65)
            self.assertIn("unsafe hyperlink scheme", result.stderr)

    def test_rejects_remote_css_resource(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "css.epub"
            build_epub(path, css="body { background: url(https://example.invalid/a.png); }")
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 65)
            self.assertIn("external CSS resource/import", result.stderr)


if __name__ == "__main__":
    unittest.main()
