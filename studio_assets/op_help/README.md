# Operator help (HTML)

Fullseye Studio's **Operators** panel renders per-operator help as HTML, so you can
include rich image-processing explanations, formatting, tables and (data-URI or
local) images. HTML files here are loaded at runtime — no code change needed.

## File lookup order (for op `<name>` in language `<lang>`)

1. `op_help/<name>.<lang>.html`  — language-specific help (e.g. `gaussian.ja.html`)
2. `op_help/<name>.html`         — default (English) help
3. a **generated** fallback built from the operator's registry metadata
   (name, category, input→output sorts, HALCON alias) when no file exists.

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
