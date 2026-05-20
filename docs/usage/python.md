---
layout: page
title: Python
permalink: /usage/python/
parent: Usage
nav_order: 1
---

# Python — `webflow2reveal`

A build-time converter. It reads a Webflow page from a URL or a local file,
resolves background colours from inline and linked stylesheets, normalizes the
slide DOM, injects Reveal.js 5.1, and writes a single self-contained
`index.html`. Optionally it serves the result on a local dev server.

## Install

```bash
# Run without installing
uvx webflow2reveal https://example.webflow.io/deck --output index.html

# Or install into a project
uv pip install webflow2reveal
```

The package depends on `beautifulsoup4`, `requests`, and `fire`.

## CLI

The CLI is a [Fire](https://github.com/google/python-fire) wrapper over the
`convert` function, so every parameter is a flag:

```bash
webflow2reveal <source> [--output index.html] [--serve] [--port 8000] [--exclude "<selectors>"]
```

| Argument / flag | Default       | Notes                                                                |
| --------------- | ------------- | -------------------------------------------------------------------- |
| `source`        | —             | `http(s)://` URL **or** a local HTML file path of the Webflow page.  |
| `--output`      | `index.html`  | Output file for the generated deck. Parent dirs are created.         |
| `--serve`       | `False`       | After writing, start a local `http.server` in the output directory.  |
| `--port`        | `8000`        | Port for the dev server (only with `--serve`).                       |
| `--exclude`     | `None`        | Comma-separated CSS selectors whose matching elements are removed before conversion. |

When `source` is a URL, linked stylesheets are fetched (with a 5 s timeout) so
their background colours can be resolved; when it is a local file, stylesheet
paths are resolved relative to that file's directory.

### Excluding elements

`--exclude` drops elements that survive the automatic chrome filtering — a
cookie bar, a floating CTA, a live-chat widget — by CSS selector:

```bash
webflow2reveal https://example.webflow.io/deck --exclude ".cookie-banner, #intercom-frame"
```

The converter also reads exclusions defined **on the page itself**: if the
Webflow page sets `window.webflow2revealOptions = { excludeSelectors: [...] }`
in an inline (or `*reveal_config*`) script, those selectors are scraped at build
time and merged with `--exclude` (duplicates removed). The same block can set a
top-level `disableLayout: false` to opt the generated deck out of the default
"bring your own layout" mode. See
[In Webflow]({{ '/usage/webflow/' | relative_url }}#4-configure-both-implementations-from-one-block)
for the shared-configuration workflow.

### Examples

```bash
# Convert a hosted Webflow page to a static deck
webflow2reveal https://example.webflow.io/pitch --output dist/pitch.html

# Convert a local export and preview it immediately
webflow2reveal ./export/index.html --serve --port 8080
# → http://localhost:8080/

# Convert and write next to the source
webflow2reveal page.html
```

## Library

```python
from webflow2reveal import convert

# Write a static deck
convert("https://example.webflow.io/deck", output="index.html")

# Convert a local file and serve it
convert("export/index.html", output="dist/index.html", serve=True, port=8080)

# Drop extra elements by selector
convert("https://example.webflow.io/deck", exclude=".cookie-banner, #live-chat")
```

`convert(source, output="index.html", serve=False, port=8000, exclude=None)`
performs the fetch/read, conversion, and (optionally) the blocking dev-server
loop. It prints progress to stdout and exits non-zero if the source URL or file
cannot be read. `exclude` takes a comma-separated string of CSS selectors and is
merged with any `excludeSelectors` declared in the page's
`window.webflow2revealOptions`.

## Viewing the result

Open the generated `index.html` in any browser. Append `?view=scroll` to switch
from the full-screen slideshow into Reveal.js's native scroll view of the same
content.

## How conversion works

See [How it works]({{ '/how-it-works/' | relative_url }}) for the shared
DOM-normalization and colour-resolution algorithm.
