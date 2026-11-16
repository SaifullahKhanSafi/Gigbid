import uuid
import pytest
from core.security import tenant_context, token
from mcp_servers.workspace.server import create_email_draft, create_interview_hold, free_slots


def test_workspace_preview_approval_and_replay():
    user = "workspace-" + uuid.uuid4().hex
    tenant_context.set(user)
    preview = create_email_draft("I would confirm the interview time.", "draft-" + user)
    with pytest.raises(Exception):
        create_email_draft("I would confirm the interview time.", "draft-" + user, dry_run=False)
    grant = token(user, "approved_write", hash=preview["payload_hash"])
    first = create_email_draft("I would confirm the interview time.", "draft-" + user, grant, False)
    assert create_email_draft("I would confirm the interview time.", "draft-" + user, grant, False) == first
    start = free_slots(1)["slots"][0]["start"]
    preview = create_interview_hold(start, "hold-" + user)
    hold = create_interview_hold(
        start, "hold-" + user, token(user, "approved_write", hash=preview["payload_hash"]), False
    )
    assert hold["start"] == start
    assert not any(s["start"] == start for s in free_slots(1)["slots"])
