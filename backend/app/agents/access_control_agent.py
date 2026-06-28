from dataclasses import dataclass

from app.models.auth import User
from app.services.access_control_service import (
    get_required_permission,
    has_permission,
    is_protected_intent,
)


@dataclass
class AccessDecision:
    allowed: bool
    status: str
    required_permission: str | None
    message: str


class AccessControlAgent:
    """
    Deterministic access-control agent.

    This agent does not use an LLM.
    Access control must be predictable, testable, and safe.
    """

    def evaluate(
        self,
        intent: str,
        user: User | None,
        permissions: list[str],
    ) -> AccessDecision:
        if not is_protected_intent(intent):
            return AccessDecision(
                allowed=True,
                status="public_allowed",
                required_permission=None,
                message="This request does not require authentication.",
            )

        required_permission = get_required_permission(intent)

        if user is None:
            return AccessDecision(
                allowed=False,
                status="auth_required",
                required_permission=required_permission,
                message=(
                    "This action requires authorized clinic access. "
                    "Please verify as staff to continue."
                ),
            )

        if required_permission and not has_permission(permissions, required_permission):
            return AccessDecision(
                allowed=False,
                status="access_denied",
                required_permission=required_permission,
                message=(
                    "Access denied. Your role does not have permission "
                    "to perform this action."
                ),
            )

        return AccessDecision(
            allowed=True,
            status="access_granted",
            required_permission=required_permission,
            message="Access granted.",
        )