from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTABLE_CORE = [
    ROOT / "bin" / "news-epub-build",
    ROOT / "bin" / "news-epub-validate",
    ROOT / "recipe" / "news-epub.recipe",
]


class ProjectPolicyTests(unittest.TestCase):
    def test_portable_core_has_no_personal_or_device_specific_paths(self) -> None:
        forbidden = ("/home/", "/mnt/us", "Kindle", "Syncthing", "DietPi", "ziadalwjad")
        for path in PORTABLE_CORE:
            text = path.read_text(encoding="utf-8")
            for value in forbidden:
                self.assertNotIn(value, text, f"{path}: unexpected deployment-specific value {value!r}")

    def test_build_script_avoids_dynamic_shell_execution(self) -> None:
        text = (ROOT / "bin" / "news-epub-build").read_text(encoding="utf-8")
        self.assertNotRegex(text, re.compile(r"(^|[;\s])eval\s", re.MULTILINE))
        self.assertNotIn("sh -c", text)
        self.assertNotIn("bash -c", text)

    def test_systemd_integration_has_one_service_and_one_timer(self) -> None:
        names = sorted(path.name for path in (ROOT / "systemd").iterdir() if path.is_file())
        self.assertEqual(names, ["news-epub.service", "news-epub.timer"])

    def test_standardised_output_prefix_is_machine_independent(self) -> None:
        config = (ROOT / "config" / "news-epub.conf.example").read_text(encoding="utf-8")
        self.assertIn("NEWS_EPUB_FILENAME_PREFIX=news-epub", config)
        self.assertNotIn("NEWS_EPUB_OUTBOX=/home/", config)


if __name__ == "__main__":
    unittest.main()
