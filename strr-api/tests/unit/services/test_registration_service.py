# Copyright © 2024 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""Tests for registration service methods."""

import json
from datetime import datetime, timezone

import pytest

from strr_api.enums.enum import RegistrationStatus
from strr_api.models import Events, Registration, User
from strr_api.services import RegistrationService


@pytest.fixture
def host_registration(session):
    """Create a HOST registration for testing."""
    user = User(username="testuser", firstname="Test", lastname="User")
    session.add(user)
    session.flush()

    registration = Registration(
        registration_type=Registration.RegistrationType.HOST,
        registration_number="TST-12345",
        sbc_account_id=12345,
        status=RegistrationStatus.ACTIVE,
        user_id=user.id,
        start_date=datetime.now(timezone.utc),
        expiry_date=datetime.now(timezone.utc),
        registration_json={
            "primaryContact": {
                "firstName": "John",
                "lastName": "Doe",
                "emailAddress": "old@example.com",
            }
        },
    )
    session.add(registration)
    session.flush()
    return {"registration": registration, "user": user}


@pytest.fixture
def platform_registration(session):
    """Create a PLATFORM registration for testing."""
    user = User(username="platformuser", firstname="Platform", lastname="User")
    session.add(user)
    session.flush()

    registration = Registration(
        registration_type=Registration.RegistrationType.PLATFORM,
        registration_number="PLT-12345",
        sbc_account_id=67890,
        status=RegistrationStatus.ACTIVE,
        user_id=user.id,
        start_date=datetime.now(timezone.utc),
        expiry_date=datetime.now(timezone.utc),
        registration_json={
            "primaryContact": {
                "firstName": "Jane",
                "lastName": "Smith",
                "emailAddress": "platform-old@example.com",
            }
        },
    )
    session.add(registration)
    session.flush()
    return {"registration": registration, "user": user}


@pytest.fixture
def strata_hotel_registration(session):
    """Create a STRATA_HOTEL registration for testing."""
    user = User(username="stratauser", firstname="Strata", lastname="User")
    session.add(user)
    session.flush()

    registration = Registration(
        registration_type=Registration.RegistrationType.STRATA_HOTEL,
        registration_number="STR-12345",
        sbc_account_id=11111,
        status=RegistrationStatus.ACTIVE,
        user_id=user.id,
        start_date=datetime.now(timezone.utc),
        expiry_date=datetime.now(timezone.utc),
        registration_json={
            "businessDetails": {
                "primaryContact": {
                    "firstName": "Hotel",
                    "lastName": "Manager",
                    "emailAddress": "strata-old@example.com",
                }
            }
        },
    )
    session.add(registration)
    session.flush()
    return {"registration": registration, "user": user}


def test_update_registration_host_email(session, host_registration):
    """Test updating email for HOST registration type."""
    registration = host_registration["registration"]
    user = host_registration["user"]

    update_data = {"primaryContact": {"emailAddress": "new@example.com"}}
    updated_reg = RegistrationService.update_registration(registration, update_data, user)

    assert updated_reg.registration_json["primaryContact"]["emailAddress"] == "new@example.com"

    # Check event was created
    events = Events.fetch_registration_events(registration.id, applicant_visible_events_only=False)
    assert len(events) == 1
    event = events[0]
    assert event.event_name == Events.EventName.REGISTRATION_UPDATED
    assert event.user_id == user.id
    assert event.visible_to_applicant is True

    # Check event details structure
    details = json.loads(event.details)
    assert "changes" in details
    assert len(details["changes"]) == 1
    change = details["changes"][0]
    assert change["field"] == "primaryContact.emailAddress"
    assert change["oldValue"] == "old@example.com"
    assert change["newValue"] == "new@example.com"


def test_update_registration_platform_email(session, platform_registration):
    """Test updating email for PLATFORM registration type."""
    registration = platform_registration["registration"]
    user = platform_registration["user"]

    update_data = {"primaryContact": {"emailAddress": "platform-new@example.com"}}
    updated_reg = RegistrationService.update_registration(registration, update_data, user)

    assert updated_reg.registration_json["primaryContact"]["emailAddress"] == "platform-new@example.com"

    # Check event was created
    events = Events.fetch_registration_events(registration.id, applicant_visible_events_only=False)
    assert len(events) == 1
    event = events[0]
    assert event.event_name == Events.EventName.REGISTRATION_UPDATED

    # Check event details
    details = json.loads(event.details)
    change = details["changes"][0]
    assert change["oldValue"] == "platform-old@example.com"
    assert change["newValue"] == "platform-new@example.com"


def test_update_registration_strata_hotel_email(session, strata_hotel_registration):
    """Test updating email for STRATA_HOTEL registration type."""
    registration = strata_hotel_registration["registration"]
    user = strata_hotel_registration["user"]

    update_data = {"businessDetails": {"primaryContact": {"emailAddress": "strata-new@example.com"}}}
    updated_reg = RegistrationService.update_registration(registration, update_data, user)

    assert (
        updated_reg.registration_json["businessDetails"]["primaryContact"]["emailAddress"] == "strata-new@example.com"
    )

    # Check event was created
    events = Events.fetch_registration_events(registration.id, applicant_visible_events_only=False)
    assert len(events) == 1
    event = events[0]
    assert event.event_name == Events.EventName.REGISTRATION_UPDATED

    # Check event details
    details = json.loads(event.details)
    change = details["changes"][0]
    assert change["oldValue"] == "strata-old@example.com"
    assert change["newValue"] == "strata-new@example.com"


