# TODO

Bigger ideas, parked for later. The scaffolding, tests, types, and CI landed in
this pass (see `CHANGELOG.md`); what remains is depth.

## Docs

- [ ] Promote `docs/` to MaterialX (MkDocs + Material) at
      `code.twardoch.com/webflow2reveal/`: Webflow export requirements, section
      class naming conventions, slide-layout inference, background-colour
      detection, demo gallery, Python CLI reference, JS integration guide.
- [ ] Add a `docs.yml` workflow to build and publish the docs site.

## Python

- [ ] Add a CSP-compatibility note for the injected inline `<style>`/`<script>`
      (the runtime relies on inline blocks and a CDN reveal.js).
- [ ] Make the reveal.js version a single named constant instead of repeating
      the `5.1.0` CDN URL in two places.
- [ ] Harden CSS class detection against Webflow renaming conventions — the
      `menu`/`nav`/`footer` substring match is fragile; consider a configurable
      chrome-selector list.
- [ ] Consider structured logging (or `--verbose`) instead of bare `print`.

## JavaScript

- [ ] Add JS unit tests for the `webflow2revealjs` runtime.
- [ ] Version-lock `webflow2revealjs` (npm) with the Python package release.
- [ ] Confirm the npm package is published and current.

## Tests

- [ ] Add fixtures for split-layout, badge/card, and image-cover slides.
- [ ] Add a test for external-stylesheet colour resolution (mocked fetch).
