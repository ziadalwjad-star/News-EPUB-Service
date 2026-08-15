# News EPUB Service

A local-first Calibre news publishing service for building self-contained, e-reader-oriented EPUB editions on Linux.

The project intentionally stays small: Calibre performs feed/article acquisition and ebook conversion; this repository supplies the curated recipe, conservative cleanup and editorial styling, unattended build orchestration, a local EPUB integrity/privacy gate, atomic publication, and optional systemd scheduling.

## Current design

```text
systemd timer / manual invocation
            ↓
     news-epub-build
            ↓
       ebook-convert
            ↓
      candidate EPUB
            ↓
  news-epub-validate
            ↓
 EPUBCheck (when available)
            ↓
 atomic rename into outbox
            ↓
 Syncthing / another consumer
```

Generation takes place in a private staging directory. The final filename is created only after validation. A failed candidate does not replace the last known-good edition.

## Output naming

The default filename is deliberately machine-sortable and independent of usernames, hosts, devices or home directories:

```text
news-epub_YYYY-MM-DD_morning.epub
news-epub_YYYY-MM-DD_evening.epub
news-epub_YYYY-MM-DD_night.epub
```

Change the prefix with `NEWS_EPUB_FILENAME_PREFIX`. The prefix is restricted to letters, numbers, `.`, `_` and `-` so remote metadata cannot become a path.

## Runtime requirements

- Linux with POSIX `sh`, GNU `stat`, `flock`, `find`, `mktemp` and `sync`
- Calibre 9.x with `ebook-convert`
- Python 3.11 or newer for `news-epub-validate`
- EPUBCheck 5.x strongly recommended for strict standards validation
- systemd only if the supplied service/timer integration is used

The runtime does not require a database, container, browser automation service, remote AI service, telemetry SDK, analytics service or cloud account.

## Quick trial without installing systemd

From the unpacked repository, with `ebook-convert` available on `PATH`:

```sh
chmod +x bin/news-epub-build bin/news-epub-validate
NEWS_EPUB_ROOT="$PWD/.state" \
NEWS_EPUB_RECIPE="$PWD/recipe/news-epub.recipe" \
NEWS_EPUB_VALIDATOR="$PWD/bin/news-epub-validate" \
bin/news-epub-build morning
```

A successful issue will appear under `.state/outbox/`. The command exits non-zero if conversion or a required quality gate fails.

To use a non-standard Calibre location:

```sh
NEWS_EPUB_EBOOK_CONVERT=/path/to/ebook-convert ...
```

## Configuration

`config/news-epub.conf.example` contains all supported deployment settings. The portable core derives `work/` and `outbox/` from `NEWS_EPUB_ROOT`, but each can be overridden independently.

Important settings:

- `NEWS_EPUB_TITLE`, `NEWS_EPUB_DESCRIPTION`, `NEWS_EPUB_LANGUAGE`: publication identity
- `NEWS_EPUB_FILENAME_PREFIX`: portable final-file prefix
- `NEWS_EPUB_OUTPUT_PROFILE`: optional Calibre output profile
- `NEWS_EPUB_REQUIRE_EPUBCHECK=1`: fail rather than publish when EPUBCheck is unavailable
- `NEWS_EPUB_MAX_ATTEMPTS`: conversion attempts; validation failures are intentionally not retried
- `NEWS_EPUB_MAX_UNCOMPRESSED_MIB`, `NEWS_EPUB_MAX_MEMBER_MIB`: EPUB resource-abuse ceilings
- `NEWS_EPUB_MIN_ARTICLES`: minimum parsed articles before the recipe will proceed (default `10`; Calibre test mode uses `1`)
- `NEWS_EPUB_DOWNLOAD_WORKERS`, `NEWS_EPUB_FETCH_TIMEOUT`: bounded network concurrency/timeouts
- `NEWS_EPUB_IMAGE_TARGET_WIDTH`: preferred responsive-image source width before Calibre device scaling

Invalid numeric recipe settings fail explicitly during recipe loading rather than falling back silently.

## Validation policy

`news-epub-validate` is a project-specific quality/security gate. It is not a replacement for EPUBCheck.

It rejects, among other things:

- malformed or corrupt ZIP/EPUB containers
- duplicate, encrypted, symlink or unsupported-compression archive members
- unsafe archive paths
- missing OCF/package/manifest/spine resources
- missing required EPUB 3 metadata
- missing or malformed EPUB 3 navigation semantics
- undeclared/orphan publication resources
- broken local references and fragment targets
- duplicate XHTML/SVG IDs
- scripts, forms, iframes, embedded active objects, event handlers, `xml:base` and meta refresh
- remote publication resources, remote CSS resources/imports and unsafe hyperlink schemes
- active or remote-resource SVG content
- common image media-type/signature mismatches
- EPUBs or individual archive members above configured size ceilings

Normal `http`, `https`, `mailto` and `tel` hyperlinks remain usable because following them is a reader action; resources required to render the issue must be local.

