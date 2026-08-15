from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path

from bs4 import BeautifulSoup as Bs4BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "recipe" / "news-epub.recipe"


class Log:
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.exceptions = []

    def info(self, message):
        self.infos.append(str(message))

    def warning(self, message):
        self.warnings.append(str(message))

    def exception(self, message):
        self.exceptions.append(str(message))


class BasicNewsRecipe:
    feeds = []
    oldest_article = 1
    test = None

    def __init__(self, options, log, progress_reporter):
        self.log = log
        self.feeds = list(getattr(self, "feeds", []))
        self.oldest_article = getattr(self, "oldest_article", 1)
        self.test = None

    def parse_feeds(self):
        return []

    def get_article_url(self, article):
        return getattr(article, "url", None)

    def add_toc_thumbnail(self, article, src):
        article.thumbnail = src

    def extract_readable_article(self, html, url):
        return html

    def cleanup(self):
        return None


def install_calibre_stubs() -> None:
    calibre = types.ModuleType("calibre")
    ebooks = types.ModuleType("calibre.ebooks")
    soup_module = types.ModuleType("calibre.ebooks.BeautifulSoup")
    web = types.ModuleType("calibre.web")
    feeds = types.ModuleType("calibre.web.feeds")
    news = types.ModuleType("calibre.web.feeds.news")
    soup_module.BeautifulSoup = lambda markup="": Bs4BeautifulSoup(markup, "html.parser")
    news.BasicNewsRecipe = BasicNewsRecipe
    sys.modules.update(
        {
            "calibre": calibre,
            "calibre.ebooks": ebooks,
            "calibre.ebooks.BeautifulSoup": soup_module,
            "calibre.web": web,
            "calibre.web.feeds": feeds,
            "calibre.web.feeds.news": news,
        }
    )


