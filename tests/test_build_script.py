from __future__ import annotations

import os
import subprocess
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "bin" / "news-epub-build"
VALIDATOR = ROOT / "bin" / "news-epub-validate"

CONTAINER_XML = b'''<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
<rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'''
PACKAGE = b'''<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">urn:test</dc:identifier><dc:title>Test</dc:title><dc:language>en</dc:language><meta property="dcterms:modified">2026-08-15T20:00:00Z</meta></metadata>
<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="a" href="article.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="a"/></spine></package>'''
NAV = b'''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol><li><a href="article.xhtml#story">Story</a></li></ol></nav></body></html>'''
ARTICLE = b'''<html xmlns="http://www.w3.org/1999/xhtml"><body><article id="story"><h1>Story</h1><p>Body.</p></article></body></html>'''


def build_valid_epub(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", CONTAINER_XML, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("EPUB/package.opf", PACKAGE, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("EPUB/nav.xhtml", NAV, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("EPUB/article.xhtml", ARTICLE, compress_type=zipfile.ZIP_DEFLATED)


def make_converter(path: Path, *, fail_status: int | None = None) -> None:
    if fail_status is None:
        body = '''#!/bin/sh
set -eu
count=0
[ ! -f "$FAKE_COUNT_FILE" ] || count="$(cat "$FAKE_COUNT_FILE")"
count=$((count + 1))
printf '%s' "$count" > "$FAKE_COUNT_FILE"
cp "$FAKE_EPUB_SOURCE" "$2"
'''
    else:
        body = f'''#!/bin/sh
set -eu
count=0
[ ! -f "$FAKE_COUNT_FILE" ] || count="$(cat "$FAKE_COUNT_FILE")"
count=$((count + 1))
printf '%s' "$count" > "$FAKE_COUNT_FILE"
exit {fail_status}
'''
    path.write_text(body)
    path.chmod(0o755)


class BuildScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "state"
        self.recipe = self.base / "recipe.recipe"
        self.recipe.write_text("# fixture\n")
        self.source = self.base / "source.epub"
        build_valid_epub(self.source)
        self.count = self.base / "count"
        self.converter = self.base / "ebook-convert"
        make_converter(self.converter)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "NEWS_EPUB_ROOT": os.fspath(self.root),
                "NEWS_EPUB_RECIPE": os.fspath(self.recipe),
                "NEWS_EPUB_VALIDATOR": os.fspath(VALIDATOR),
                "NEWS_EPUB_EBOOK_CONVERT": os.fspath(self.converter),
                "NEWS_EPUB_MAX_ATTEMPTS": "2",
                "NEWS_EPUB_RETRY_DELAY": "0",
                "NEWS_EPUB_LOCK_WAIT": "1",
                "NEWS_EPUB_REQUIRE_EPUBCHECK": "0",
                "NEWS_EPUB_FILENAME_PREFIX": "news-epub",
                "FAKE_EPUB_SOURCE": os.fspath(self.source),
                "FAKE_COUNT_FILE": os.fspath(self.count),
            }
        )
        return env

    def run_build(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [os.fspath(BUILD), *args],
            env=env or self.env(),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_help_is_available_without_runtime_dependencies(self) -> None:
        result = self.run_build("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage: news-epub-build", result.stdout)

    def test_rejects_extra_positional_arguments(self) -> None:
        result = self.run_build("morning", "unexpected")
        self.assertEqual(result.returncode, 64)
        self.assertIn("expected at most one edition argument", result.stderr)

    def test_success_publishes_standardised_filename_once(self) -> None:
        result = self.run_build("morning")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        outputs = list((self.root / "outbox").glob("news-epub_*_morning.epub"))
        self.assertEqual(len(outputs), 1)
        self.assertEqual(self.count.read_text(), "1")
        self.assertIn("stage=publish", result.stdout)
        self.assertIn("published=", result.stdout)

    def test_conversion_failure_retries_only_configured_attempts(self) -> None:
        make_converter(self.converter, fail_status=7)
        result = self.run_build("morning")
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        self.assertEqual(self.count.read_text(), "2")
        self.assertFalse(list((self.root / "outbox").glob("*.epub")))
        self.assertIn("all conversion attempts failed", result.stderr)

    def test_validation_failure_is_not_retried(self) -> None:
        self.source.write_bytes(b"not an epub")
        result = self.run_build("morning")
        self.assertEqual(result.returncode, 65, result.stdout + result.stderr)
        self.assertEqual(self.count.read_text(), "1")
        self.assertIn("will not be retried", result.stderr)
        self.assertFalse(list((self.root / "outbox").glob("*.epub")))

    def test_failed_candidate_does_not_replace_last_known_good(self) -> None:
        self.source.write_bytes(b"not an epub")
        outbox = self.root / "outbox"
        outbox.mkdir(parents=True)
        expected = outbox / f"news-epub_{time.strftime('%Y-%m-%d')}_morning.epub"
        expected.write_bytes(b"last-good")
        result = self.run_build("morning")
        self.assertEqual(result.returncode, 65, result.stdout + result.stderr)
        self.assertEqual(expected.read_bytes(), b"last-good")

    def test_rejects_unsafe_filename_prefix_before_conversion(self) -> None:
        env = self.env()
        env["NEWS_EPUB_FILENAME_PREFIX"] = "../bad"
        result = self.run_build("morning", env=env)
        self.assertEqual(result.returncode, 64, result.stdout + result.stderr)
        self.assertFalse(self.count.exists())
        self.assertIn("NEWS_EPUB_FILENAME_PREFIX", result.stderr)

    def test_reports_unreadable_recipe_before_conversion(self) -> None:
        env = self.env()
        env["NEWS_EPUB_RECIPE"] = os.fspath(self.base / "missing.recipe")
        result = self.run_build("morning", env=env)
        self.assertEqual(result.returncode, 66, result.stdout + result.stderr)
        self.assertFalse(self.count.exists())
        self.assertIn("stage=preflight", result.stderr)

    def test_cleans_stale_staging_directory(self) -> None:
        work = self.root / "work"
        stale = work / ".run.stale"
        stale.mkdir(parents=True)
        old = time.time() - 3 * 3600
        os.utime(stale, (old, old))
        env = self.env()
        env["NEWS_EPUB_STALE_RUN_HOURS"] = "1"
        result = self.run_build("morning", env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(stale.exists())

    def test_work_and_outbox_can_be_configured_independently(self) -> None:
        env = self.env()
        env["NEWS_EPUB_WORK"] = os.fspath(self.base / "custom-work")
        env["NEWS_EPUB_OUTBOX"] = os.fspath(self.base / "custom-outbox")
        result = self.run_build("night", env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(list((self.base / "custom-outbox").glob("news-epub_*_night.epub"))), 1)


if __name__ == "__main__":
    unittest.main()
