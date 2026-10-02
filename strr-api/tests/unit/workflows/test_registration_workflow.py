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
"""Tests for RegistrationWorkflow state machine."""
import pytest
from statemachine.exceptions import TransitionNotAllowed
from unittest.mock import MagicMock, patch

from strr_api.enums.enum import RegistrationStatus
from strr_api.models.events import Events
from strr_api.workflows.registration_workflow import RegistrationWorkflow


class DummyUser:
    def __init__(self, user_id=42):
        self.id = user_id


class DummyRegistration:
    def __init__(self, status=RegistrationStatus.ACTIVE.value, reg_id=777):
        self.id = reg_id
        self.status = status
        self.decider_id = None
        self.cancelled_date = None
        self.is_set_aside = False
        self.noc_status = None

    def save(self):
        pass


def test_registration_suspension_and_reinstatement():
    """Verify suspension and reinstatement lifecycle with event tracking."""
    reg = DummyRegistration(status=RegistrationStatus.ACTIVE.value)
    reviewer = DummyUser(user_id=88)

    with patch("strr_api.services.events_service.EventsService.save_event") as mock_event, \
         patch("strr_api.services.email_service.EmailService.send_registration_status_update_email") as mock_email:

        wf = RegistrationWorkflow(reg, reviewer=reviewer)

        # Active -> Suspended
        wf.suspend()
        assert reg.status == RegistrationStatus.SUSPENDED
        assert reg.decider_id == 88
        mock_event.assert_called_with(
            event_type=Events.EventType.REGISTRATION,
            event_name=Events.EventName.NON_COMPLIANCE_SUSPENDED,
            registration_id=777,
            user_id=88,
            visible_to_applicant=True,
        )

        # Suspended -> Active (Reinstated)
        wf.reinstate()
        assert reg.status == RegistrationStatus.ACTIVE
        mock_event.assert_called_with(
            event_type=Events.EventType.REGISTRATION,
            event_name=Events.EventName.REGISTRATION_REINSTATED,
            registration_id=777,
            user_id=88,
            visible_to_applicant=True,
        )
        assert mock_email.call_count == 2


def test_registration_cancellation():
    """Verify cancellation lifecycle and timestamp recording."""
    reg = DummyRegistration(status=RegistrationStatus.ACTIVE.value)
    reviewer = DummyUser(user_id=55)

    with patch("strr_api.services.events_service.EventsService.save_event") as mock_event, \
         patch("strr_api.services.email_service.EmailService.send_registration_status_update_email"):

        wf = RegistrationWorkflow(reg, reviewer=reviewer)
        wf.cancel()

        assert reg.status == RegistrationStatus.CANCELLED
        assert reg.cancelled_date is not None
        assert reg.decider_id == 55


def test_illegal_registration_transitions():
    """Verify that cancelled registrations cannot be suspended or reinstated."""
    reg = DummyRegistration(status=RegistrationStatus.CANCELLED.value)
    wf = RegistrationWorkflow(reg)

    with pytest.raises(TransitionNotAllowed):
        wf.suspend()

    with pytest.raises(TransitionNotAllowed):
        wf.reinstate()
