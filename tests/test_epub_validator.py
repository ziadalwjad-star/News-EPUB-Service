from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
import warnings
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
    <dc:identifier id="pub-id">urn:test</dc:identifier>
    <dc:title>Test</dc:title>
    <dc:language>en</dc:language>
    <meta property="dcterms:modified">2026-08-15T20:00:00Z</meta>
    {metadata_extra}
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
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<body><nav epub:type="toc"><ol><li><a href="article.xhtml#story">Story</a></li></ol></nav></body></html>
"""

ARTICLE = """<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><link rel="stylesheet" href="style.css"/>{head_extra}</head>
<body><article id="story"><h1>Headline</h1><p>Body.</p>{extra}</article></body></html>
"""


def build_epub(
    path: Path,
    *,
    article_extra: str = "",
    head_extra: str = "",
    nav: str = NAV,
    css: str = "p { margin: 0; }",
    metadata_extra: str = "",
    package_override: str | None = None,
    extra_manifest: str = "",
    extra_files: dict[str, bytes] | None = None,
) -> None:
    package = package_override or PACKAGE.format(metadata_extra=metadata_extra, extra_manifest=extra_manifest)
    files = {
        "META-INF/container.xml": CONTAINER_XML.encode(),
        "EPUB/package.opf": package.encode(),
        "EPUB/nav.xhtml": nav.encode(),
        "EPUB/article.xhtml": ARTICLE.format(extra=article_extra, head_extra=head_extra).encode(),
        "EPUB/style.css": css.encode(),
    }
    files.update(extra_files or {})
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for name, data in files.items():
            archive.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)


class ValidatorTests(unittest.TestCase):
    def run_validator(self, epub: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [os.fspath(VALIDATOR), "--require-epub3", *args, os.fspath(epub)],
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_rejected(self, path: Path, message: str, *args: str) -> None:
        result = self.run_validator(path, *args)
        self.assertEqual(result.returncode, 65, result.stdout + result.stderr)
        self.assertIn(message, result.stderr)

    def test_accepts_minimal_local_epub3(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "valid.epub"
            build_epub(path)
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("news-epub-validate: ok:", result.stdout)

    def test_json_metrics_are_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "valid.epub"
            build_epub(path)
            result = self.run_validator(path, "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            metrics = json.loads(result.stdout)
            self.assertEqual(metrics["version"], "3.0")
            self.assertGreaterEqual(metrics["xhtml_items"], 2)

    def test_rejects_duplicate_zip_member(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.epub"
            build_epub(path)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with zipfile.ZipFile(path, "a") as archive:
                    archive.writestr("EPUB/style.css", b"p{}")
            self.assert_rejected(path, "duplicate ZIP member name")

    def test_rejects_symlink_member(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "symlink.epub"
            build_epub(path)
            info = zipfile.ZipInfo("EPUB/link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(path, "a") as archive:
                archive.writestr(info, b"article.xhtml")
            self.assert_rejected(path, "symbolic-link ZIP members")

    def test_rejects_unsupported_compression(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bzip.epub"
            build_epub(path)
            with zipfile.ZipFile(path, "a") as archive:
                archive.writestr("EPUB/extra.bin", b"data", compress_type=zipfile.ZIP_BZIP2)
            self.assert_rejected(path, "unsupported ZIP compression method")

    def test_rejects_member_over_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.epub"
            build_epub(
                path,
                extra_manifest='<item id="large" href="large.bin" media-type="application/octet-stream"/>',
                extra_files={"EPUB/large.bin": b"x" * (2 * 1024 * 1024)},
            )
            self.assert_rejected(path, "archive member exceeds", "--max-member-mib", "1")

    def test_rejects_missing_required_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata.epub"
            bad_package = PACKAGE.format(metadata_extra="", extra_manifest="").replace("<dc:title>Test</dc:title>", "")
            build_epub(path, package_override=bad_package)
            self.assert_rejected(path, "no non-empty title")

    def test_rejects_missing_modified_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "modified.epub"
            bad_package = PACKAGE.format(metadata_extra="", extra_manifest="").replace(
                '<meta property="dcterms:modified">2026-08-15T20:00:00Z</meta>', ""
            )
            build_epub(path, package_override=bad_package)
            self.assert_rejected(path, "missing dcterms:modified")

    def test_rejects_nav_without_toc_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nav.epub"
            build_epub(path, nav=NAV.replace('epub:type="toc"', 'epub:type="landmarks"'))
            self.assert_rejected(path, "exactly one epub:type='toc'")

    def test_rejects_remote_image_resource(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "remote.epub"
            build_epub(path, article_extra='<img src="https://tracker.example/pixel.gif" alt=""/>')
            self.assert_rejected(path, "external publication resource")

    def test_rejects_missing_manifest_resource(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.epub"
            build_epub(path, extra_manifest='<item id="image" href="missing.jpg" media-type="image/jpeg"/>')
            self.assert_rejected(path, "manifest resource is missing")

    def test_rejects_reference_to_unmanifested_resource(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unmanifested.epub"
            build_epub(
                path,
                article_extra='<img src="ghost.png" alt="ghost"/>',
                extra_files={"EPUB/ghost.png": b"\x89PNG\r\n\x1a\nrest"},
            )
            self.assert_rejected(path, "publication resource is not declared in the manifest")

    def test_rejects_script_element(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "script.epub"
            build_epub(path, article_extra="<script>location.href='https://example.invalid'</script>")
            self.assert_rejected(path, "active or unsafe element <script>")

    def test_rejects_event_handler_attribute(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "event.epub"
            build_epub(path, article_extra='<p onclick="alert(1)">Text</p>')
            self.assert_rejected(path, "event-handler attribute")

    def test_rejects_base_element(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "base.epub"
            build_epub(path, head_extra='<base href="https://example.invalid/"/>')
            self.assert_rejected(path, "active or unsafe element <base>")

    def test_rejects_xml_base(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "xmlbase.epub"
            build_epub(path, article_extra='<p xml:base="https://example.invalid/">Text</p>')
            self.assert_rejected(path, "xml:base is not allowed")

    def test_rejects_meta_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "refresh.epub"
            build_epub(path, head_extra='<meta http-equiv="refresh" content="0;url=https://example.invalid"/>')
            self.assert_rejected(path, "meta refresh is not allowed")

    def test_rejects_broken_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fragment.epub"
            build_epub(path, article_extra='<a href="#missing">Broken</a>')
            self.assert_rejected(path, "missing fragment target")

    def test_rejects_duplicate_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ids.epub"
            build_epub(path, article_extra='<p id="story">Duplicate</p>')
            self.assert_rejected(path, "duplicate id")

    def test_rejects_unsafe_hyperlink_scheme(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scheme.epub"
            build_epub(path, article_extra='<a href="javascript:alert(1)">Bad</a>')
            self.assert_rejected(path, "unsafe hyperlink scheme")

    def test_allows_normal_external_source_hyperlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source-link.epub"
            build_epub(path, article_extra='<a href="https://example.org/story">Original source</a>')
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_remote_css_resource(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "css.epub"
            build_epub(path, css="body { background: url(https://example.invalid/a.png); }")
            self.assert_rejected(path, "external CSS resource/import")

    def test_rejects_remote_inline_style_resource(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inline-style.epub"
            build_epub(path, article_extra='<p style="background:url(https://example.invalid/a.png)">Text</p>')
            self.assert_rejected(path, "external publication resource")

    def test_rejects_remote_style_element_resource(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "style-element.epub"
            build_epub(path, head_extra='<style>@import "https://example.invalid/a.css";</style>')
            self.assert_rejected(path, "external publication resource")

    def test_rejects_active_svg(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "svg-script.epub"
            svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
            build_epub(
                path,
                extra_manifest='<item id="svg" href="figure.svg" media-type="image/svg+xml"/>',
                extra_files={"EPUB/figure.svg": svg},
            )
            self.assert_rejected(path, "active or unsafe element <script>")

    def test_rejects_remote_svg_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "svg-remote.epub"
            svg = b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.invalid/a.png"/></svg>'
            build_epub(
                path,
                extra_manifest='<item id="svg" href="figure.svg" media-type="image/svg+xml"/>',
                extra_files={"EPUB/figure.svg": svg},
            )
            self.assert_rejected(path, "external publication resource")

    def test_rejects_image_media_type_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image-mismatch.epub"
            build_epub(
                path,
                extra_manifest='<item id="image" href="photo.jpg" media-type="image/jpeg"/>',
                extra_files={"EPUB/photo.jpg": b"not a jpeg"},
            )
            self.assert_rejected(path, "image bytes do not match declared media type")

    def test_rejects_orphaned_publication_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orphan.epub"
            build_epub(path, extra_files={"EPUB/orphan.txt": b"orphan"})
            self.assert_rejected(path, "publication resource is not declared in the manifest")

    def test_rejects_manifest_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "escape.epub"
            build_epub(path, extra_manifest='<item id="escape" href="../../escape.bin" media-type="application/octet-stream"/>')
            self.assert_rejected(path, "resource escapes the EPUB container")


if __name__ == "__main__":
    unittest.main()
