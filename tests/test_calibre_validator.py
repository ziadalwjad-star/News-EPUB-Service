from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    from tests.test_epub_validator import build_epub
except ModuleNotFoundError:
    from test_epub_validator import build_epub

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "bin" / "news-epub-validate"


class CalibreValidatorCompatibilityTests(unittest.TestCase):
    def run_validator(self, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [os.fspath(VALIDATOR), "--require-epub3", "--json", os.fspath(path)],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_tolerates_known_safe_raster_mismatch_with_explicit_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "calibre-mismatch.epub"
            build_epub(
                path,
                extra_manifest='<item id="image" href="photo.png" media-type="image/png"/>',
                extra_files={"EPUB/photo.png": b"\xff\xd8\xff\xe0" + b"jpeg bytes"},
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("raster media-type mismatch accepted", result.stderr)
            metrics = json.loads(result.stdout)
            self.assertEqual(metrics["image_items"], 1)
            self.assertEqual(metrics["raster_media_type_warnings"], 1)

    def test_still_rejects_unrecognised_image_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad-image.epub"
            build_epub(
                path,
                extra_manifest='<item id="image" href="photo.png" media-type="image/png"/>',
                extra_files={"EPUB/photo.png": b"not a recognised raster image"},
            )
            result = self.run_validator(path)
            self.assertEqual(result.returncode, 65, result.stdout + result.stderr)
            self.assertIn("not a recognised safe raster format", result.stderr)


if __name__ == "__main__":
    unittest.main()
