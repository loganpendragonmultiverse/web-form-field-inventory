import json
from pathlib import Path

import pytest

from web_form_field_inventory.cli import main
from web_form_field_inventory.core import PROJECT, analyze, render_json, render_markdown


def test_representative_sample_has_expected_result():
    data = json.loads(
        (Path(__file__).parents[1] / "examples" / "sample.json").read_text(encoding="utf-8")
    )
    report = analyze(data)
    assert report["version"] == 1 and report["project"] == PROJECT
    assert report["form_count"] == 1 and report["field_count"] == 2 and len(report["issues"]) == 1
    assert f'"project": "{PROJECT}"' in render_json(report)
    assert PROJECT.replace("-", " ").title() in render_markdown(report)


def test_missing_required_input_is_rejected():
    with pytest.raises(ValueError):
        analyze({})


def test_cli_json_and_output_safety(tmp_path, capsys):
    source = Path(__file__).parents[1] / "examples" / "sample.json"
    assert main([str(source), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["project"] == PROJECT
    output = tmp_path / "report.md"
    output.write_text("keep", encoding="utf-8")
    assert main([str(source), "--output", str(output)]) == 2


def test_reads_saved_html_and_inventory_variants(tmp_path):
    page = tmp_path / "form.html"
    page.write_text(
        '<form><label for="choice"> Choice </label>'
        '<select id="choice"><option>A</option></select>'
        '<textarea name="notes" aria-label="Notes"></textarea>'
        '<input type="hidden" name="token"><button>Send</button></form>',
        encoding="utf-8",
    )
    report = analyze({"path": str(page)})
    assert report["field_count"] == 4
    assert report["forms"][0]["fields"][0]["label"] == "Choice"
    assert any(item["issue"] == "missing submission name" for item in report["issues"])
    with pytest.raises(ValueError, match="html or path"):
        analyze({"html": ""})
