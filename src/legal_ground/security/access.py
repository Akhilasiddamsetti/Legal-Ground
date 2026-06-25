"""Caller identity and deny-by-default access checks for retrieval.

In production a Principal would be constructed from a verified Microsoft Entra
token. Locally it is built from CLI flags or the evaluation harness.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: str
    matter_ids: frozenset[str]


def can_access(chunk: dict, principal: Principal) -> bool:
    scope = chunk.get("access_scope")
    if not isinstance(scope, dict):
        return False

    matter_id = scope.get("matter_id")
    allowed_roles = scope.get("allowed_roles")
    if not isinstance(matter_id, str) or not matter_id:
        return False
    if not isinstance(allowed_roles, list) or not all(isinstance(role, str) for role in allowed_roles):
        return False

    return matter_id in principal.matter_ids and principal.role in allowed_roles


def pilot_principal(
    role: str = "pilot_user",
    matter_id: str = "acme-v-northridge",
) -> Principal:
    return Principal(
        user_id=f"local-{role}",
        role=role,
        matter_ids=frozenset({matter_id}),
    )
