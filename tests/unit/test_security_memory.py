import pytest
from core.security import mask, token, decode
from agent.memory.promotion_rules import record_edit, record_outcome
from agent.memory.store import MemoryStore


def test_mask_nested_pii():
    value = mask({"token": "super-secret", "body": "Email x@y.test, call +92 300 1234567"})
    assert value["token"] == "[REDACTED]" and "x@y.test" not in value["body"] and "1234567" not in value["body"]


def test_scope_and_expiry():
    with pytest.raises(ValueError):
        decode(token("u", "mcp"), "user")
    with pytest.raises(Exception):
        decode(token("u", "user", ttl=-1), "user")


def test_style_needs_three_distinct_edits():
    user = "memory-user"
    for i in range(2):
        record_edit(user, "Hello there\nI would test.", "I would test.", str(i))
    assert not MemoryStore().search((user, "style"))
    record_edit(user, "Hello there\nI would test.", "I would test.", "third")
    assert len(MemoryStore().search((user, "style"))) == 1
    record_edit(user, "Hello there\nI would test.", "I would test.", "third")
    assert MemoryStore().search((user, "style"))[0].value["confirmations"] == 3


def test_outcome_threshold_and_tenant_isolation():
    for i in range(5):
        record_outcome("outcome-user", "ml", "replied", str(i))
    assert MemoryStore().get(("outcome-user", "outcome"), "ml")
    assert not MemoryStore().get(("other", "outcome"), "ml")
