from legal_ground.security.access import Principal, can_access, pilot_principal

AUTHORIZED_CHUNK = {
    "access_scope": {
        "matter_id": "acme-v-northridge",
        "allowed_roles": ["pilot_user", "pilot_reviewer", "pilot_admin"],
    }
}


def test_authorized_user_can_access():
    principal = Principal("u1", "pilot_user", frozenset({"acme-v-northridge"}))
    assert can_access(AUTHORIZED_CHUNK, principal) is True


def test_wrong_matter_is_denied():
    principal = Principal("u2", "pilot_user", frozenset({"some-other-matter"}))
    assert can_access(AUTHORIZED_CHUNK, principal) is False


def test_wrong_role_is_denied():
    principal = Principal("u3", "outsider", frozenset({"acme-v-northridge"}))
    assert can_access(AUTHORIZED_CHUNK, principal) is False


def test_missing_access_scope_is_denied():
    principal = Principal("u4", "pilot_user", frozenset({"acme-v-northridge"}))
    assert can_access({}, principal) is False
    assert can_access({"access_scope": None}, principal) is False
    assert can_access({"access_scope": {"matter_id": "acme-v-northridge"}}, principal) is False


def test_pilot_principal_is_authorized_by_default():
    assert can_access(AUTHORIZED_CHUNK, pilot_principal()) is True
