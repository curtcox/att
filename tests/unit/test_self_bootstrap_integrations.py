from att.core.self_bootstrap_integrations import parse_gh_actions_status


def test_parse_actions_status_pending_when_invalid_json() -> None:
    assert parse_gh_actions_status("not-json", "feature") == "pending"


def test_parse_actions_status_success_for_completed_success() -> None:
    raw = '[{"headBranch":"feature","status":"completed","conclusion":"success"}]'
    assert parse_gh_actions_status(raw, "feature") == "success"


def test_parse_actions_status_failure_for_completed_failure() -> None:
    raw = '[{"headBranch":"feature","status":"completed","conclusion":"failure"}]'
    assert parse_gh_actions_status(raw, "feature") == "failure"


def test_parse_actions_status_pending_for_in_progress() -> None:
    raw = '[{"headBranch":"feature","status":"in_progress","conclusion":null}]'
    assert parse_gh_actions_status(raw, "feature") == "pending"
