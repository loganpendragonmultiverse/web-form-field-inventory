# Development contract

Inspect saved HTML for fields, labels, validation, accessibility, and submission targets.

Preserve deterministic, source-safe behavior and the interpretation boundary documented in the README. Every feature release must update tests, version metadata, changelog, README claims, repository metadata, release assets, and the Forge catalog together.

## 1.1.0 improvement session

Resolve supported static accessible-name patterns, external form associations and source locations; compare saved HTML forms.

The inventory recognizes wrapping and explicit labels, button text, aria-label, aria-labelledby and controls associated through the form attribute. Input controls default to text, and reports include line/column positions and validation constraints. Add `baseline_html` containing the previous saved HTML to receive added, removed and changed form/field records, including actions and methods. Comparison identities use form ID plus field ID/name and ordinal, so reordered anonymous controls may appear changed. This is static HTML analysis: CSS visibility, scripts, shadow DOM and the browser accessibility tree are not evaluated. No form is submitted.

Local formatting, lint, strict types and regression tests pass. Public release completion requires the protected CI/CodeQL matrix, tagged artifacts and matching Forge catalog/detail deployment.

## Static submission variants

Set `include_submissions` to `true` in the JSON input to add a `submissions`
list to each form. Each row identifies one enabled submit button or image input,
its effective action and method, and its source field ordinal, ID and name.
`formaction` and `formmethod` override form defaults. Methods use HTML defaults:
invalid values become `get`; `dialog` describes a dialog action, not a network request.
External controls with a matching `form` ID participate in source order.
Disabled controls and disabled fieldset descendants are omitted, except controls
in that fieldset's first legend.

Supply `document_url` to resolve relative actions, including the first static
`base href`. An empty action uses the document URL. Without a document URL,
relative actions remain relative. No URL is fetched or validated as reachable.
Named submitters report their static value; unnamed buttons add no name/value.
Image submitters expose coordinate names (`name.x`/`name.y` or `x`/`y`),
without inventing click coordinates.

`baseline_html` uses the same options, so form comparison records include
effective submission changes. Default reports and comparisons remain unchanged.
These are individual explicit submit-control variants, not simulated requests:
implicit Enter submission, scripts, runtime values, browser parsing corrections,
CSS state, and successful submission are outside this static analysis.

```bash
form-inventory examples/submissions.json --format json
```
