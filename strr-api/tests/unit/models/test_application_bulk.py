"""Tests for bulk application query helpers."""

from datetime import datetime, timedelta, timezone

from strr_api.enums.enum import ApplicationType, RegistrationStatus
from strr_api.models import Application, Registration, User
from strr_api.models.application import Application as AppModel


def test_get_all_by_registration_ids_groups_and_orders(session, random_string, random_integer):
    user = User()
    session.add(user)
    session.flush()

    r1 = Registration(
        registration_type=Registration.RegistrationType.HOST,
        registration_number=random_string(12),
        sbc_account_id=random_integer(),
        status=RegistrationStatus.ACTIVE,
        user_id=user.id,
        start_date=datetime.now(timezone.utc),
        expiry_date=datetime.now(timezone.utc) + timedelta(days=365),
    )
    r2 = Registration(
        registration_type=Registration.RegistrationType.HOST,
        registration_number=random_string(12),
        sbc_account_id=random_integer(),
        status=RegistrationStatus.ACTIVE,
        user_id=user.id,
        start_date=datetime.now(timezone.utc),
        expiry_date=datetime.now(timezone.utc) + timedelta(days=365),
    )
    session.add_all([r1, r2])
    session.flush()

    base = datetime.now(timezone.utc)
    a1_old = Application(
        application_json={"registration": {"strRequirements": {}}},
        application_number=Application.generate_unique_application_number(),
        registration_id=r1.id,
        submitter_id=user.id,
        type=ApplicationType.REGISTRATION.value,
        registration_type=Registration.RegistrationType.HOST,
        status=AppModel.Status.FULL_REVIEW_APPROVED,
        application_date=base - timedelta(days=2),
    )
    a1_new = Application(
        application_json={"registration": {"strRequirements": {}}},
        application_number=Application.generate_unique_application_number(),
        registration_id=r1.id,
        submitter_id=user.id,
        type=ApplicationType.REGISTRATION.value,
        registration_type=Registration.RegistrationType.HOST,
        status=AppModel.Status.PAID,
        application_date=base,
    )
    a2_only = Application(
        application_json={"registration": {"strRequirements": {}}},
        application_number=Application.generate_unique_application_number(),
        registration_id=r2.id,
        submitter_id=user.id,
        type=ApplicationType.REGISTRATION.value,
        registration_type=Registration.RegistrationType.HOST,
        status=AppModel.Status.DRAFT,
        application_date=base - timedelta(days=1),
    )
    session.add_all([a1_old, a1_new, a2_only])
    session.commit()

    grouped = Application.get_all_by_registration_ids([r1.id, r2.id, 999999999])
    assert set(grouped.keys()) == {r1.id, r2.id, 999999999}
    assert grouped[999999999] == []
    assert [a.application_number for a in grouped[r1.id]] == [a1_new.application_number, a1_old.application_number]
    assert len(grouped[r2.id]) == 1
    assert grouped[r2.id][0].application_number == a2_only.application_number


def test_get_all_by_registration_ids_empty_input():
    assert Application.get_all_by_registration_ids([]) == {}
