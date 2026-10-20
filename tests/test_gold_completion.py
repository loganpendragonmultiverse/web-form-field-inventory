import json
from pathlib import Path

import pytest

from web_form_field_inventory.cli import main
from web_form_field_inventory.core import analyze


def test_external_controls_and_submissions_follow_source_order():
    html = '<button form="f" id="before">Before</button><form id="f"><input name="q"><button id="inside">Inside</button></form><input form="f" id="after">'
    form = analyze({"html": html, "include_submissions": True})["forms"][0]
    assert [row["id"] for row in form["fields"]] == ["before", None, "inside", "after"]
    assert [row["submitter"]["field"] for row in form["submissions"]] == [1, 3]


def test_first_duplicate_ids_and_attributes_match_static_document_order():
    html = '<span id="label">First</span><span id="label">Last</span><form id="f" action="/first" action="/last"></form><form id="f"></form><input form="f" aria-labelledby="label">'
    result = analyze({"html": html})
    assert result["forms"][0]["action"] == "/first"
    assert result["forms"][0]["fields"][0]["label"] == "First"
    assert result["forms"][1]["fields"] == []


def test_effective_types_respect_case_defaults_and_element_kind():
    html = '<form><input type="HIDDEN" name="a"><input type="unknown" name="b"><button type="unknown">Go</button><select type="submit" name="c"></select><textarea type="image" name="d"></textarea></form>'
    report = analyze({"html": html, "include_submissions": True})
    assert [row["type"] for row in report["forms"][0]["fields"]] == [
        "hidden",
        "text",
        "submit",
        "select",
        "textarea",
    ]
    assert all(row["field"] != "a" for row in report["issues"])
    assert len(report["forms"][0]["submissions"]) == 1


def test_duplicate_form_and_cross_kind_comparison_keys_preserve_all_rows():
    before = '<form id="a" action="/one"><input name="x"></form><form id="a/x:1" action="/two"></form><form id="a" action="/three"></form>'
    after = (
        before.replace("/one", "/changed-one")
        .replace("/two", "/changed-two")
        .replace("/three", "/changed-three")
    )
    changes = analyze({"html": after, "baseline_html": before})["comparison"]
    assert len(changes["changed"]) == 3
    assert sorted(row["after"]["action"] for row in changes["changed"].values()) == [
        "/changed-one",
        "/changed-three",
        "/changed-two",
    ]
    assert not changes["added"] and not changes["removed"]


@pytest.mark.parametrize(
    "html",
    [
        "<div>" * 201 + "x",
        "<br>" * 20001,
        "<input>" * 2001,
        "<form><label>" + "x" * 10001 + "<input></label></form>",
        '<form><input aria-labelledby="' + "x " * 101 + '"></form>',
    ],
    ids=["nesting-depth", "node-count", "control-count", "label-length", "aria-references"],
)
def test_oversized_static_structures_fail_instead_of_partial_success(html):
    with pytest.raises(ValueError, match="exceeds"):
        analyze({"html": html})


def test_html_byte_limit_and_path_reads_are_bounded(tmp_path, monkeypatch):
    from web_form_field_inventory import core

    monkeypatch.setattr(core, "MAX_HTML_BYTES", 5)
    with pytest.raises(ValueError, match="5 MB"):
        analyze({"html": "é" * 3})
    source = tmp_path / "large.html"
    source.write_text("<form></form>")
    with pytest.raises(ValueError, match="byte limit"):
        analyze({"path": str(source)})


def test_exclusive_report_preserves_raced_files_and_dangling_links(tmp_path, monkeypatch):
    source = tmp_path / "input.json"
    source.write_text(json.dumps({"html": "<form></form>"}))
    output = tmp_path / "output.md"
    original = Path.open

    def racing_open(path, mode="r", *args, **kwargs):
        if path == output and mode == "x":
            with original(output, "w") as writer:
                writer.write("preserve")
        return original(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", racing_open)
    assert main([str(source), "--output", str(output)]) == 2
    assert output.read_text() == "preserve"
    link, target = tmp_path / "link", tmp_path / "absent"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks unavailable")
    assert main([str(source), "--output", str(link)]) == 2
    assert not target.exists()


def test_implicit_label_only_names_first_labelable_control():
    report = analyze(
        {
            "html": '<form><label>First <input type="hidden"><input id="a"><input id="b"></label><label for="">Not implicit <input id="c"></label></form>'
        }
    )
    fields = report["forms"][0]["fields"]
    assert [field["label"] for field in fields] == [None, "First", None, None]


def test_duplicate_id_explicit_label_does_not_name_later_control():
    report = analyze(
        {
            "html": '<form><span id="a">Not labelable</span><label for="a">Label</label><input id="a"></form>'
        }
    )
    assert report["forms"][0]["fields"][0]["label"] is None


def test_external_form_owner_uses_first_global_id_node():
    report = analyze(
        {"html": '<span id="f"></span><form id="f"></form><input form="f" name="external">'}
    )
    assert report["field_count"] == 0
    assert report["forms"][0]["fields"] == []


@pytest.mark.parametrize(
    "label",
    [
        'aria-label="' + "x" * 10001 + '"',
        'title="' + "x" * 10001 + '"',
        'type="submit" value="' + "x" * 10001 + '"',
        'type="image" alt="' + "x" * 10001 + '"',
    ],
)
def test_all_selected_label_sources_enforce_limit(label):
    with pytest.raises(ValueError, match="10000"):
        analyze({"html": "<form><input " + label + "></form>"})


def test_combined_explicit_labels_enforce_final_limit():
    html = (
        '<form><label for="x">'
        + "a" * 6000
        + '</label><label for="x">'
        + "b" * 6000
        + '</label><input id="x"></form>'
    )
    with pytest.raises(ValueError, match="10000"):
        analyze({"html": html})
