from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from app.models.action import Action, ActionType, ActionStatus, get_utc_now


class SimulatedActionService:
    """Service responsible for executing approved actions within a safe simulated environment."""

    def execute_action(self, action: Action) -> Tuple[ActionStatus, Dict[str, Any], str]:
        """
        Execute an approved action in a simulated environment.
        Returns (new_status, execution_result_dict, human_readable_message)
        """
        now = get_utc_now()
        payload = action.payload_json or {}

        if action.action_type == ActionType.SEND_MESSAGE:
            recipient = payload.get("recipient", "Unknown Recipient")
            subject = payload.get("subject", "No Subject")
            message_body = payload.get("message_body", "")

            # Simulated message transmission
            result = {
                "simulated": True,
                "channel": "SIMULATED_EMAIL_OR_DISPATCH",
                "recipient": recipient,
                "subject": subject,
                "dispatched_at": now.isoformat(),
                "simulated_delivery_status": "DELIVERED_TO_SIMULATION_INBOX",
                "simulated_provider_note": (
                    "Message simulated. No external email or messaging service was contacted."
                ),
            }
            msg = f"Simulated message successfully dispatched to '{recipient}'."
            return ActionStatus.EXECUTED, result, msg

        elif action.action_type == ActionType.SCHEDULE_FOLLOW_UP:
            due_at = payload.get("due_at")
            purpose = payload.get("purpose", "")

            # Simulated follow-up tracking
            result = {
                "simulated": True,
                "follow_up_scheduled": True,
                "due_at": due_at,
                "purpose": purpose,
                "scheduled_at": now.isoformat(),
                "simulated_provider_note": (
                    "Follow-up scheduled in local case state. No external calendar or push notifications triggered."
                ),
            }
            msg = f"Follow-up successfully scheduled for {due_at}."
            return ActionStatus.EXECUTED, result, msg

        else:
            # Unsupported action type fallback
            result = {
                "simulated": True,
                "error": f"Unsupported action type: {action.action_type}",
            }
            return ActionStatus.FAILED, result, "Action execution failed due to unsupported type."
