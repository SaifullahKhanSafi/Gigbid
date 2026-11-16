import uuid
import pytest
from core import db
from core.security import tenant_context
from mcp_servers.portfolio.server import rank_team, get_case_study


def test_agency_routes_to_supported_member_and_revalidates_evidence():
    user = "agency-" + uuid.uuid4().hex
    tenant_context.set(user)
    db.put(user, "settings", "profile", {"persona": "ml", "agency_mode": False})
    with pytest.raises(PermissionError):
        rank_team("Build a React TypeScript booking app", ["React", "TypeScript"])
    db.put(user, "settings", "profile", {"persona": "ml", "agency_mode": True})
    result = rank_team("Build a React TypeScript booking app", ["React", "TypeScript"])
    assert result["selected_persona"] == "web"
    assert result["fit"]["score"] == 1
    assert get_case_study(result["fit"]["evidence"][0]["id"])["persona"] == "web"
