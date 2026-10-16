import copy

import pytest

from web_form_field_inventory.core import analyze


def variants(html, **extra):
    return analyze({"html": html, "include_submissions": True, **extra})["forms"][0]["submissions"]


def test_opt_in_and_external_multiple_submit_controls():
    html = (
        '<button form="a" name="route" value="external" formaction="../external">Outside</button>'
        '<form id="a" action="save" method="post"><input name="q">'
        '<button id="save" name="route" value="save">Save</button>'
        '<input type="submit" name="route" value="preview" formaction="/preview" formmethod="GET">'
        '<input type="reset"><button type="button">No</button></form>'
    )
    data = {"html": html, "document_url": "https://example.test/forms/edit"}
    original = copy.deepcopy(data)
    legacy = analyze(data)
    assert "submissions" not in legacy["forms"][0]
    rows = variants(html, document_url=data["document_url"])
    assert [row["action"] for row in rows] == [
        "https://example.test/external",
        "https://example.test/forms/save",
        "https://example.test/preview",
    ]
    assert [row["method"] for row in rows] == ["post", "post", "get"]
    assert [row["submitter"]["value"] for row in rows] == ["external", "save", "preview"]
    assert data == original


def test_disabled_fieldsets_first_legend_and_external_ownership():
    html = (
        '<form id="a"><button disabled>Disabled</button>'
        '<fieldset disabled><legend><button id="allowed">Allowed</button></legend>'
        "<legend><button>Disabled second legend</button></legend><button>Disabled</button>"
        '</fieldset><button form="missing">Unowned</button>'
        '<button form="b">Other</button><button>Normal</button></form>'
        '<form id="b"><button>Second</button></form>'
        '<input form="a" type="submit" disabled>'
    )
    rows = variants(html)
    assert len(rows) == 2
    assert rows[0]["submitter"]["id"] == "allowed"
    assert rows[1]["submitter"]["field"] == 5


def test_unnamed_and_image_submitters_do_not_invent_values():
    rows = variants(
        '<form><button>Go</button><input type="image" name="map">'
        '<input type="image"><input type="SuBmIt" name="go" value="yes"></form>'
    )
    assert rows[0]["submitter"]["value"] is None
    assert rows[1]["submitter"]["coordinate_names"] == ["map.x", "map.y"]
    assert rows[2]["submitter"]["coordinate_names"] == ["x", "y"]
    assert rows[3]["submitter"]["value"] == "yes"


def test_effective_actions_base_empty_invalid_methods_and_dialog():
    rows = variants(
        '<base href="/assets/"><form action="send" method="invalid">'
        '<button>Default</button><button formaction="" formmethod="POST">Empty</button>'
        '<button formaction="../review" formmethod="dialog">Dialog</button>'
        '<button formmethod="">Invalid</button><button type="unknown">Default type</button></form>',
        document_url="https://example.test/forms/edit",
    )
    assert rows[0]["action"] == "https://example.test/assets/send"
    assert rows[1]["action"] == "https://example.test/forms/edit"
    assert rows[2]["action"] == "https://example.test/review"
    assert [row["method"] for row in rows] == ["get", "post", "dialog", "get", "get"]
    assert variants('<form action="../save"><button>Go</button></form>')[0]["action"] == "../save"
    assert variants('<form><input name="q"></form>') == []


def test_baseline_compares_effective_variants_without_changing_default_schema():
    before = '<form id="a"><button formaction="/old" formmethod="get">Go</button></form>'
    after = before.replace("/old", "/new").replace('formmethod="get"', 'formmethod="post"')
    assert not analyze({"html": after, "baseline_html": before})["comparison"]["changed"]
    diff = analyze(
        {
            "html": after,
            "baseline_html": before,
            "include_submissions": True,
            "document_url": "https://example.test/",
        }
    )["comparison"]
    row = diff["changed"]["a"]
    assert row["before"]["submissions"][0]["method"] == "get"
    assert row["after"]["submissions"][0]["action"] == "https://example.test/new"
    disabled = after.replace("<button", "<button disabled")
    assert (
        analyze({"html": disabled, "baseline_html": after, "include_submissions": True})[
            "comparison"
        ]["changed"]["a"]["after"]["submissions"]
        == []
    )


@pytest.mark.parametrize("extra", [{"include_submissions": "yes"}, {"document_url": 3}])
def test_invalid_options(extra):
    with pytest.raises(TypeError):
        analyze({"html": "<form></form>", **extra})
