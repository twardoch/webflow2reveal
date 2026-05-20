---
layout: page
title: JavaScript
permalink: /usage/javascript/
parent: Usage
nav_order: 2
---

# JavaScript — `webflow2revealjs`

A run-time, browser-side converter. Add one script to a Webflow page and the
library can transform the live DOM into a Reveal.js deck in place — no build
step, no server. It can also fetch and convert a different page, or convert raw
HTML you hand it.

## Install

```bash
npm install webflow2revealjs
```

Or load the prebuilt global bundle straight from a CDN — the simplest path for a
Webflow **Page Custom Code** block:

```html
<!-- before the closing </body> tag -->
<script src="https://cdn.jsdelivr.net/npm/webflow2revealjs@latest/dist/index.global.js"></script>
```

The package ships CJS (`dist/index.js`), ESM (`dist/index.mjs`), an IIFE global
(`dist/index.global.js`, exposed as `Webflow2Reveal`), and type definitions.

## Trigger it

Once the script is on the page, there are three ways to enter slide mode:

1. **A button** — give any element the class `w2r-trigger` (or the attribute
   `data-w2r-trigger`, or id `w2r-trigger`). Clicking it converts in place and
   pushes `?reveal=1` to the URL.
2. **A URL parameter** — load the page with `?reveal=1` (or `?reveal=true`) and
   it auto-converts on load.
3. **Programmatically** — call `convertToReveal(options)` yourself.

A floating close button (`×`) is added in place-conversion mode; it strips the
`reveal`/`view` params and reloads the original page.

```html
<a href="#" class="w2r-trigger">View as Slides</a>
```

## Programmatic API

```ts
import { convertToReveal } from 'webflow2revealjs';

// Convert the current page in place
await convertToReveal();

// Convert a remote page (needs a CORS proxy for cross-origin assets)
await convertToReveal({
  sourceUrl: 'https://example.webflow.io/deck',
  corsProxy: 'https://api.allorigins.win/raw?url=',
});

// Convert raw HTML into a target element
await convertToReveal({
  htmlContent: myHtmlString,
  targetElement: document.getElementById('stage')!,
});
```

### `ConvertOptions`

| Option          | Type                          | Notes                                                                                  |
| --------------- | ----------------------------- | -------------------------------------------------------------------------------------- |
| `sourceUrl`     | `string`                      | Page to fetch and convert. Omit (with no `htmlContent`) to convert the current page.   |
| `htmlContent`   | `string`                      | Raw HTML to convert. Skips fetching `sourceUrl`.                                        |
| `corsProxy`     | `string`                      | Prefix used to fetch cross-origin pages/stylesheets, e.g. `https://api.allorigins.win/raw?url=`. |
| `targetElement` | `HTMLElement`                 | Mount point. Defaults to `document.body` (in-place mode).                              |
| `excludeSelectors` | `string[] \| string`       | Selector(s) whose matching elements are removed before converting. A string may be comma-separated. |
| `revealOptions` | `Record<string, any>`         | Merged over the defaults and passed to `Reveal.initialize`.                            |
| `onBeforeInit`  | `() => void`                  | Called just before `Reveal.initialize`.                                                |
| `onAfterInit`   | `() => void`                  | Called after Reveal finishes initializing.                                            |

To preconfigure the auto-init (`?reveal=1`) path and the `.w2r-trigger` click
path, set `window.webflow2revealOptions` before the script runs — that object is
passed verbatim to `convertToReveal`. This is the recommended way to configure
the library on a Webflow page; see
[In Webflow]({{ '/usage/webflow/' | relative_url }}) for the full workflow,
including how the Python build-time tool reads the same block.

### Default Reveal options

`width: 1440`, `height: 900`, `margin: 0`, `center: false`, `minScale: 0.2`,
`maxScale: 2.0`, `hash: true`, `transition: 'slide'`,
`backgroundTransition: 'slide'`, and `disableLayout: true`. Anything in
`revealOptions` overrides these.

`disableLayout: true` is the **bring-your-own-layout (BYOL)** mode: Reveal skips
its own scaling/centering math and the deck keeps Webflow's typography and
spacing, with webflow2reveal's stylesheet sizing each slide to the stage. To let
Reveal take over layout instead, pass `revealOptions: { disableLayout: false }`.

## In-place vs. fetched conversion

- **In place** (no `sourceUrl`/`htmlContent`): the live `document` is used, so
  there are no CORS issues — local stylesheets are read directly from
  `document.styleSheets`, the original sections are cloned into the Reveal
  scaffold, and the page's other top-level content is hidden behind a close
  button.
- **Fetched / raw HTML**: the markup is parsed with `DOMParser`; cross-origin
  stylesheets are fetched through `corsProxy` when supplied.

## Scroll view

As with the Python output, appending `?view=scroll` initializes Reveal in its
native scroll view instead of the windowed slideshow.

## How conversion works

See [How it works]({{ '/how-it-works/' | relative_url }}) for the shared
DOM-normalization and colour-resolution algorithm.
