# Web Form Field Inventory

[![CI](https://github.com/loganpendragonmultiverse/web-form-field-inventory/actions/workflows/ci.yml/badge.svg)](https://github.com/loganpendragonmultiverse/web-form-field-inventory/actions/workflows/ci.yml)

Inspect saved HTML for fields, labels, validation, accessibility, and submission targets. The command uses explicit UTF-8 JSON input and produces reviewable JSON or Markdown output.

## Three-minute start

```bash
python -m pip install .
form-inventory examples/sample.json
form-inventory examples/sample.json --format json --output report.json
```

The example documents the v1 input shape. Existing report files are never overwritten. Source inputs are read-only except where the documented purpose explicitly creates a new output artifact.

## Privacy and platforms

The tool runs locally and does not upload input or include telemetry. Python 3.10 or newer is supported on Windows, macOS, and Linux.

## Interpretation boundary

Static HTML inspection cannot observe JavaScript-created fields, runtime validation, server behavior, or successful submission.

## Development

```bash
python -m pip install -e ".[dev]"
ruff format --check .
ruff check .
mypy src
pytest
python -m build
```

The project is feature-complete for its documented v1 scope. Maintenance focuses on correctness, security, compatibility, and well-supported input improvements.

Part of the [Logan Pendragon Forge open-source collection](https://www.loganpendragonforge.com/open-source/). Licensed under the [MIT License](LICENSE).
