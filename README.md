# News EPUB Service — Automated, Validated & Syncthing-Ready News EPUB Publishing

A production-focused news aggregation and EPUB publishing service that collects articles from curated RSS and Atom feeds, cleans and normalises real-world publisher content, builds e-reader-friendly Morning, Evening and Night editions, validates them through multiple integrity and visual-quality gates, and publishes approved EPUBs to a synchronisation-ready outbox.

The programme is designed to:

* automatically produce Morning, Evening and Night news editions at 06:00, 17:30 and 22:00 Europe/London;
* collect articles from curated RSS and Atom sources across world news, politics, technology, cybersecurity, privacy, finance, law, defence, science and other categories;
* filter articles by age and remove duplicate stories;
* extract and clean publisher webpages for comfortable offline reading on e-ink and other e-readers;
* maintain one authoritative article headline and prevent duplicate, repeated or differently worded feed/page headlines from appearing together;
* synchronise EPUB navigation and TOC titles with the authoritative article headline;
* preserve useful article text, subheadings, captions, credits and editorial imagery while removing advertising, promotional modules, tracking content and unrelated recommendations;
* recover editorial images from lazy-loading, responsive-image, `<picture>`, OpenGraph, structured metadata and other real-world publisher image sources;
* prevent duplicate hero images and visually duplicated photographs caused by alternate URLs, crops, resolutions or encodings;
* enforce at most one lead image between the article headline and the first substantive paragraph;
* preserve legitimate later article images in their appropriate positions instead of creating artificial image galleries at the end of articles;
* reject tracking pixels, placeholders, avatars, logos, social graphics, recommendation thumbnails and other non-editorial imagery;
* optimise images and formatting for efficient EPUB output and e-reader display;
* generate a structured newspaper-style EPUB with sections, article navigation, metadata and a dated edition cover;
* repair recoverable XHTML, image-reference, manifest and media-type problems produced by real-world publisher content;
* validate EPUB package structure, manifest resources, spine content, image references, links and other integrity requirements;
* run a separate visual/content audit covering headlines, images, advertisements, publisher promotions, malformed articles and other rendering-quality problems;
* require EPUBCheck validation before publication;
* reject invalid or visually unsafe candidates before they can replace the last known-good published edition;
* build editions in private temporary storage and publish completed EPUBs through destination-local staging and atomic final publication;
* expose only the current day's Morning, Evening and Night editions in the synchronised outbox;
* move previous editions to a separate server-side archive outside the recursively synchronised Syncthing directory;
* automatically remove stray non-production files from the publication outbox;
* support configurable historical archive retention;
* integrate with Syncthing while remaining usable with other file-synchronisation or storage systems;
* inspect and validate relevant Syncthing folder configuration;
* report whether a Kindle or other configured Syncthing peer is connected and whether it has actually completed synchronisation;
* distinguish successful local EPUB publication from successful remote-device delivery;
* provide end-to-end article and overall build progress instead of relying on Calibre's phase-local percentage reporting;
* prevent overlapping builds and provide controlled retry and failure handling;
* run automatically through a hardened systemd service using a dedicated unprivileged account;
* use one persistent systemd timer for all three daily editions;
* preserve missed-run recovery through systemd `Persistent=true`;
* provide command-line tools for installation, building, validation, auditing, Syncthing setup, Kindle delivery status and diagnostics;
* allow storage paths, archive paths, output profile, retention, Calibre behaviour and other deployment settings to be configured without modifying the programme itself;
* provide regression tests, media-quality benchmarks, SHA-256 manifests and GitHub Actions checks for reproducible releases.

In normal use, the service is installed once and runs automatically. The persistent systemd timer starts the appropriate Morning, Evening or Night build at the configured Europe/London schedule. Calibre retrieves and processes the configured news sources, the service repairs and normalises the resulting content, performs structural validation and visual/content auditing, runs EPUBCheck, and publishes the edition only after every required production gate succeeds.

Approved EPUBs are placed in the current-day outbox for local use or automatic synchronisation. Previous editions are moved to the separate archive, and Syncthing delivery can be checked independently so successful EPUB creation is not mistaken for successful delivery to the receiving e-reader.

Please use the releases tab for the latest version.

# v1.1.1

Focused production-alignment and CBS content-quality fix.

Changes

