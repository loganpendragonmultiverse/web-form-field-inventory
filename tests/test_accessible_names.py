import pytest

from web_form_field_inventory.core import analyze


def test_implicit_labels_buttons_aria_and_external_controls() -> None:
    html = """<form id="profile"><label>Name <input name="name"></label>
<button>Save <span>profile</span></button></form>
<span id="first">Contact</span><span id="second">email</span>
<input form="profile" name="email" aria-labelledby="first second" required>
<label for="phone">Phone</label><input form="profile" id="phone" name="phone" aria-label="Mobile phone">
<input form="profile" type="submit"><input form="profile" type="hidden" name="token">
"""
    report = analyze({"html": html})
    fields = report["forms"][0]["fields"]
    assert [field["label"] for field in fields[:5]] == [
        "Name",
        "Save profile",
        "Contact email",
        "Mobile phone",
        "Submit",
    ]
    assert fields[0]["type"] == "text"
    assert all("accessible label" not in issue["issue"] for issue in report["issues"])
    assert fields[2]["line"] == 4 and fields[2]["required"]


def test_saved_html_diff_is_structural() -> None:
    before = '<form id="a" action="/old"><input name="qty" min="1"></form>'
    after = (
        '<form id="a" action="/new"><input name="qty" min="2" required><button>Save</button></form>'
    )
    diff = analyze({"html": after, "baseline_html": before})["comparison"]
    assert diff["changed"]["a"]["after"]["action"] == "/new"
    assert diff["changed"]["a/qty:1"]["after"]["constraints"] == {"min": "2"}
    assert len(diff["added"]) == 1 and not diff["removed"]


@pytest.mark.parametrize(
    "data", [{"html": []}, {"path": 42}, {"html": "<form></form>", "baseline_html": None}]
)
def test_invalid_fields(data) -> None:
    with pytest.raises((ValueError, TypeError)):
        analyze(data)
