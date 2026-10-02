# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Registration Lifecycle State Machine."""
from datetime import datetime, timezone
from typing import Optional

from statemachine import State, StateMachine

from strr_api.enums.enum import RegistrationStatus
from strr_api.models.events import Events
from strr_api.models.rental import Registration
from strr_api.services.email_service import EmailService
from strr_api.services.events_service import EventsService


class RegistrationWorkflow(StateMachine):
    """
    Finite State Machine governing the STRR Registration lifecycle.
    
    Guarantees valid status transitions and automated audit event and email dispatch.
    """

    # --- States ---
    active = State("Active", value=RegistrationStatus.ACTIVE, initial=True)
    suspended = State("Suspended", value=RegistrationStatus.SUSPENDED)
    expired = State("Expired", value=RegistrationStatus.EXPIRED)
    cancelled = State("Cancelled", value=RegistrationStatus.CANCELLED)

    # --- Transitions ---
    suspend = active.to(suspended)
    reinstate = suspended.to(active) | cancelled.to(active, cond="is_set_aside_active")
    cancel = (
        active.to(cancelled)
        | suspended.to(cancelled)
        | cancelled.to(cancelled, cond="is_set_aside_active")
    )
    expire = active.to(expired) | suspended.to(expired)
    renew = (
        active.to(active)
        | expired.to(active)
    )

    def is_set_aside_active(self):
        """Guard condition: permits transitions from terminal state if decision was set aside."""
        return bool(getattr(self.registration, "is_set_aside", False))

    def __init__(self, registration: Registration, reviewer=None, email_content: Optional[str] = None):
        self.registration = registration
        self.reviewer = reviewer
        self.email_content = email_content
        if not isinstance(registration.status, RegistrationStatus):
            try:
                registration.status = RegistrationStatus(registration.status)
            except (ValueError, TypeError):
                registration.status = RegistrationStatus.ACTIVE
        super().__init__(model=registration, state_field="status")

    def transition_to_status(self, target_status: str):
        """Transition registration to target status using the appropriate event."""
        from statemachine.exceptions import TransitionNotAllowed

        target_str = target_status.value if hasattr(target_status, "value") else str(target_status)
        if target_str == RegistrationStatus.SUSPENDED.value:
            self.suspend()
        elif target_str == RegistrationStatus.ACTIVE.value:
            if self.current_state == self.suspended or (
                self.current_state == self.cancelled and self.is_set_aside_active()
            ):
                self.reinstate()
            else:
                self.renew()
        elif target_str == RegistrationStatus.CANCELLED.value:
            self.cancel()
        elif target_str == RegistrationStatus.EXPIRED.value:
            self.expire()
        else:
            raise TransitionNotAllowed(f"No transition defined to target registration status {target_str}")

    def before_transition(self, event: str, state: State):
        """Track decider on the registration."""
        if self.reviewer:
            self.registration.decider_id = self.reviewer.id

    def on_enter_cancelled(self):
        """Stamp cancellation timestamp."""
        self.registration.cancelled_date = datetime.now(timezone.utc)

    def after_transition(self, event: str, source: State, target: State):
        """Execute audit event and notification dispatch."""
        self.registration.is_set_aside = False
        self.registration.noc_status = None
        self.registration.save()

        reviewer_id = self.reviewer.id if self.reviewer else None
        event_name = None

        if target == self.active:
            if source == self.suspended:
                event_name = Events.EventName.REGISTRATION_REINSTATED
            else:
                event_name = Events.EventName.REGISTRATION_APPROVED
        elif target == self.suspended:
            event_name = Events.EventName.NON_COMPLIANCE_SUSPENDED
        elif target == self.cancelled:
            event_name = Events.EventName.REGISTRATION_CANCELLED
        elif target == self.expired:
            event_name = Events.EventName.REGISTRATION_EXPIRED

        if event_name:
            try:
                EventsService.save_event(
                    event_type=Events.EventType.REGISTRATION,
                    event_name=event_name,
                    registration_id=self.registration.id,
                    user_id=reviewer_id,
                    visible_to_applicant=True,
                )
            except Exception:
                pass

        try:
            EmailService.send_registration_status_update_email(self.registration, self.email_content)
        except Exception:
            pass
