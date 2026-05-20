---
layout: page
title: In Webflow
permalink: /usage/webflow/
parent: Usage
nav_order: 3
---

# Using webflow2reveal inside a Webflow page

This page is the practical, Webflow-first walkthrough: how to prepare a page in
the Webflow Designer, drop the JavaScript library into Webflow's custom-code
slots so visitors can flip the live page into slides, configure both
implementations from a single block of page code, and — when you want a static
file instead — point the Python CLI at the same published page.

If you only want the API surface, see [JavaScript]({{ '/usage/javascript/' | relative_url }})
and [Python]({{ '/usage/python/' | relative_url }}). If you want to understand
the conversion algorithm, see [How it works]({{ '/how-it-works/' | relative_url }}).

## 1. Design the page so it converts cleanly

webflow2reveal does not need special components — it reads the structure your
Webflow page already has. Each top-level `<section>` becomes one slide. To get
predictable results:

- **Build the page as a stack of full-width sections.** One section = one slide,
  in document order.
- **Set background colours via classes**, the way Webflow does by default. The
  converter resolves each section's colour from your CSS (inline and linked) and
  uses it as the slide background — it also picks readable text colour from the
  background's luminance, so a dark section gets light text automatically.
- **Use two direct children for a split slide.** A section with exactly two
  child blocks (optionally inside a `grid`/`container`/`row`/`wrap`/`bleed`
  wrapper) renders as a 50/50 two-column slide. A column containing an image
  becomes a full-bleed image cell.
- **A lone image section** (an image, no headings/paragraphs) becomes a
  full-bleed image slide.

### What gets dropped automatically

Sections whose class names contain `menu`, `nav`, `footer`, `header`, or
`banner` are treated as chrome and skipped, as are sections with `id="top"` or
`id="summary"`. So your Webflow navbar and footer normally disappear from the
deck without any configuration. The Webflow badge and common third-party widgets
(e.g. Freshworks) are hidden in slide mode too.

If something you *don't* want as a slide survives — a cookie bar, a floating CTA,
a decorative band — exclude it with a CSS selector (next section). You don't have
to restructure the Webflow page to remove it.

## 2. Add the JavaScript to your Webflow page

This is the run-time path: the published page stays a normal landing page, and a
button (or a `?reveal=1` link) turns it into a deck in the visitor's browser. No
build step, no export.

In the Webflow Designer, open **Page Settings → Custom Code** (or **Site
Settings → Custom Code** to apply site-wide) and paste this into the
**Before `</body>` tag** slot:

```html
<script src="https://cdn.jsdelivr.net/npm/webflow2revealjs@latest/dist/index.global.js"></script>
```

That single tag is enough: the library auto-wires itself on load. Pin a version
(e.g. `webflow2revealjs@1.0.10`) instead of `@latest` for a page you won't be
re-testing.

> Webflow's free Custom Code field has a character budget, but a CDN `<script>`
> tag costs only a few dozen characters, so it fits comfortably. An **Embed**
> element placed near the end of the page works equally well if you prefer to
> keep the code on the canvas.

## 3. Give visitors a way in

Once the script is on the page, there are three entry points into slide mode:

1. **A trigger element.** Add the class `w2r-trigger` to any element (a button,
   a link, a menu item) in the Designer. Clicking it converts the page in place
   and adds `?reveal=1` to the URL. The attribute `data-w2r-trigger` or the id
   `w2r-trigger` work the same way.

   ```html
   <a href="#" class="w2r-trigger">View as slides</a>
   ```

2. **A URL parameter.** Link to the page with `?reveal=1` (or `?reveal=true`)
   appended and it converts automatically on load — handy for a "Present" link
   you share directly.

3. **Programmatically**, by calling `convertToReveal()` yourself (see the
   [JavaScript API]({{ '/usage/javascript/' | relative_url }})).

A floating close button (`×`) appears in slide mode; clicking it strips the
query params and reloads the original page. Add `?view=scroll` (alongside
`reveal=1`) to open the deck as a scrolling page instead of a windowed slideshow.

## 4. Configure both implementations from one block

Both the run-time JS and the build-time Python read configuration from a
`window.webflow2revealOptions` object you define on the page. Put it in the
**Before `</body>` tag** slot *before* the library script:

```html
<script>
  window.webflow2revealOptions = {
    // CSS selectors to remove before converting (string or array)
    excludeSelectors: ['.cookie-banner', '#intercom-frame', '.floating-cta'],
  };
</script>
<script src="https://cdn.jsdelivr.net/npm/webflow2revealjs@latest/dist/index.global.js"></script>
```

The JS library passes this object straight into `convertToReveal()` on both the
`?reveal=1` auto-init path and the `.w2r-trigger` click path, so anything in
[`ConvertOptions`]({{ '/usage/javascript/' | relative_url }}#convertoptions) is
valid here — `excludeSelectors`, `revealOptions`, `corsProxy`, and the
`onBeforeInit` / `onAfterInit` callbacks.

What makes this block special is that the **Python CLI reads it too**. When you
later run `webflow2reveal` against the *published* page (next section), it scans
the page's inline scripts for `window.webflow2revealOptions` and honours these
keys at build time:

| Key                | Read by JS (runtime) | Read by Python (build time) |
| ------------------ | -------------------- | --------------------------- |
| `excludeSelectors` | ✅ removes elements before converting | ✅ removes elements before converting |
| `disableLayout`    | only via `revealOptions.disableLayout` | ✅ top-level key respected in the generated deck |
| `revealOptions`, `corsProxy`, callbacks | ✅ | ignored (build output uses fixed Reveal options) |

So `excludeSelectors` is the one setting that behaves identically whether the
deck is produced live in the browser or compiled to a file — define your
exclusions once, on the page, and both paths obey them.

> Note the `disableLayout` asymmetry: Python accepts it as a **top-level** key
> in `webflow2revealOptions`, while the JS library only reads it from
> `revealOptions` (it defaults to `true`, the "bring your own layout" mode that
> keeps Webflow's own typography). To control it in both, set both:
> `{ disableLayout: false, revealOptions: { disableLayout: false } }`.

## 5. Build a static deck from the same page (Python)

Sometimes you want a self-contained file rather than a live conversion — to
host on a different server, attach to an email, open offline, or archive a
snapshot. Point the Python CLI at the published Webflow URL:

```bash
# No install required
uvx webflow2reveal https://your-site.webflow.io/deck --output deck.html

# Preview it locally straight away
uvx webflow2reveal https://your-site.webflow.io/deck --serve --port 8080
```

The CLI fetches the page (including its linked stylesheets, to resolve
background colours), applies any `excludeSelectors` it finds in the page's
`webflow2revealOptions` block, and writes a single `index.html` with Reveal.js
inlined. You can add more exclusions for this build without touching the page:

```bash
uvx webflow2reveal https://your-site.webflow.io/deck \
  --exclude ".promo-strip, #live-chat" \
  --output deck.html
```

CLI `--exclude` selectors and page `excludeSelectors` are merged and
de-duplicated. See [Python]({{ '/usage/python/' | relative_url }}) for the full
CLI and library reference.

## Choosing a path

- **Keep it live in Webflow** (Section 2–4) when the page should stay a normal
  landing page and "present mode" is a button away. Nothing leaves Webflow.
- **Compile with Python** (Section 5) when you need a portable, dependency-free
  file. The same page, the same `excludeSelectors`, a static result.

Both run the identical normalization described in
[How it works]({{ '/how-it-works/' | relative_url }}); they differ only in
*when* the conversion happens.