* Fixed CBS News Politics related-story modules leaking non-editorial thumbnails into article endings.
* Added a narrow cbsnews.com cleanup rule targeting li elements whose IDs begin with inline-recirc-item--.
* Fixed the two reproducible trailing_image_clusters audit failures without weakening validation.
* Prevented CBS recommendation thumbnails from leaking across neighbouring article image paths.
* Preserved legitimate CBS article text and editorial images while removing only the proven recirculation module.

# v1.1

Major EPUB quality, Kindle delivery, validation, scheduling and production-reliability update.

Changes

* Reworked article headline handling around a single authoritative source-page headline instead of allowing the RSS/feed title and extracted page title to compete.
* Fixed articles displaying two differently worded headlines when the RSS title and publisher headline described the same story differently.
* EPUB navigation and TOC titles are now synchronised to the authoritative article headline.
* Added final headline canonicalisation before and after XHTML normalisation so publisher markup cannot recreate duplicate headings later in the conversion pipeline.
* Added detection and cleanup for repeated, near-duplicate, publisher-suffixed and differently represented headline blocks.
* Added detection of doubled or tripled headline text contained inside a single heading element.
* Additional opening headings are now converted to neutral deck/body text when appropriate instead of rendering as a second headline.
* Removed retained headline classes, inline font styling and nested bold formatting from demoted heading blocks so they cannot still look like headlines on Kindle.
* Added independent final headline-rendering gates for duplicate blocks, repeated title text, extra opening headings and residual headline-style variants.
* Reworked lead-image handling so structured metadata such as OpenGraph, Twitter image metadata and JSON-LD cannot inject a second hero when an editorial lead image is already present.
* Added a strict final-layout rule allowing at most one lead image between the article headline and first substantive paragraph.
* Added lead-image selection that favours large editorial photographs over avatars, logos, icons, branding and sharing graphics.
* Added exact-resource, SHA-256 and decoded-raster perceptual image deduplication for resized, recompressed and differently encoded copies of the same photograph.
* Added canonicalisation for common CDN, responsive-image and resized-image URL variants.
* Improved image placement so recovered body images must map to an appropriate article position instead of being appended arbitrarily.
* Added filtering for related-story, recommended-story, trending, most-read and similar thumbnail modules.
* Added detection and rejection of suspicious trailing image clusters after substantive article text.
* Improved preservation of genuine body photographs, captions, credits and source ordering while applying stricter duplicate and junk-image filtering.
* Expanded publisher cleanup for newsletter, subscription, promotional, advertising, CRM, social-channel and branded call-to-action modules.
* Added final post-XHTML promotion cleanup so publisher modules hidden inside custom elements cannot evade earlier cleaning.
* Added promotion matching across split inline markup.
* Expanded cleanup coverage for observed publisher noise from BBC, Deutsche Welle, Times of Israel, The Record, NASA, Premium Times, Euronews, Guardian, ABC and other sources.
* Added a comprehensive EPUB integrity validator covering package structure, manifest resources, spine content, broken references, remote resources, unsafe links, scripts, active SVG, duplicate IDs and malformed EPUB content.
* Added automatic repair for recoverable broken local article-image references.
* Added automatic correction of raster manifest media types when downloaded image bytes do not match their declared PNG or JPEG type.
* Added EPUB 3 metadata, XHTML and structural repair handling for malformed real-world publisher output.
* Added EPUBCheck as a production publication gate so candidates with EPUBCheck errors are rejected before publication.
* Made Calibre flow-size handling configurable through `NEWS_EPUB_FLOW_SIZE` while retaining the large-article-safe behaviour used in v1.0.
* Strengthened the existing temporary-file publication process with destination-local staging, filesystem synchronisation, byte verification and final atomic publication.
* Extended last-known-good protection so candidates that fail structural validation, content audit or EPUBCheck cannot replace the current published edition.
* Reworked the Syncthing-facing outbox into a strict today-only publication directory.
* Only the current day's Morning, Evening and Night EPUBs are permitted to remain in the synchronised outbox.
* Previous-day and legacy EPUBs are moved to a sibling server-side archive outside the recursively synchronised Syncthing directory.
* Old pairing, permissions, status and other non-production files are removed from the production outbox.
* Added configurable archive retention.
* Added validation preventing the archive directory from being placed inside the Syncthing outbox.
* Added Syncthing configuration discovery and validation covering folder path, folder type, pause state, watcher/rescan settings, marker directory, device relationships and ignore rules.
* Added `news-epub-kindle-status` to distinguish successful local publication from actual remote Kindle synchronisation.
* Added Kindle delivery diagnostics for connection state, remote completion percentage, outstanding items, outstanding bytes and remote folder state.
* Local EPUB publication is no longer treated as proof that the Kindle has received the file.
* Added `news-epub-diagnose`, `news-epub-status`, `news-epub-run`, `news-epub-audit`, `news-epub-validate`, `news-epub-syncthing-setup` and installation/status helpers.
* Added end-to-end News EPUB Service progress reporting instead of relying on Calibre's phase-local percentage values.
* Added separate article-acquisition progress and overall build progress through retrieval, conversion, validation, audit, EPUBCheck and publication.
* Builds now reach `overall=100%` only after the complete production pipeline succeeds.
* Added stage-aware status reporting for long-running builds.
* Reworked scheduling from three separate timer units and a templated service into one consolidated systemd service and timer.
* The existing 06:00, 17:30 and 22:00 schedule is now explicitly anchored to `Europe/London`.
* Persistent timer behaviour is retained for missed-run recovery.
* Improved installation and upgrade handling for the consolidated service and timer.
* Hardened the existing unprivileged `news-epub` runtime with stronger systemd sandboxing and clearer separation between private working storage, publication storage and archive storage.
* Expanded configuration validation for publication paths, archive paths, filename prefixes, retry behaviour, EPUBCheck requirements and Calibre options.
* Standardised published filenames as `daily-news_YYYY-MM-DD_morning.epub`, `daily-news_YYYY-MM-DD_evening.epub` and `daily-news_YYYY-MM-DD_night.epub`.
* Added machine-readable audit metrics for article/image coverage, broken references, junk content, promotions, headline integrity, opening-image overflow, duplicate images and trailing image clusters.
* Added hard production gates requiring zero broken or remote references, zero known junk/promotional modules, one visible headline, at most one opening image and no duplicate article images or suspicious trailing image clusters.
* Expanded the existing responsive and lazy-image handling with structured hero metadata, stronger deduplication, placement rules and additional safety checks.
* Added image safety limits for malformed payloads, excessive decoded dimensions, unsafe URLs, private-network targets and active SVG content.
* Improved support for legitimate editorial portraits, infographics, RTL articles and multi-image stories.
* Expanded image-format handling for real-world publisher JPEG, PNG, WebP, AVIF and related delivery patterns.
* Added detailed DietPi deployment, security, audit, image-recovery and operational documentation.
* Added a reproducible SHA-256 package manifest and normalised GitHub-ready release layout.
* Added GitHub Actions regression testing with Beautiful Soup and Pillow dependencies.
* Expanded automated coverage to 217 regression tests covering build behaviour, EPUB validation and repair, headline rendering, image selection and deduplication, publisher cleanup, Syncthing configuration, archival behaviour, scheduling and operator helpers.
* Added a deterministic media benchmark covering editorial-image retention, junk rejection, caption recovery and multi-image ordering.
* Current media benchmark results are 9/9 editorial images retained, 3/3 junk images rejected, 7/7 captions recovered and 2/2 multi-image ordering cases correct.
* Improved error reporting throughout the recipe, build scripts and deployment tooling with stronger validation and fewer silent or ambiguous failure paths.
* Replaced the v1.0 aged-file deletion model with a today-only synchronised outbox plus separate historical archive.
* Removed reliance on filename equality, URL equality or exact textual headline matching as the sole method for detecting visually duplicated article content.


# v1.0

Initial release of the News EPUB Service.

Features

* Automated Morning, Evening and Night EPUB generation.
* Dedicated systemd service and timers for scheduled operation.
* Curated RSS and Atom feed aggregation across multiple subject areas.
* Per-source article age limits.
* Duplicate article filtering.
* Automatic webpage cleanup and removal of unnecessary interactive content.
* Lazy-loaded and responsive image handling.
* Tracking and placeholder image filtering.
* Image compression and device-aware scaling.
* Newspaper-style sections, navigation and article lists.
* Automatic dated cover generation for each edition.
* Configurable Calibre output profile.
* Temporary build files with atomic publication to the final outbox.
* EPUB ZIP-integrity validation before publication.
* Build locking to prevent concurrent editions from interfering with each other.
* Bounded retry handling for failed builds.
* Automatic cleanup of older EPUB editions.
* Configurable storage, recipe, lock and output settings.
* Dedicated non-root service account for safer unattended operation.
* Generic output directory suitable for Syncthing, network storage or other synchronisation workflows.
* Designed to remain independent of any specific e-reader, server distribution or synchronisation platform.
