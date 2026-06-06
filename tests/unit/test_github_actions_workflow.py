from pathlib import Path

import yaml


def test_codescribe_workflow_yaml_loads() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/codescribe.yml").read_text())
    triggers = workflow.get("on") or workflow.get(True)

    assert workflow["name"] == "CodeScribe PR Analysis"
    assert "pull_request" in triggers
    assert workflow["permissions"]["pull-requests"] == "write"


def test_reusable_action_yaml_loads() -> None:
    action = yaml.safe_load(Path("action.yml").read_text())

    assert action["name"] == "CodeScribe PR Intelligence"
    assert action["runs"]["using"] == "composite"
