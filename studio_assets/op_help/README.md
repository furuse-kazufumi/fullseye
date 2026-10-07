# Operator help (HTML)

Fullseye Studio's **Operators** panel renders per-operator help as HTML, so you can
include rich image-processing explanations, formatting, tables and (data-URI or
local) images. HTML files here are loaded at runtime — no code change needed.

## File lookup order (for op `<name>` in language `<lang>`)

1. `op_help/<name>.<lang>.html`  — language-specific help (e.g. `threshold.en.html`)
2. `op_help/<name>.html`         — the base page. **For generated pages this is Japanese**
   (converted from the `docs/ops/**/<op>.md` note, which copies the docstring verbatim).
   Only the three hand-authored pages (`gaussian`, `otsu`, `sobel_mag`) are English, and
   they deliberately have no `<lang>` siblings (a generated translation would replace a
   richer page that carries runnable `sample:` pipelines).
3. a **generated** fallback built from the operator's registry metadata
   (name, category, input→output sorts, HALCON alias) when no file exists.

Non-2-D operators use the same order under `op_help/<dim>/` (3-D and every ledger family).

So you only need to author HTML for the operators you want to document; every other
operator still shows a useful auto-generated card. Adding a new UI language (see
`../i18n.json`) automatically enables `<name>.<lang>.html` overrides for that language.

## Authoring notes

- Qt's `QTextBrowser` renders a rich-text subset of HTML/CSS (inline styles work
  well; flexbox/grid do not). Keep styling inline and simple.
- Images: use a `<img src="...">` with an absolute local path or a `data:` URI.
- Keep the palette consistent with the app: amber `#f5a524` headings, teal
  `#17b8a6` sub-headings, muted `#8b91a0` metadata.

Examples in this folder: `gaussian.html`, `sobel_mag.html`, `otsu.html`.

## Language coverage — frame vs. content (measured, not claimed)

Every generated page ships in 6 languages (ja, en, zh, tw, ko, de), but "ships" covers two
different things:

- **Frame** — headings, labels, buttons, figure captions, the fail-closed contract
  boxes. These come from `docs/i18n/opdocs.json` and are complete in all 6 languages.
- **Content** — the operator's own docstring. Only the summary (first paragraph) has a
  translation table (`docs/i18n/op_summary.json`); the rest of the docstring is shown in
  its original language with a one-line notice saying so.

Measured on 2026-10-07 (3,086 generated pages per language): the summary is translated on
63.7 % of the English pages and 60.7 % of the zh / tw / ko / de pages; 2,439 pages per
language (79 %) still contain Japanese prose somewhere in the body. The live numbers are in
`docs/i18n/help_coverage.json`, written by `py -3.11 tools/opdocs.py coverage` (also part of
`all`); `tests/test_help_rendering.py` fails if a language's translated share goes down or
the number of untranslated summaries goes up.