When EPUBCheck is absent and not required, the build logs a warning on every successful project-level validation. Set `NEWS_EPUB_REQUIRE_EPUBCHECK=1` for strict unattended deployment.

## Article cleanup and design

The recipe retains reader-relevant semantics such as IDs, language/direction, quotations, list numbering, table associations, captions and image alt text while removing source-site styling, scripts, forms, embeds and unsafe link schemes.

The interior uses a monochrome-first editorial system:

- serif body text and sans-serif hierarchy/metadata
- restrained rules rather than cards, shadows, gradients or pill controls
- left-aligned captions
- non-italic blockquotes for sustained e-ink readability
- semantic lists and tables
- no embedded custom fonts
- no fixed layout or fixed-position UI
- reader-controlled font sizing

Calibre's normal large-flow handling is left enabled and tables are not forcibly linearised. Image compression uses Calibre's dimension-aware default rather than a fixed per-image 96 KB ceiling.

The cover continues to use Calibre's built-in cover generator for reliability, but with a restrained monochrome preset and separate edition/date hierarchy. A custom raster cover should be introduced only after rendering is tested on the target Kindle firmware.

## Network/privacy model

All publication processing is local. The only routine outbound connections are those needed to fetch the configured feeds, article pages and their editorial assets.

The recipe rejects explicit article/image URLs targeting localhost, private, loopback, link-local, reserved or otherwise non-global IP literals, and rejects `file:`, `data:`, `blob:` and `javascript:` image sources. This reduces direct SSRF/local-file exposure from hostile feed/article markup.

This is not a complete network sandbox. DNS resolution and redirects occur inside Calibre's networking stack. If the host requires a stronger network boundary, enforce it outside this project with host firewall/network policy appropriate to the chosen publishers.

No telemetry or analytics are added by this repository.

## systemd deployment

The integration is intentionally two units:

```text
news-epub.timer
news-epub.service
```

The timer runs at 06:00, 17:30 and 22:00 in the host's local timezone. Missed calendar events are not replayed after a long outage; a stale news edition is usually less useful than waiting for the next scheduled edition.

A conventional installation is:

```sh
sudo install -m 0755 bin/news-epub-build bin/news-epub-validate /usr/local/bin/
sudo install -d -m 0755 /opt/news-epub /etc/news-epub
sudo install -m 0644 recipe/news-epub.recipe /opt/news-epub/news-epub.recipe
sudo install -m 0644 config/news-epub.conf.example /etc/news-epub/news-epub.conf
sudo install -m 0644 systemd/news-epub.service systemd/news-epub.timer /etc/systemd/system/
```

Create an unprivileged `news-epub` service account and make the configured state directory writable by that account. The supplied unit drops capabilities and enables conservative systemd hardening without binding the portable core to a particular home directory or downstream sync path.

Then:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now news-epub.timer
```

Before enabling unattended operation, run one edition manually and inspect the resulting EPUB in Calibre and on the actual target e-reader.

### Migration from the earlier three-timer layout

Disable the previous units before enabling the consolidated timer:

```sh
sudo systemctl disable --now \
  news-epub-morning.timer \
  news-epub-evening.timer \
  news-epub-night.timer
```

Remove the obsolete timer files and `news-epub@.service` after confirming the new units are installed.

## Failure semantics

- preflight/configuration errors fail before conversion
- conversion failures may retry according to configuration
- an empty converter output is a hard failure
- structural/privacy validation failures are deterministic quality failures and are not retried
- EPUBCheck failures are not retried
- the candidate is flushed before atomic rename
- work/outbox must share a filesystem
- final-directory sync failure is reported as an explicit ambiguous-publication error
- retention/stale-directory cleanup failures are warnings because they do not invalidate a successfully published issue
- `HUP`, `INT` and `TERM` abort with non-zero status and do not proceed to publication

Logs use `level=<...> stage=<...>` fields so journal output can be filtered by build stage.

## Tests

The regression suite covers the validator, build wrapper and recipe-level sanitisation/design invariants.

Standalone tests require Beautiful Soup only as a test double for Calibre's bundled soup implementation:

```sh
python -m pip install beautifulsoup4==4.14.3
python -m unittest discover -s tests -v
```

CI also checks shell syntax, Python compilation and systemd calendar/unit syntax. The GitHub Actions dependencies are pinned to immutable commit SHAs.

## Known limits before calling the system fully validated

The repository-level tests do not substitute for a real Calibre issue build. Before treating a release as deployment-ready, verify:

1. a full current issue with the installed Calibre version;
2. EPUBCheck output;
3. representative publisher extraction completeness;
4. image/caption preservation;
5. actual Kindle navigation, typography and cover rendering;
6. interruption during a real Calibre build;
7. disk-full and downstream Syncthing failure behaviour on the deployment host.

The project should prefer visible degradation or explicit failure over silently publishing an issue whose integrity is uncertain.
