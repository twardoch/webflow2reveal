# webflow2reveal

Turn a structured, sectioned **Webflow** page into an interactive
**[Reveal.js](https://revealjs.com)** slide deck — without authoring slides by
hand.

A Webflow export is already a stack of full-width `<section>`s with consistent
class names. webflow2reveal treats each qualifying section as one slide, infers
the slide layout and background colour from the page's own CSS, discards chrome
(nav, footer, menu, banner), and wraps everything in a Reveal scaffold sized for
a 1440×900 stage.

It ships as **two implementations that share one approach**:

| | Package | Runs | Input → Output |
|---|---|---|---|
| **Python** | [`webflow2reveal`](https://pypi.org/project/webflow2reveal/) (PyPI) | Build time | URL / local HTML → static `index.html` |
| **JavaScript** | [`webflow2revealjs`](https://www.npmjs.com/package/webflow2revealjs) (npm) | Run time, in browser | Live page / fetched URL / raw HTML → in-place deck |

📖 **Full documentation: <https://code.twardoch.com/webflow2reveal/>** ·
🖥️ **[Live demo](https://code.twardoch.com/webflow2reveal/demo/)**

## Quick start

### Python (build a static deck)

```bash
# Convert a hosted Webflow page (no install needed)
uvx webflow2reveal https://example.webflow.io/deck --output index.html

# Convert a local export and preview it on a dev server
uvx webflow2reveal ./export/index.html --serve --port 8080
```

```python
from webflow2reveal import convert
convert("https://example.webflow.io/deck", output="index.html")
```

### JavaScript (convert in the browser)

Add one script to a Webflow **Page Custom Code** block before `</body>`:

```html
<script src="https://cdn.jsdelivr.net/npm/webflow2revealjs@latest/dist/index.global.js"></script>
<a href="#" class="w2r-trigger">View as Slides</a>
```

Clicking a `.w2r-trigger` element — or loading the page with `?reveal=1` —
converts the live page to slides in place. Or call it yourself:

```ts
import { convertToReveal } from 'webflow2revealjs';
await convertToReveal();                       // current page, in place
await convertToReveal({ sourceUrl, corsProxy }); // fetch and convert another page
```

## How it works

```text
Webflow page  →  parse CSS bg-colours  →  pick slide <section>s  →
                 normalize DOM (split / image / text / badge layouts)  →
                 score luminance (light/dark)  →  inject Reveal.js 5.1  →
                 static index.html  /  in-place browser deck
```

1. **Resolve colours** — scan inline and linked stylesheets into a
   `class → background-colour` map.
2. **Select slides** — every `<section>` becomes a slide unless its classes/id
   mark it as nav, footer, menu, header, or banner.
3. **Normalize the DOM** — rewrite each slide into a small layout vocabulary
   (`slide-split-layout`, `slide-column`, `slide-text-container`,
   `slide-image-cover`, `slide-badge`).
4. **Classify backgrounds** — set `data-background-color` and tag each slide
   `slide-light-bg`/`slide-dark-bg` by perceptual luminance for correct text
   contrast.
5. **Inject Reveal.js 5.1** plus a bundled stylesheet that sizes everything to
   the stage and hides Webflow chrome.

Add `?view=scroll` to any generated deck to switch into Reveal's native scroll
view. See [How it works](https://code.twardoch.com/webflow2reveal/how-it-works/)
for the full algorithm.

## Repository layout

```
py/src/webflow2reveal/   Python package (compiler.py = the converter)
js/src/index.ts          TypeScript library (convertToReveal + DOM helpers)
docs/                    Jekyll site (just-the-docs) + live demo under docs/demo/
build.sh                 Build JS bundle + Python wheel; copy bundle into docs/demo
publish.sh               Tag, build, and publish to PyPI + npm
dev_server.py            Local CORS-proxying dev server for testing fetched pages
```

## Build & publish

```bash
./build.sh     # builds js/dist/* and dist/*.whl, copies bundle to docs/demo/dist/
./publish.sh   # version-tags, rebuilds, publishes to PyPI and npm
```

The JS build emits CJS, ESM, and an IIFE global (`Webflow2Reveal`) via `tsup`.
The Python package versions from git tags via `hatch-vcs`; a single tag releases
both packages.

## License

MIT © Adam Twardoch.

---

