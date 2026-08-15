# News EPUB Service

A scheduled news aggregation service that collects articles from curated RSS and Atom feeds and automatically builds clean, e-reader-friendly EPUB editions throughout the day.

The programme is designed to:

* automatically produce Morning, Evening and Night news editions on a configurable schedule;
* collect articles from multiple RSS and Atom sources across news, politics, technology, security, finance, science and other categories;
* filter articles by age and remove duplicate stories;
* clean web content for comfortable offline reading on e-ink and other e-readers;
* preserve useful article images while removing tracking pixels, scripts, forms, video and other unnecessary web content;
* generate a structured newspaper-style EPUB with sections, article navigation, metadata and a dated edition cover;
* optimise images and formatting for efficient EPUB output;
* validate completed EPUB files before publishing them;
* build editions in a temporary workspace so incomplete files are never exposed as finished publications;
* publish completed editions to a dedicated outbox suitable for Syncthing or another file-synchronisation service;
* automatically remove older editions according to the configured retention period;
* prevent overlapping builds and retry failed conversions;
* run automatically through systemd using a dedicated unprivileged service account;
* allow storage paths, output profile, retention and other deployment settings to be configured without modifying the programme itself.

In normal use, the service is installed once and runs automatically. Each scheduled timer starts the appropriate edition build, Calibre retrieves and processes the configured news sources, and the completed EPUB is placed in the outbox for local use or automatic synchronisation to an e-reader or other device.

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