def test_update_registration_no_change_no_event(session, host_registration):
    """Test that no event is created when email value doesn't change."""
    registration = host_registration["registration"]
    user = host_registration["user"]

    # Update with same email
    update_data = {"primaryContact": {"emailAddress": "old@example.com"}}
    updated_reg = RegistrationService.update_registration(registration, update_data, user)

    # Email should still be the same
    assert updated_reg.registration_json["primaryContact"]["emailAddress"] == "old@example.com"

    # No event should be created
    events = Events.fetch_registration_events(registration.id, applicant_visible_events_only=False)
    assert len(events) == 0


def test_update_registration_empty_registration_json(session):
    """Test updating email when registration_json is empty or None."""
    user = User(username="emptyuser", firstname="Empty", lastname="User")
    session.add(user)
    session.flush()

    registration = Registration(
        registration_type=Registration.RegistrationType.HOST,
        registration_number="TST-EMPTY",
        sbc_account_id=99999,
        status=RegistrationStatus.ACTIVE,
        user_id=user.id,
        start_date=datetime.now(timezone.utc),
        expiry_date=datetime.now(timezone.utc),
        registration_json=None,
    )
    session.add(registration)
    session.flush()

    update_data = {"primaryContact": {"emailAddress": "new@example.com"}}
    updated_reg = RegistrationService.update_registration(registration, update_data, user)

    # Should create the structure
    assert updated_reg.registration_json is not None
    assert updated_reg.registration_json["primaryContact"]["emailAddress"] == "new@example.com"

    # Event should track old value as None
    events = Events.fetch_registration_events(registration.id, applicant_visible_events_only=False)
    assert len(events) == 1
    details = json.loads(events[0].details)
    change = details["changes"][0]
    assert change["oldValue"] is None
    assert change["newValue"] == "new@example.com"


def test_update_registration_updates_timestamp(session, host_registration):
    """Test that updated_date is modified when registration is updated."""
    registration = host_registration["registration"]
    user = host_registration["user"]

    original_updated_date = registration.updated_date

    update_data = {"primaryContact": {"emailAddress": "timestamp-test@example.com"}}
    updated_reg = RegistrationService.update_registration(registration, update_data, user)

    # Updated date should be changed
    assert updated_reg.updated_date > original_updated_date


def test_update_registration_multiple_fields(session, host_registration):
    """Test updating multiple fields in primaryContact simultaneously."""
    registration = host_registration["registration"]
    user = host_registration["user"]

    update_data = {
        "primaryContact": {
            "emailAddress": "multi-test@example.com",
            "phoneNumber": "555-1234",
            "firstName": "Updated",
        }
    }
    updated_reg = RegistrationService.update_registration(registration, update_data, user)

    assert updated_reg.registration_json["primaryContact"]["emailAddress"] == "multi-test@example.com"
    assert updated_reg.registration_json["primaryContact"]["phoneNumber"] == "555-1234"
    assert updated_reg.registration_json["primaryContact"]["firstName"] == "Updated"

    # Check event tracks all changes
    events = Events.fetch_registration_events(registration.id, applicant_visible_events_only=False)
    assert len(events) == 1
    details = json.loads(events[0].details)
    assert len(details["changes"]) == 3


def test_update_registration_secondary_contact(session, host_registration):
    """Test updating secondaryContact fields."""
    registration = host_registration["registration"]
    user = host_registration["user"]

    # Add a secondary contact first
    registration.registration_json["secondaryContact"] = {
        "firstName": "Second",
        "lastName": "Contact",
        "emailAddress": "second-old@example.com",
    }
    registration.save()

    update_data = {"secondaryContact": {"emailAddress": "second-new@example.com"}}
    updated_reg = RegistrationService.update_registration(registration, update_data, user)

    assert updated_reg.registration_json["secondaryContact"]["emailAddress"] == "second-new@example.com"

    # Check event
    events = Events.fetch_registration_events(registration.id, applicant_visible_events_only=False)
    assert len(events) == 1
    details = json.loads(events[0].details)
    change = details["changes"][0]
    assert change["field"] == "secondaryContact.emailAddress"


def test_update_registration_platform_business_details(session):
    """Test updating platform businessDetails emails."""
    user = User(username="platformuser", firstname="Platform", lastname="User")
    session.add(user)
    session.flush()

    registration = Registration(
        registration_type=Registration.RegistrationType.PLATFORM,
        registration_number="PLT-BIZ",
        sbc_account_id=77777,
        status=RegistrationStatus.ACTIVE,
        user_id=user.id,
        start_date=datetime.now(timezone.utc),
        expiry_date=datetime.now(timezone.utc),
        registration_json={
            "businessDetails": {
                "noticeOfNonComplianceEmail": "old-noc@example.com",
                "takeDownRequestEmail": "old-takedown@example.com",
            }
        },
    )
    session.add(registration)
    session.flush()

    update_data = {
        "businessDetails": {
            "noticeOfNonComplianceEmail": "new-noc@example.com",
            "takeDownRequestEmail": "new-takedown@example.com",
        }
    }
    updated_reg = RegistrationService.update_registration(registration, update_data, user)

    assert updated_reg.registration_json["businessDetails"]["noticeOfNonComplianceEmail"] == "new-noc@example.com"
    assert updated_reg.registration_json["businessDetails"]["takeDownRequestEmail"] == "new-takedown@example.com"

    # Check event tracks both changes
    events = Events.fetch_registration_events(registration.id, applicant_visible_events_only=False)
    assert len(events) == 1
    details = json.loads(events[0].details)
    assert len(details["changes"]) == 2
