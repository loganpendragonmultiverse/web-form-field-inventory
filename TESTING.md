# Testing

Run `ruff format --check .`, `ruff check .`, `mypy src`, `pytest`, and `python -m build`. CI runs the supported OS/Python matrix; the runtime has no third-party dependencies.

## 1.1.0 regression acceptance

Run the complete existing suite plus the new regression fixtures. Confirm the documented command produces the selected output, malformed input remains actionable, and source files remain unchanged. Resolve supported static accessible-name patterns, external form associations and source locations; compare saved HTML forms.

## Submission variant acceptance

Run the full suite, including synthetic HTML for external controls, multiple
submitters, disabled fieldsets and first legends, unnamed and image controls,
relative/base actions (including empty or absent first href attributes), irrelevant
select/textarea type attributes, method defaults and structural baseline changes.
No test executes HTML or sends a form. Verify both README examples from an
installed wheel and an extracted source distribution.

## 1.2.1 static inventory completion

External controls and submission ordinals follow source order. Duplicate IDs and
attributes use the first source occurrence for association; colliding comparison
keys receive explicit source ordinals so no form or field silently replaces another.
Input/button types use case-insensitive HTML defaults, while select/textarea type
attributes do not change element kind. These remain static evidence, not a browser
accessibility tree or a submitted request.

Reads are bounded: JSON input 12 MB, each HTML input 5 MB, 20,000 elements, 200 nesting
levels, 2,000 controls, 100 aria-labelledby references and 10,000 characters per
resolved label. Exceeding a limit fails clearly rather than returning a partial
success. Existing output files and symlinks are refused before exclusive creation;
a regular file appearing during creation is preserved. Hostile concurrent filesystem
changes are outside this accidental-overwrite protection. Run both installed examples
and the full format/lint/type/coverage/build matrix before release.
