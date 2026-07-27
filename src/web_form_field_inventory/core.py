from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

PROJECT = "web-form-field-inventory"


def _require(data: dict[str, Any], key: str) -> Any:
    value = data.get(key)
    if value is None or value == "" or value == []:
        raise ValueError(f"{key} is required")
    return value


class _FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, Any]] = []
        self.current: dict[str, Any] | None = None
        self.labels: dict[str, str] = {}
        self.label_for: str | None = None
        self.label_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "form":
            self.current = {
                "action": values.get("action", ""),
                "method": (values.get("method") or "get").lower(),
                "fields": [],
            }
            self.forms.append(self.current)
        elif tag == "label":
            self.label_for, self.label_text = (values.get("for"), [])
        elif tag in {"input", "select", "textarea", "button"} and self.current is not None:
            self.current["fields"].append(
                {
                    "tag": tag,
                    "type": values.get("type", tag),
                    "name": values.get("name"),
                    "id": values.get("id"),
                    "required": "required" in values,
                    "pattern": values.get("pattern"),
                    "autocomplete": values.get("autocomplete"),
                    "aria_label": values.get("aria-label"),
                    "label": None,
                }
            )

    def handle_data(self, data: str) -> None:
        if self.label_for is not None:
            self.label_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "label" and self.label_for is not None:
            self.labels[self.label_for] = " ".join("".join(self.label_text).split())
            self.label_for, self.label_text = (None, [])
        elif tag == "form":
            self.current = None


def _form_inventory(data: dict[str, Any]) -> dict[str, Any]:
    html = str(data.get("html", ""))
    if data.get("path"):
        html = Path(data["path"]).read_text(encoding="utf-8")
    if not html:
        raise ValueError("html or path is required")
    parser = _FormParser()
    parser.feed(html)
    issues = []
    for form_index, form in enumerate(parser.forms, 1):
        for field in form["fields"]:
            field["label"] = parser.labels.get(field["id"] or "") or field["aria_label"]
            if field["type"] != "hidden" and (not field["label"]):
                issues.append(
                    {
                        "form": form_index,
                        "field": field["name"] or field["id"] or "unnamed",
                        "issue": "missing accessible label",
                    }
                )
            if not field["name"] and field["tag"] != "button":
                issues.append(
                    {
                        "form": form_index,
                        "field": field["id"] or "unnamed",
                        "issue": "missing submission name",
                    }
                )
    return {
        "forms": parser.forms,
        "form_count": len(parser.forms),
        "field_count": sum(len(form["fields"]) for form in parser.forms),
        "issues": issues,
    }


def analyze(data: dict[str, Any]) -> dict[str, Any]:
    return {"version": 1, "project": PROJECT, **_form_inventory(data)}


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [f"# {report['project'].replace('-', ' ').title()} report", ""]
    for key, value in report.items():
        if key not in {"version", "project"}:
            lines.extend(
                [
                    f"## {key.replace('_', ' ').title()}",
                    "",
                    f"```json\n{json.dumps(value, indent=2, ensure_ascii=False, default=str)}\n```",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"
