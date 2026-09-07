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
        self.stack: list[dict[str, Any]] = []
        self.nodes: list[dict[str, Any]] = []
        self.controls: list[tuple[dict[str, Any], dict[str, Any]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        node: dict[str, Any] = {
            "tag": tag,
            "attrs": values,
            "text": [],
            "parents": self.stack.copy(),
        }
        self.nodes.append(node)
        if tag not in {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }:
            self.stack.append(node)
        if tag == "form":
            self.current = {
                "id": values.get("id"),
                "action": values.get("action", ""),
                "method": (values.get("method") or "get").lower(),
                "fields": [],
            }
            self.forms.append(self.current)
        elif tag == "label":
            self.label_for, self.label_text = (values.get("for"), [])
        elif tag in {"input", "select", "textarea", "button"}:
            field = {
                "tag": tag,
                "type": values.get("type")
                or ("text" if tag == "input" else "submit" if tag == "button" else tag),
                "name": values.get("name"),
                "id": values.get("id"),
                "required": "required" in values,
                "pattern": values.get("pattern"),
                "autocomplete": values.get("autocomplete"),
                "aria_label": values.get("aria-label"),
                "label": None,
                "line": self.getpos()[0],
                "column": self.getpos()[1] + 1,
                "constraints": {
                    key: values[key]
                    for key in (
                        "min",
                        "max",
                        "minlength",
                        "maxlength",
                        "step",
                        "multiple",
                        "disabled",
                        "readonly",
                    )
                    if key in values
                },
            }
            self.controls.append((node, field))
            if self.current is not None and "form" not in values:
                self.current["fields"].append(field)

    def handle_data(self, data: str) -> None:
        if not any(node["tag"] in {"script", "style"} for node in self.stack):
            for node in self.stack:
                node["text"].append(data)
        if self.label_for is not None:
            self.label_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                self.stack = self.stack[:index]
                break
        if tag == "label" and self.label_for is not None:
            self.labels[self.label_for] = " ".join("".join(self.label_text).split())
            self.label_for, self.label_text = (None, [])
        elif tag == "form":
            self.current = None

    def resolve(self) -> None:
        ids = {node["attrs"]["id"]: node for node in self.nodes if node["attrs"].get("id")}
        forms = {form["id"]: form for form in self.forms if form["id"]}
        for node, field in self.controls:
            attrs = node["attrs"]
            if attrs.get("form") in forms:
                forms[attrs["form"]]["fields"].append(field)
            references = (attrs.get("aria-labelledby") or "").split()
            accessible = " ".join(" ".join(ids[key]["text"]) for key in references if key in ids)
            labels = [
                candidate
                for candidate in self.nodes
                if candidate["tag"] == "label"
                and (
                    candidate["attrs"].get("for") == attrs.get("id")
                    and attrs.get("id")
                    or any(candidate is parent for parent in node["parents"])
                    and not candidate["attrs"].get("for")
                )
            ]
            fallback = " ".join(" ".join(label["text"]) for label in labels)
            if field["tag"] == "button":
                fallback = fallback or " ".join(node["text"])
            if field["type"] in {"submit", "reset", "button", "image"} and field["tag"] == "input":
                fallback = (
                    fallback
                    or attrs.get("alt")
                    or attrs.get("value")
                    or ({"submit": "Submit", "reset": "Reset"}.get(field["type"], ""))
                )
            field["label"] = (
                " ".join(
                    (
                        accessible
                        or attrs.get("aria-label")
                        or fallback
                        or attrs.get("title")
                        or ""
                    ).split()
                )
                or None
            )
            field["analysis"] = (
                "static HTML only; CSS, scripts and browser accessibility tree not evaluated"
            )


def _form_inventory(data: dict[str, Any]) -> dict[str, Any]:
    html = data.get("html", "")
    if not isinstance(html, str) or ("path" in data and not isinstance(data["path"], str)):
        raise ValueError("html and path must be strings")
    if data.get("path"):
        html = Path(data["path"]).read_text(encoding="utf-8")
    if not html:
        raise ValueError("html or path is required")
    parser = _FormParser()
    parser.feed(html)
    parser.resolve()
    issues = []
    for form_index, form in enumerate(parser.forms, 1):
        for field in form["fields"]:
            if field["type"] != "hidden" and (not field["label"]):
                issues.append(
                    {
                        "form": form_index,
                        "field": field["name"] or field["id"] or "unnamed",
                        "issue": "missing accessible label in supported static HTML patterns",
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
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    report = {"version": 1, "project": PROJECT, **_form_inventory(data)}
    if "baseline_html" in data:
        previous = _form_inventory({"html": data["baseline_html"]})

        def records(inventory: dict[str, Any]) -> dict[str, Any]:
            rows = {}
            for i, form in enumerate(inventory["forms"]):
                identity = form["id"] or f"form-{i + 1}"
                rows[identity] = {"action": form["action"], "method": form["method"]}
                for j, field in enumerate(form["fields"]):
                    key = f"{identity}/{field['id'] or field['name'] or 'unnamed'}:{j + 1}"
                    rows[key] = {
                        k: v for k, v in field.items() if k not in {"line", "column", "analysis"}
                    }
            return rows

        before, after = records(previous), records(report)
        report["comparison"] = {
            "added": {key: after[key] for key in sorted(after.keys() - before.keys())},
            "removed": {key: before[key] for key in sorted(before.keys() - after.keys())},
            "changed": {
                key: {"before": before[key], "after": after[key]}
                for key in sorted(before.keys() & after.keys())
                if before[key] != after[key]
            },
        }
    return report


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
