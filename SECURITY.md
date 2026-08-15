# Security and privacy

News EPUB Service treats feed metadata, article HTML, URLs, redirects and downloaded assets as untrusted input.

## Runtime guarantees provided by this repository

- no shell evaluation of feed/article metadata
- no telemetry, analytics or remote AI processing
- unprivileged systemd execution by default
- private-by-default file creation (`0027` umask)
- per-run private staging followed by same-filesystem atomic publication
- explicit rejection of active/remote resources in the finished EPUB
- bounded EPUB member and aggregate uncompressed sizes
- rejection of unsafe ZIP paths, duplicate members and ZIP symlinks
- rejection of explicit local/private IP-literal article and image URLs
- source-site scripts, forms, styles and common embedded active content removed before publication

## Boundary not claimed

The recipe does not implement a DNS/redirect sandbox around Calibre. A compromised public hostname could theoretically resolve or redirect in ways not visible to the recipe's pre-fetch URL checks. Hosts requiring stronger isolation should enforce network policy outside the application.

The project validator enforces local project invariants but does not replace EPUBCheck. Strict deployments should set `NEWS_EPUB_REQUIRE_EPUBCHECK=1`.

## Sensitive data

No secrets are required by the supplied source list. Do not add credentials to the repository or commit a populated environment file containing secrets. If future authenticated feeds are added, store credentials in a root/service-readable configuration outside the source tree and avoid including them in logs.

## Reporting

For a security defect, open a private security advisory in the repository rather than publishing exploit details in a normal issue when confidentiality is warranted.
