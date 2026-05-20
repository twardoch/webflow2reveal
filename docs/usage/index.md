---
layout: page
title: Usage
permalink: /usage/
nav_order: 2
has_toc: true
has_children: true
---

# Usage

Pick where the conversion should run:

- [Python]({{ '/usage/python/' | relative_url }}) — at build time, producing a
  static `index.html`.
- [JavaScript]({{ '/usage/javascript/' | relative_url }}) — at run time, in the
  visitor's browser.

Both implementations apply the same DOM normalization and CSS injection
described in [How it works]({{ '/how-it-works/' | relative_url }}); they differ
only in when and where they execute.

New to it, or working straight from the Webflow Designer? Start with
[In Webflow]({{ '/usage/webflow/' | relative_url }}) — a task-oriented guide that
covers preparing the page, embedding the JS via Webflow's custom-code slots,
configuring both implementations from one block, and compiling a static deck
with Python.