def load_recipe():
    install_calibre_stubs()
    loader = importlib.machinery.SourceFileLoader("news_epub_recipe_test", os.fspath(RECIPE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class RecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_recipe()
        cls.recipe_class = cls.module.NewsEpubRecipe

    def make_recipe(self):
        log = Log()
        recipe = self.recipe_class(None, log, None)
        return recipe, log

    def test_feed_inventory_is_preserved(self):
        self.assertEqual(len(self.recipe_class.feed_groups), 19)
        self.assertEqual(sum(len(entries) for _group, entries in self.recipe_class.feed_groups), 62)

    def test_default_issue_completeness_threshold_is_meaningful(self):
        self.assertGreaterEqual(self.recipe_class.min_issue_articles, 10)

    def test_srcset_prefers_smallest_width_at_or_above_target(self):
        srcset = "a.jpg 800w, b.jpg 1600w, c.jpg 2400w"
        self.assertEqual(self.recipe_class.best_srcset_source(srcset), "b.jpg")

    def test_srcset_prefers_largest_width_when_all_are_below_target(self):
        srcset = "a.jpg 800w, b.jpg 1200w"
        self.assertEqual(self.recipe_class.best_srcset_source(srcset), "b.jpg")

    def test_rejects_explicit_local_and_private_network_targets(self):
        self.assertTrue(self.recipe_class.url_has_unsafe_network_target("http://127.0.0.1/private"))
        self.assertTrue(self.recipe_class.url_has_unsafe_network_target("http://10.1.2.3/private"))
        self.assertTrue(self.recipe_class.url_has_unsafe_network_target("http://[::1]/private"))
        self.assertTrue(self.recipe_class.url_has_unsafe_network_target("file:///etc/passwd"))
        self.assertFalse(self.recipe_class.url_has_unsafe_network_target("https://example.org/story"))
        self.assertFalse(self.recipe_class.url_has_unsafe_network_target("/relative/image.jpg"))

    def test_url_logging_omits_credentials_query_and_fragment(self):
        rendered = self.recipe_class.url_for_log(
            "https://user:secret@example.org:8443/story?token=private#section"
        )
        self.assertEqual(rendered, "https://example.org:8443/story")

    def test_image_source_rejects_explicit_private_network_target(self):
        self.assertFalse(self.recipe_class.image_source_is_usable("http://192.168.1.2/image.jpg"))
        self.assertFalse(self.recipe_class.image_source_is_usable("ftp://example.org/image.jpg"))
        self.assertTrue(self.recipe_class.image_source_is_usable("https://example.org/image.jpg"))
        self.assertTrue(self.recipe_class.image_source_is_usable("/images/photo.jpg"))

    def test_image_normalisation_uses_lazy_source_and_removes_tracking_pixel(self):
        soup = Bs4BeautifulSoup(
            '<div><img src="placeholder.gif" data-src="https://example.org/photo.jpg"/>'
            '<img src="https://tracker.example/1x1.gif" width="1" height="1"/></div>',
            "html.parser",
        )
        self.recipe_class.normalise_images(soup)
        images = soup.find_all("img")
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["src"], "https://example.org/photo.jpg")

    def test_auto_cleanup_preserves_article_images(self):
        keep = self.recipe_class.auto_cleanup_keep
        self.assertIn("//article//img", keep)
        self.assertIn("//main//img", keep)
        self.assertIn("//*[@role='main']//img", keep)

    def test_fallback_hero_uses_open_graph_image_when_extracted_article_is_image_less(self):
        source = Bs4BeautifulSoup(
            '<html><head>'
            '<meta property="og:image" content="https://cdn.example.org/hero.jpg"/>'
            '<meta property="og:image:alt" content="Lead photograph"/>'
            '</head><body><article><p>Text</p></article></body></html>',
            "html.parser",
        )
        extracted = '<html><body><h2>Story</h2><p>Text</p></body></html>'
        rendered, injected, origin = self.recipe_class.inject_fallback_hero(extracted, str(source))
        soup = Bs4BeautifulSoup(rendered, "html.parser")
        self.assertTrue(injected)
        self.assertEqual(origin, "meta:og:image")
        self.assertEqual(soup.find("img")["src"], "https://cdn.example.org/hero.jpg")
        self.assertEqual(soup.find("img")["alt"], "Lead photograph")

    def test_fallback_hero_does_not_duplicate_existing_extracted_image(self):
        source = (
            '<html><head><meta property="og:image" content="https://cdn.example.org/hero.jpg"/></head>'
            '<body><article><p>Text</p></article></body></html>'
        )
        extracted = '<html><body><h2>Story</h2><img src="images/local.jpg"/><p>Text</p></body></html>'
        rendered, injected, origin = self.recipe_class.inject_fallback_hero(extracted, source)
        soup = Bs4BeautifulSoup(rendered, "html.parser")
        self.assertFalse(injected)
        self.assertEqual(origin, "")
        self.assertEqual([img["src"] for img in soup.find_all("img")], ["images/local.jpg"])

    def test_fallback_hero_uses_json_ld_image(self):
        source = (
            '<html><head><script type="application/ld+json">'
            '{"@type":"NewsArticle","image":{"url":"https://cdn.example.org/json-hero.jpg"}}'
            '</script></head><body><article><p>Text</p></article></body></html>'
        )
        extracted = '<html><body><p>Text</p></body></html>'
        rendered, injected, origin = self.recipe_class.inject_fallback_hero(extracted, source)
        soup = Bs4BeautifulSoup(rendered, "html.parser")
        self.assertTrue(injected)
        self.assertEqual(origin, "json-ld:image")
        self.assertEqual(soup.find("img")["src"], "https://cdn.example.org/json-hero.jpg")

    def test_fallback_hero_rejects_logo_like_metadata(self):
        source = (
            '<html><head><meta property="og:image" content="https://cdn.example.org/site-logo.png"/></head>'
            '<body><article><p>Text</p></article></body></html>'
        )
        extracted = '<html><body><p>Text</p></body></html>'
        _rendered, injected, origin = self.recipe_class.inject_fallback_hero(extracted, source)
        self.assertFalse(injected)
        self.assertEqual(origin, "")

    def test_cleanup_logs_article_image_coverage(self):
        recipe, log = self.make_recipe()
        recipe.postprocess_html(Bs4BeautifulSoup('<article><img src="images/a.jpg"/></article>', "html.parser"), True)
        recipe.postprocess_html(Bs4BeautifulSoup('<article><p>No image</p></article>', "html.parser"), True)
        recipe._fallback_hero_injections = 1
        recipe.cleanup()
        messages = log.infos + log.warnings
        self.assertEqual(len(messages), 1)
        self.assertIn("Article image coverage after download: 1/2 (50.0%)", messages[0])
        self.assertIn("hero fallbacks injected=1", messages[0])

    def test_semantic_attributes_survive_source_cleanup(self):
        recipe, _log = self.make_recipe()
        soup = Bs4BeautifulSoup(
            '<article lang="ar" dir="rtl" class="site"><p id="note" style="color:red">Text</p>'
            '<ol start="3"><li value="5">Item</li></ol>'
            '<table><tr><th id="h" scope="col">H</th><td headers="h" colspan="2">V</td></tr></table></article>',
            "html.parser",
        )
        cleaned = recipe.preprocess_html(soup)
        article = cleaned.find("article")
        self.assertEqual(article.get("lang"), "ar")
        self.assertEqual(article.get("dir"), "rtl")
        self.assertIsNone(article.get("class"))
        self.assertEqual(cleaned.find("p").get("id"), "note")
        self.assertIsNone(cleaned.find("p").get("style"))
        self.assertEqual(cleaned.find("ol").get("start"), "3")
        self.assertEqual(cleaned.find("li").get("value"), "5")
        self.assertEqual(cleaned.find("th").get("scope"), "col")
        self.assertEqual(cleaned.find("td").get("headers"), ["h"])
        self.assertEqual(cleaned.find("td").get("colspan"), "2")

    def test_unsafe_link_scheme_is_removed_but_text_is_preserved(self):
        recipe, _log = self.make_recipe()
        soup = Bs4BeautifulSoup('<p><a href="javascript:alert(1)">Keep text</a></p>', "html.parser")
        cleaned = recipe.preprocess_html(soup)
        link = cleaned.find("a")
        self.assertEqual(link.get_text(), "Keep text")
        self.assertIsNone(link.get("href"))

    def test_active_and_embedded_source_elements_are_removed(self):
        recipe, _log = self.make_recipe()
        soup = Bs4BeautifulSoup(
            '<article><p>Keep</p><script>alert(1)</script><form><input/></form><svg><text>x</text></svg></article>',
            "html.parser",
        )
        cleaned = recipe.preprocess_html(soup)
        self.assertEqual(cleaned.find("p").get_text(), "Keep")
        self.assertIsNone(cleaned.find("script"))
        self.assertIsNone(cleaned.find("form"))
        self.assertIsNone(cleaned.find("svg"))

    def test_remote_images_remaining_after_calibre_processing_are_removed_and_logged(self):
        recipe, log = self.make_recipe()
        soup = Bs4BeautifulSoup(
            '<article><img src="https://example.org/remote.jpg"/><img src="images/local.jpg"/></article>',
            "html.parser",
        )
        cleaned = recipe.postprocess_html(soup, True)
        images = cleaned.find_all("img")
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["src"], "images/local.jpg")
        self.assertEqual(len(log.warnings), 1)
        self.assertIn("Removed 1 image references", log.warnings[0])

    def test_empty_issue_is_an_explicit_failure(self):
        recipe, _log = self.make_recipe()
        with self.assertRaisesRegex(RuntimeError, "minimum required"):
            recipe.parse_feeds()

    def test_conversion_does_not_disable_calibre_flow_splitting_or_linearise_tables(self):
        self.assertNotIn("flow_size", self.recipe_class.conversion_options)
        self.assertNotIn("linearize_tables", self.recipe_class.conversion_options)

    def test_design_avoids_web_card_and_pill_patterns(self):
        css = self.recipe_class.extra_css.lower()
        self.assertNotIn("border-radius", css)
        self.assertNotIn("box-shadow", css)
        self.assertNotIn("gradient", css)
        self.assertNotIn("position: fixed", css)


if __name__ == "__main__":
    unittest.main()
