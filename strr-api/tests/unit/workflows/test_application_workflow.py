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
"""Tests for ApplicationWorkflow state machine."""
import pytest
from statemachine.exceptions import TransitionNotAllowed
from unittest.mock import MagicMock, patch

from strr_api.models.application import Application
from strr_api.models.events import Events
from strr_api.workflows.application_workflow import ApplicationWorkflow


class DummyUser:
    def __init__(self, user_id=42):
        self.id = user_id


class DummyApplication:
    def __init__(self, status=Application.Status.DRAFT.value, app_id=101):
        self.id = app_id
        self.status = status
        self.decision_date = None
        self.is_set_aside = False
        self.reviewer_id = None
        self.decider_id = None
        self.type = "registration"
        self.registration_id = None
        self.registration = None
        self.submitter_id = 1
        self.payment_account = "test_account"
        self.application_json = {}

    def save(self):
        pass


def test_happy_path_draft_to_approval():
    """Verify standard happy path progression from Draft to Full Review Approval."""
    app = DummyApplication(status=Application.Status.DRAFT.value)
    reviewer = DummyUser(user_id=99)

    with patch("strr_api.services.events_service.EventsService.save_event") as mock_save_event, \
         patch("strr_api.services.email_service.EmailService.send_application_status_update_email") as mock_email, \
         patch("strr_api.services.registration_service.RegistrationService.create_registration") as mock_create_reg:

        mock_reg = MagicMock()
        mock_reg.id = 555
        mock_create_reg.return_value = mock_reg

        wf = ApplicationWorkflow(app, reviewer=reviewer)
        assert wf.current_state == wf.draft

        # Draft -> Payment Due
        wf.submit_for_payment()
        assert app.status == Application.Status.PAYMENT_DUE.value

        # Payment Due -> Paid
        wf.record_payment()
        assert app.status == Application.Status.PAID.value

        # Paid -> Full Review
        wf.route_to_full_review()
        assert app.status == Application.Status.FULL_REVIEW.value

        # Full Review -> Approved
        wf.approve_full_review()
        assert app.status == Application.Status.FULL_REVIEW_APPROVED.value
        assert app.decision_date is not None
        assert app.reviewer_id == 99
        assert app.decider_id == 99

        # Verify side effects were triggered automatically
        mock_save_event.assert_called()
        mock_email.assert_called_once()
        mock_create_reg.assert_called_once()


def test_noc_lifecycle_and_approval():
    """Verify NOC issuing, expiry, and eventual approval."""
    app = DummyApplication(status=Application.Status.FULL_REVIEW.value)
    reviewer = DummyUser(user_id=10)

    with patch("strr_api.services.events_service.EventsService.save_event"), \
         patch("strr_api.services.email_service.EmailService.send_application_status_update_email"), \
         patch("strr_api.services.registration_service.RegistrationService.create_registration") as mock_reg:
        mock_reg.return_value = MagicMock(id=1)

        wf = ApplicationWorkflow(app, reviewer=reviewer)

        # Issue NOC
        wf.send_noc()
        assert app.status == Application.Status.NOC_PENDING.value

        # 30-day job expires NOC
        wf.expire_noc()
        assert app.status == Application.Status.NOC_EXPIRED.value

        # Examiner approves from expired NOC
        wf.approve_full_review()
        assert app.status == Application.Status.FULL_REVIEW_APPROVED.value
        assert app.decision_date is not None


def test_decline_and_set_aside():
    """Verify that declining an application and setting it aside restores it to Full Review."""
    app = DummyApplication(status=Application.Status.FULL_REVIEW.value)
    reviewer = DummyUser(user_id=12)

    with patch("strr_api.services.events_service.EventsService.save_event"), \
         patch("strr_api.services.email_service.EmailService.send_application_status_update_email"):

        wf = ApplicationWorkflow(app, reviewer=reviewer)

        # Full Review -> Declined
        wf.decline()
        assert app.status == Application.Status.DECLINED.value
        assert app.decision_date is not None

        # Set Aside restores to Full Review with flag
        wf.set_aside()
        assert app.status == Application.Status.FULL_REVIEW.value
        assert app.is_set_aside is True


def test_illegal_transition_prevention():
    """Verify that impossible transitions are strictly prevented by the state machine."""
    app = DummyApplication(status=Application.Status.DRAFT.value)
    wf = ApplicationWorkflow(app)

    # 1. Cannot jump from DRAFT to APPROVED directly
    with pytest.raises(TransitionNotAllowed):
        wf.approve_full_review()
    assert app.status == Application.Status.DRAFT.value

    # 2. Cannot send NOC on DRAFT
    with pytest.raises(TransitionNotAllowed):
        wf.send_noc()

    # 3. Cannot route unpaid application to review
    with pytest.raises(TransitionNotAllowed):
        wf.route_to_full_review()


def test_terminal_state_lock():
    """Verify that terminal states (Approved) cannot transition to incompatible states."""
    app = DummyApplication(status=Application.Status.FULL_REVIEW_APPROVED.value)
    wf = ApplicationWorkflow(app)

    # Cannot decline an already approved application
    with pytest.raises(TransitionNotAllowed):
        wf.decline()

    # Cannot send NOC on an approved application
    with pytest.raises(TransitionNotAllowed):
        wf.send_noc()


def test_allowed_actions_mapping():
    """Verify that allowed examiner actions match backend rules."""
    assert ApplicationWorkflow.get_allowed_actions_for_status(Application.Status.FULL_REVIEW.value) == ["APPROVE", "SEND_NOC", "REJECT", "WITHDRAW"]
    assert ApplicationWorkflow.get_allowed_actions_for_status(Application.Status.NOC_PENDING.value) == ["APPROVE", "REJECT", "WITHDRAW"]
    assert ApplicationWorkflow.get_allowed_actions_for_status(Application.Status.DECLINED.value) == ["SET_ASIDE"]
    assert ApplicationWorkflow.get_allowed_actions_for_status(Application.Status.FULL_REVIEW_APPROVED.value) == []


def test_withdraw_suppresses_email():
    """Verify that withdrawal transitions to declined but suppresses notification email."""
    app = DummyApplication(status=Application.Status.FULL_REVIEW.value)
    reviewer = DummyUser(user_id=14)

    with patch("strr_api.services.events_service.EventsService.save_event") as mock_event, \
         patch("strr_api.services.email_service.EmailService.send_application_status_update_email") as mock_email:

        wf = ApplicationWorkflow(app, reviewer=reviewer, is_withdraw=True)
        wf.withdraw()

        assert app.status == Application.Status.DECLINED.value
        mock_event.assert_called_once()
        mock_email.assert_not_called()

