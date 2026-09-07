# Development contract

Inspect saved HTML for fields, labels, validation, accessibility, and submission targets.

Preserve deterministic, source-safe behavior and the interpretation boundary documented in the README. Every feature release must update tests, version metadata, changelog, README claims, repository metadata, release assets, and the Forge catalog together.

## 1.1.0 improvement session

Resolve supported static accessible-name patterns, external form associations and source locations; compare saved HTML forms.

The inventory recognizes wrapping and explicit labels, button text, aria-label, aria-labelledby and controls associated through the form attribute. Input controls default to text, and reports include line/column positions and validation constraints. Add `baseline_html` containing the previous saved HTML to receive added, removed and changed form/field records, including actions and methods. Comparison identities use form ID plus field ID/name and ordinal, so reordered anonymous controls may appear changed. This is static HTML analysis: CSS visibility, scripts, shadow DOM and the browser accessibility tree are not evaluated. No form is submitted.

Local formatting, lint, strict types and regression tests pass. Public release completion requires the protected CI/CodeQL matrix, tagged artifacts and matching Forge catalog/detail deployment.
