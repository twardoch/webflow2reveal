# Changelog

All notable changes to webflow2reveal are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project uses
git-tag-driven [semantic versioning](https://semver.org/).

## [Unreleased]

### Added

- **Python test suite** (`py/tests/test_compiler.py`): 10 unit and functional
  tests covering CSS colour parsing, slide/chrome detection, balanced-brace
  scanning, JS option extraction, and full `convert()` runs. URL conversion is
  exercised with a mocked `requests.get`, so the suite runs offline.
- **Continuous integration** (`.github/workflows/ci.yml`): ruff, mypy, and the
  test matrix (Python 3.10–3.13) on every push and pull request, plus a build +
  `twine check` job.
- **Tag-driven release** (`.github/workflows/release.yml`): builds, smoke-tests
  the wheel's CLI, publishes to PyPI via trusted publishing, and cuts a GitHub
  release on any `v*` tag.
- `dev` dependency group (pytest, ruff, mypy, types-requests) and `[project.urls]`.

### Changed

- **Type hints** added to every function in `compiler.py`, including the
  `str | None` return of `get_section_bg_color` and `find_balanced_braces`.
- **Comments** on the section-detection heuristics explaining which classes
  count as slides versus page chrome, and why colour resolution walks the class
  list in reverse.
- Tooling config in `pyproject.toml`: ruff (lint), mypy, and pytest.
- `.gitignore` now excludes OMC state (`.omc/`) and the local vector-store
  artifact (`ruvector.db`).

### Fixed

- Removed a redundant `import re` nested inside the luminance branch of
  `convert()`.

## Earlier

See the git tag history (`v1.0.0` … `v1.0.19`) for the Webflow-to-Reveal.js
conversion engine, background-colour inference, split-layout normalisation, and
the companion `webflow2revealjs` npm runtime.
