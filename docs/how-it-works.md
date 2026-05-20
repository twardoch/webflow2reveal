---
layout: page
title: How it works
permalink: /how-it-works/
nav_order: 3
---

# How it works

Both implementations run the same pipeline. The Python version
([`compiler.py`](https://github.com/twardoch/webflow2reveal/blob/main/py/src/webflow2reveal/compiler.py))
uses BeautifulSoup at build time; the JavaScript version
([`index.ts`](https://github.com/twardoch/webflow2reveal/blob/main/js/src/index.ts))
uses the DOM at run time. The steps below are intentionally described once, in
terms both share.

## 1. Resolve background colours

Webflow paints slide backgrounds via CSS classes, not inline attributes. The
converter builds a `class → colour` map by scanning:

- every inline `<style>` block, and
- every linked stylesheet (fetched over the network when the source is remote,
  read from disk when local; the JS in-place path reads `document.styleSheets`
  directly to dodge CORS).

A lightweight CSS parser pulls `background-color` (and solid `background`)
declarations and records the colour against each class selector it applies to.
Nested blocks such as media queries are descended into. Transparent and
zero-alpha values are ignored.

## 2. Select slide sections

Every `<section>` is a slide candidate. A section is **rejected** when its
classes contain `menu`, `nav`, `footer`, `header`, or `banner`; when its `id` is
`top` or `summary`; or when it contains a `vexy-menu` / `vexy-footer` web
component. Everything else becomes a slide and gets the `slide-section` class.

## 3. Find or build the Reveal scaffold

If the page already contains `div.reveal > div.slides`, those sections are used
as-is. Otherwise the selected sections are extracted and re-wrapped in a freshly
created `div.reveal > div.slides` scaffold appended to the body.

## 4. Normalize each slide's DOM

For every slide section the converter infers a layout and rewrites the inner
markup into a small, predictable vocabulary the bundled stylesheet understands:

- **Badge / card overlay** — a single `card`/`badge` element becomes
  `slide-badge`; any images become `slide-image-cover` inside a
  `slide-image-container`.
- **Split (two-column) layout** — exactly two layout children (optionally inside
  a `grid`/`container`/`row`/`wrap`/`bleed` wrapper) become a
  `slide-split-layout` of two `slide-column`s. A column with an image is treated
  as an image cell; a text column has its content wrapped in a
  `slide-text-container`. Per-column background colours are propagated inline.
- **Single image** — a section with an image and no headings/paragraphs becomes
  a full-bleed `slide-image-cover`.
- **Single text block** — otherwise the section's content is wrapped in a
  `slide-text-container` (reusing an existing `hero-wrap`/`container`/`front`
  wrapper when present).

Mask, video-wrapper, and script/style nodes are deliberately left in place
rather than wrapped.

## 5. Resolve and classify backgrounds

Each section's background colour is the most specific non-transparent colour
among its classes (resolved against the map from step 1) and is written to
`data-background-color` — the attribute Reveal.js uses to paint slide
backgrounds. The colour's perceptual luminance (`0.299·R + 0.587·G + 0.114·B`)
then tags the slide `slide-light-bg` (luminance > 0.6) or `slide-dark-bg`, which
drives automatic text-contrast overrides. Hex, `rgb()`, and a few named colours
are understood.

## 6. Inject Reveal.js and styles

The converter appends the Reveal.js 5.1.0 stylesheet and script from cdnjs, plus
a large bundled CSS override that:

- pins each slide to the full stage and removes Webflow's responsive margins;
- lays out split slides as a 1fr/1fr grid and stretches image cells to cover;
- vertically anchors text containers (a 4:6 flex split places text ~40% down);
- fixes a typographic scale (h1 100px, h2 72px, body 26px, …) sized for a
  1440×900 stage; and
- hides Webflow chrome and third-party widgets (the Webflow badge, Freshworks,
  `vexy-menu`/`vexy-footer`).

It then initializes Reveal with `width: 1440`, `height: 900`, `margin: 0`,
`center: false`, `minScale: 0.2`, `maxScale: 2.0`, `hash: true`, and slide
transitions.

## 7. Scroll view

A `?view=scroll` query parameter initializes Reveal in its native scroll view
and toggles `reveal-scroll-active` on `<html>`/`<body>` so the same deck reads as
a scrolling page instead of a windowed slideshow.

## Where the two implementations differ

| Aspect                 | Python (`webflow2reveal`)            | JavaScript (`webflow2revealjs`)               |
| ---------------------- | ------------------------------------ | --------------------------------------------- |
| When it runs           | Build time                           | Run time, in the browser                      |
| Input                  | URL or local HTML file               | Live page, fetched URL, or raw HTML string    |
| Output                 | Static `index.html` (+ optional dev server) | In-place DOM transform or mount into an element |
| Cross-origin CSS       | Fetched server-side                  | `document.styleSheets` in place, or `corsProxy` |
| Reveal options         | Fixed                                | Overridable via `revealOptions`               |
| Extras                 | Dev server (`--serve`)               | Close button, `.w2r-trigger`, `?reveal=1` auto-init |

## A note on theme-specific styles

The bundled stylesheet carries a set of `kapr-*` and `vexy-*` rules tuned for
the author's own Webflow theme (card palettes, column contrast, hidden chrome).
They are harmless on other pages — unmatched selectors simply do nothing — but
they are the part most worth editing when adapting the converter to a different
Webflow design system.
