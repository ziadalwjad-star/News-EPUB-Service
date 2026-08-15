# Article image recovery

The News EPUB recipe preserves and recovers editorial article images before Calibre packages the issue.

## Why this exists

A real DietPi/Calibre issue build showed that many article pages reached the finished EPUB without any image reference even though the EPUB contained hundreds of image resources overall. The loss occurred during Calibre's automatic article cleanup/readability stage for publishers whose lead image is not retained by the generic extracted article markup.

## Current behavior

The recipe now:

- preserves standalone `<img>` elements under `<article>`, `<main>`, and `role="main"` during automatic cleanup, in addition to `<figure>` and `<picture>` containers;
- continues to normalize lazy-loaded `src`, `srcset`, and common data-image attributes before download;
- when readability still produces an image-less article, recovers a plausible lead image from Open Graph/Twitter metadata, `link rel="image_src"`, JSON-LD article image metadata, or article/main image markup;
- rejects unsafe schemes, private/local network targets, tracking pixels, placeholders, logos, avatars, icons, adverts, and similar non-editorial candidates;
- avoids adding a fallback when the extracted article already contains an image;
- reports final per-article image coverage in the Calibre log using `Article image coverage after download: ...`.

The EPUB validator remains independent of extraction. It still validates all packaged local resources and repairs Calibre's known safe raster media-type declaration mismatches in the staged EPUB before final publication.

## Regression coverage

`tests/test_recipe.py` covers article-image preservation, Open Graph fallback, JSON-LD fallback, duplicate avoidance, non-editorial image rejection, safe image schemes, and image-coverage logging.
