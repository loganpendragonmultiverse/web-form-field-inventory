from __future__ import annotations

import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

PROJECT = "web-form-field-inventory"


MAX_HTML_BYTES = 5_000_000
MAX_JSON_BYTES = 12_000_000


def read_bounded(path: Path, limit: int) -> str:
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Input exceeds configured byte limit")
    return raw.decode("utf-8")


def _text(node: dict[str, Any]) -> str:
    if sum(map(len, node["text"])) > 10_000:
        raise ValueError("Static label text exceeds 10000 characters")
    return " ".join("".join(node["text"]).split())


def _field_type(tag: str, values: dict[str, str | None]) -> str:
    kind = (values.get("type") or "").lower()
    if tag == "input":
        return (
            kind
            if kind
            in {
                "hidden",
                "text",
                "search",
                "tel",
                "url",
                "email",
                "password",
                "date",
                "month",
                "week",
                "time",
                "datetime-local",
                "number",
                "range",
                "color",
                "checkbox",
                "radio",
                "file",
                "submit",
                "image",
                "reset",
                "button",
            }
            else "text"
        )
    if tag == "button":
        return kind if kind in {"submit", "reset", "button"} else "submit"
    return tag


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
        if len(self.nodes) >= 20_000 or len(self.stack) >= 200:
            raise ValueError("HTML exceeds 20000 nodes or 200 nesting levels")
        values: dict[str, str | None] = {}
        for key, value in attrs:
            values.setdefault(key, value)
        node: dict[str, Any] = {
            "tag": tag,
            "attrs": values,
            "text": [],
            "parents": self.stack.copy(),
        }
        self.nodes.append(node)
        labelable = tag in {"button", "meter", "output", "progress", "select", "textarea"} or (
            tag == "input" and _field_type(tag, values) != "hidden"
        )
        if labelable:
            for parent in self.stack:
                if parent["tag"] == "label" and "for" not in parent["attrs"]:
                    parent.setdefault("label_control", node)
        if tag == "legend" and self.stack and self.stack[-1]["tag"] == "fieldset":
            self.stack[-1].setdefault("first_legend", node)
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
            node["form_record"] = self.current
            self.forms.append(self.current)
        elif tag == "label":
            self.label_for, self.label_text = (values.get("for"), [])
        elif tag in {"input", "select", "textarea", "button"}:
            if len(self.controls) >= 2000:
                raise ValueError("HTML exceeds 2000 controls")
            field = {
                "tag": tag,
                "type": _field_type(tag, values),
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
        ids: dict[str, dict[str, Any]] = {}
        forms: dict[str, dict[str, Any]] = {}
        for node in self.nodes:
            if node["attrs"].get("id"):
                ids.setdefault(node["attrs"]["id"], node)
        for identity, node in ids.items():
            if node["tag"] == "form":
                forms[identity] = node["form_record"]
        for node, field in self.controls:
            attrs = node["attrs"]
            if attrs.get("form") in forms:
                forms[attrs["form"]]["fields"].append(field)
            references = (attrs.get("aria-labelledby") or "").split()
            if len(references) > 100:
                raise ValueError("aria-labelledby exceeds 100 references")
            accessible = " ".join(_text(ids[key]) for key in references if key in ids)
            if len(accessible) > 10_000:
                raise ValueError("Static label text exceeds 10000 characters")
            labels = [
                candidate
                for candidate in self.nodes
                if candidate["tag"] == "label"
                and (
                    candidate["attrs"].get("for") == attrs.get("id")
                    and attrs.get("id")
                    and ids.get(attrs["id"]) is node
                    or any(candidate is parent for parent in node["parents"])
                    and "for" not in candidate["attrs"]
                    and candidate.get("label_control") is node
                )
            ]
            fallback = " ".join(_text(label) for label in labels)
            if field["tag"] == "button":
                fallback = fallback or _text(node)
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
            if len(field["label"] or "") > 10_000:
                raise ValueError("Static label text exceeds 10000 characters")
            field["analysis"] = (
                "static HTML only; CSS, scripts and browser accessibility tree not evaluated"
            )

        for form in self.forms:
            form["fields"].sort(key=lambda field: (field["line"], field["column"]))


def _disabled(node: dict[str, Any]) -> bool:
    if "disabled" in node["attrs"]:
        return True
    for parent in node["parents"]:
        if parent["tag"] != "fieldset" or "disabled" not in parent["attrs"]:
            continue
        legend = parent.get("first_legend")
        if legend is None or not any(ancestor is legend for ancestor in node["parents"]):
            return True
    return False


def _submissions(parser: _FormParser, document_url: str) -> None:
    base = next(
        (
            (node["attrs"].get("href") or "")
            for node in parser.nodes
            if node["tag"] == "base" and "href" in node["attrs"]
        ),
        "",
    )
    base_url = urljoin(document_url, base)
    for form in parser.forms:
        variants = []
        for node, field in parser.controls:
            if node["tag"] not in {"input", "button"}:
                continue
            ordinal = next((i for i, item in enumerate(form["fields"], 1) if item is field), None)
            if ordinal is None or _disabled(node):
                continue
            kind = str(field["type"]).lower()
            if kind not in {"submit", "image"}:
                continue
            attrs = node["attrs"]
            action = attrs.get("formaction") if "formaction" in attrs else form["action"]
            action = action or ""
            method = str(attrs.get("formmethod") if "formmethod" in attrs else form["method"])
            method = method.lower()
            if method not in {"get", "post", "dialog"}:
                method = "get"
            name = field["name"]
            submitter = {
                "field": ordinal,
                "id": field["id"],
                "name": name,
                "type": kind,
                "value": attrs.get("value", "") if kind != "image" and name else None,
                "coordinate_names": ([f"{name}.x", f"{name}.y"] if name else ["x", "y"])
                if kind == "image"
                else [],
            }
            variants.append(
                {
                    "submitter": submitter,
                    "action": urljoin(base_url, action) if action else document_url,
                    "method": method,
                }
            )
        form["submissions"] = variants


def _form_inventory(data: dict[str, Any]) -> dict[str, Any]:
    html = data.get("html", "")
    if not isinstance(html, str) or ("path" in data and not isinstance(data["path"], str)):
        raise ValueError("html and path must be strings")
    if data.get("path"):
        html = read_bounded(Path(data["path"]), MAX_HTML_BYTES)
    if not html:
        raise ValueError("html or path is required")
    if len(html) > MAX_HTML_BYTES or len(html.encode("utf-8")) > MAX_HTML_BYTES:
        raise ValueError("HTML exceeds 5 MB limit")
    include_submissions = data.get("include_submissions", False)
    if not isinstance(include_submissions, bool):
        raise TypeError("include_submissions must be a boolean")
    document_url = data.get("document_url", "")
    if not isinstance(document_url, str):
        raise TypeError("document_url must be a string")
    parser = _FormParser()
    parser.feed(html)
    parser.resolve()
    if include_submissions:
        _submissions(parser, document_url)
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
        raise TypeError("input must be a JSON object")
    report = {"version": 1, "project": PROJECT, **_form_inventory(data)}
    if "baseline_html" in data:
        previous = _form_inventory(
            {
                "html": data["baseline_html"],
                "include_submissions": data.get("include_submissions", False),
                "document_url": data.get("document_url", ""),
            }
        )

        def records(inventory: dict[str, Any]) -> dict[str, Any]:
            entries: list[tuple[str, str, dict[str, Any]]] = []
            for i, form in enumerate(inventory["forms"]):
                identity = form["id"] or f"form-{i + 1}"
                row = {"action": form["action"], "method": form["method"]}
                if "submissions" in form:
                    row["submissions"] = form["submissions"]
                entries.append((identity, f"form {i + 1}", row))
                for j, field in enumerate(form["fields"]):
                    key = f"{identity}/{field['id'] or field['name'] or 'unnamed'}:{j + 1}"
                    entries.append(
                        (
                            key,
                            f"field {i + 1}:{j + 1}",
                            {
                                k: v
                                for k, v in field.items()
                                if k not in {"line", "column", "analysis"}
                            },
                        )
                    )
            counts = Counter(key for key, _, _ in entries)
            rows: dict[str, Any] = {}
            for preferred, ordinal, value in entries:
                key = preferred
                if counts[key] > 1:
                    key = f"{preferred} [{ordinal}]"
                    while key in counts or key in rows:
                        key += "@"
                rows[key] = value
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
