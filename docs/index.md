---
layout: page
title: webflow2reveal
description: Turn a sectioned Webflow page into a Reveal.js slide deck — a Python CLI and a browser-side JavaScript library sharing one approach.
permalink: /
has_toc: false
---

<link rel="stylesheet" href="{{ '/assets/css/webflow2reveal.css' | relative_url }}">

<section class="w2r-hero">
  <p class="w2r-hero__lede">
    <strong>webflow2reveal</strong> turns a structured, sectioned Webflow page
    into an interactive <a href="https://revealjs.com">Reveal.js</a> slide deck.
    It reads your existing <code>&lt;section&gt;</code> elements, infers slide
    layouts and background colours from the page's own CSS, and wraps everything
    in a Reveal scaffold — no manual slide authoring.
  </p>
</section>

## What it does

```text
Webflow page  →  parse CSS bg-colours  →  pick slide <section>s  →
                 normalize DOM (split / image / text / badge layouts)  →
                 score luminance (light/dark)  →  inject Reveal.js 5.1  →
                 static index.html  /  in-place browser deck
```

A Webflow export is already a stack of full-width `<section>`s with consistent
class names. webflow2reveal treats each qualifying section as one slide, throws
away chrome (nav, footer, menu, banner), and rebuilds the inner markup into a
predictable structure (`slide-section`, `slide-split-layout`, `slide-column`,
`slide-text-container`, `slide-image-cover`, `slide-badge`) that a single
bundled stylesheet then sizes to a 1440×900 stage.

Background colours are not guessed at random — they are resolved from the
page's own inline and linked stylesheets, then each slide is classified
`slide-light-bg` or `slide-dark-bg` by perceptual luminance so text contrast
stays correct.

## Pick your implementation

- [Python]({{ '/usage/python/' | relative_url }}) — build-time. Fetches a URL
  or reads a local HTML file, writes a self-contained `index.html`, optionally
  serves it. Install-free via `uvx webflow2reveal`.
- [JavaScript]({{ '/usage/javascript/' | relative_url }}) — run-time, in the
  browser. Drop one `<script>` into a Webflow page and a `?reveal=1` URL or a
  `.w2r-trigger` button transforms the live page into slides in place.

Both share the same normalization algorithm. The difference is *when* it runs:
once at build time (Python) versus on demand in the visitor's browser (JS).

## Two ways to present the same deck

Every generated deck understands a `?view=scroll` query parameter that switches
Reveal.js into its native scroll view — the same content reads either as a
classic full-screen slideshow or as a vertically scrolling page.

## Try it

The [interactive demo]({{ '/demo/' | relative_url }}) is an ordinary landing
page. Click **View as Slides** (or append `?reveal=1`) and the JavaScript
library converts it to a Reveal deck in place, with a close button to return.

## License

MIT. See the [GitHub repo](https://github.com/twardoch/webflow2reveal).
