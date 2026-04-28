#!/usr/bin/env python3
"""Synthetic high-volume seed for local performance testing.

Loads ``strr-api/.env`` via the normal ``Development`` config (``python-dotenv``).
Refuses to run unless ``DEPLOYMENT_ENV`` is a local-ish value or you pass
``--i-know-this-is-local``.

Example::

    cd strr-api
    export DEPLOYMENT_ENV=development
    poetry run python scripts/perf_seed_registrations.py --registrations 5000 --batch-size 500 --seed 42

Post-seed (use the same host/port/user/db as in ``.env``)::

    PGPASSWORD=\"$DATABASE_PASSWORD\" psql -h \"$DATABASE_HOST\" -p \"$DATABASE_PORT\" \\
      -U \"$DATABASE_USERNAME\" -d \"$DATABASE_NAME\" -c \"ANALYZE registrations; ANALYZE application;\"
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Project root: strr-api/
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

LOCAL_DEPLOYMENT_ENVS = frozenset({"development", "dev", "local", "sandbox"})


def _assert_safe_to_seed(*, force: bool) -> None:
    if force:
        return
    dep = (os.getenv("DEPLOYMENT_ENV") or "").strip().lower()
    if dep not in LOCAL_DEPLOYMENT_ENVS:
        raise SystemExit(
            "Refusing to seed: set DEPLOYMENT_ENV to one of "
            f"{sorted(LOCAL_DEPLOYMENT_ENVS)} (see .env), or pass --i-know-this-is-local."
        )


def _app_json(
    *,
    pr: bool,
    bl: bool,
    straa_exempt: bool,
    org_nm: str,
) -> dict:
    return {
        "header": {"registrationId": None},
        "registration": {
            "strRequirements": {
                "isPrincipalResidenceRequired": "true" if pr else "false",
                "isBusinessLicenceRequired": "true" if bl else "false",
                "isStraaExempt": "true" if straa_exempt else "false",
                "isStrProhibited": "false",
                "organizationNm": org_nm,
            }
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registrations", type=int, default=10_000, help="Total HOST registrations to insert.")
    parser.add_argument("--batch-size", type=int, default=500, help="Commit every N registrations.")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (reproducible rows).")
    parser.add_argument(
        "--renewal-fraction",
        type=float,
        default=0.12,
        help="Fraction of rows that get a non-draft RENEWAL application (after initial approval).",
    )
    parser.add_argument(
        "--provisional-fraction",
        type=float,
        default=0.15,
        help="Fraction of rows whose *latest* application is provisional (review-queue style).",
    )
    parser.add_argument(
        "--noc-fraction",
        type=float,
        default=0.04,
        help="Fraction of ACTIVE rows with noc_status=NOC_PENDING.",
    )
    parser.add_argument(
        "--set-aside-fraction",
        type=float,
        default=0.02,
        help="Fraction of rows with is_set_aside=true.",
    )
    parser.add_argument(
        "--i-know-this-is-local",
        action="store_true",
        help="Skip DEPLOYMENT_ENV guard (still uses DATABASE_* from .env).",
    )
    args = parser.parse_args()
    _assert_safe_to_seed(force=args.i_know_this_is_local)

    import random

    from strr_api import create_app
    from strr_api.config import Development
    from strr_api.enums.enum import ApplicationType, PropertyType, RegistrationNocStatus, RegistrationStatus
    from strr_api.models import Address, Contact, PropertyContact, Registration, RentalProperty, User
    from strr_api.models.application import Application
    from strr_api.models.db import db

    rng = random.Random(args.seed)
    app = create_app(Development)

    prefix = f"PERF{args.seed}"
    now = datetime.now(timezone.utc)

    with app.app_context():
        owner = User.query.filter_by(username="perf_seed_owner").one_or_none()
        if not owner:
            owner = User(
                username="perf_seed_owner",
                firstname="Perf",
                lastname="Seed",
                email="perf-seed@local.invalid",
                sub="00000000-0000-4000-8000-000000000001",
                iss="https://perf-seed.local",
                idp_userid="perf-seed-owner",
                login_source="IDIR",
            )
            db.session.add(owner)
            db.session.commit()

        adjudicator = User.query.filter_by(username="perf_adjudicator").one_or_none()
        if not adjudicator:
            adjudicator = User(
                username="perf_adjudicator",
                firstname="Perf",
                lastname="Adjudicator",
                email="perf-adjudicator@local.invalid",
                sub="00000000-0000-4000-8000-000000000002",
                iss="https://perf-seed.local",
                idp_userid="perf-adjudicator",
                login_source="IDIR",
            )
            db.session.add(adjudicator)
            db.session.commit()

        n = args.registrations
        batch_size = max(1, args.batch_size)

        for i in range(n):
            reg_num = f"{prefix}{i:09d}"
            # sbc_account_id must fit a 32-bit signed integer (Postgres INTEGER).
            sbc_id = 1_500_000_000 + (i % 100_000_000)

            u = rng.random()
            status = RegistrationStatus.ACTIVE
            if u < 0.05:
                status = RegistrationStatus.EXPIRED
            elif u < 0.08:
                status = RegistrationStatus.SUSPENDED
            elif u < 0.10:
                status = RegistrationStatus.CANCELLED

            noc_status = None
            if status == RegistrationStatus.ACTIVE and rng.random() < args.noc_fraction:
                noc_status = RegistrationNocStatus.NOC_PENDING

            is_set_aside = rng.random() < args.set_aside_fraction

            reviewer_id = adjudicator.id if rng.random() < 0.08 else None

            base = now - timedelta(days=120)
            rj = rng.random()
            if rj < 0.25:
                pr, bl, ex, org = True, False, False, "Maple Ridge"
            elif rj < 0.40:
                pr, bl, ex, org = False, True, False, "Surrey"
            elif rj < 0.55:
                pr, bl, ex, org = False, False, True, "Victoria"
            else:
                pr, bl, ex, org = False, False, False, "Vancouver"

            latest_status = Application.Status.FULL_REVIEW_APPROVED
            if rng.random() < args.provisional_fraction:
                latest_status = rng.choice(
                    [Application.Status.PROVISIONALLY_APPROVED, Application.Status.PROVISIONAL_REVIEW]
                )

            decider_id = None
            if latest_status in (
                Application.Status.FULL_REVIEW_APPROVED,
                Application.Status.AUTO_APPROVED,
                Application.Status.FULL_REVIEW,
            ):
                decider_id = adjudicator.id if rng.random() < 0.05 else None
            # Provisional "review queue" rows stay without registration-level decider
            else:
                decider_id = None

            reg = Registration(
                registration_type=Registration.RegistrationType.HOST.value,
                registration_number=reg_num,
                sbc_account_id=sbc_id,
                status=status,
                user_id=owner.id,
                start_date=now - timedelta(days=400),
                expiry_date=now + timedelta(days=30),
                reviewer_id=reviewer_id,
                decider_id=decider_id,
                noc_status=noc_status,
                is_set_aside=is_set_aside,
            )
            db.session.add(reg)
            db.session.flush()

            unit_addr = Address(
                country="CA",
                street_address=f"{1000 + (i % 500)} Perf St",
                city="Victoria",
                province="BC",
                postal_code="V8V1A1",
                street_number=str(100 + (i % 50)),
            )
            mail_addr = Address(
                country="CA",
                street_address=f"{2000 + (i % 300)} Mail Rd",
                city="Surrey",
                province="BC",
                postal_code="V3T0A1",
            )
            db.session.add_all([unit_addr, mail_addr])
            db.session.flush()

            contact = Contact(
                lastname=f"Host{i}",
                firstname="Perf",
                email=f"host{i}@perf.local",
                address_id=mail_addr.id,
            )
            db.session.add(contact)
            db.session.flush()

            rp = RentalProperty(
                registration_id=reg.id,
                address_id=unit_addr.id,
                property_type=PropertyType.SINGLE_FAMILY_HOME,
                ownership_type=RentalProperty.OwnershipType.OWN,
                is_principal_residence=True,
                rental_act_accepted=True,
                jurisdiction=rng.choice(
                    ["District of Maple Ridge", "City of Surrey", "City of Victoria", "City of Vancouver"]
                ),
                pr_required=rng.choice([True, False]),
                bl_required=rng.choice([True, False]),
            )
            db.session.add(rp)
            db.session.flush()

            pc = PropertyContact(
                property_id=rp.id,
                contact_id=contact.id,
                is_primary=True,
                contact_type=PropertyContact.ContactType.INDIVIDUAL,
            )
            db.session.add(pc)

            app1 = Application(
                application_number=Application.generate_unique_application_number(),
                application_json=_app_json(pr=pr, bl=bl, straa_exempt=ex, org_nm=org),
                registration_id=reg.id,
                submitter_id=owner.id,
                type=ApplicationType.REGISTRATION.value,
                registration_type=Registration.RegistrationType.HOST,
                status=Application.Status.FULL_REVIEW_APPROVED,
                application_date=base,
            )
            db.session.add(app1)

            app2 = Application(
                application_number=Application.generate_unique_application_number(),
                application_json=_app_json(pr=pr, bl=bl, straa_exempt=ex, org_nm=org),
                registration_id=reg.id,
                submitter_id=owner.id,
                type=ApplicationType.REGISTRATION.value,
                registration_type=Registration.RegistrationType.HOST,
                status=latest_status,
                application_date=base + timedelta(days=1),
            )
            db.session.add(app2)

            if rng.random() < args.renewal_fraction:
                app3 = Application(
                    application_number=Application.generate_unique_application_number(),
                    application_json=_app_json(pr=pr, bl=bl, straa_exempt=ex, org_nm=org),
                    registration_id=reg.id,
                    submitter_id=owner.id,
                    type=ApplicationType.RENEWAL.value,
                    registration_type=Registration.RegistrationType.HOST,
                    status=Application.Status.PAID,
                    application_date=base + timedelta(days=2),
                )
                db.session.add(app3)

            if (i + 1) % batch_size == 0:
                db.session.commit()
                print(f"committed {i + 1}/{n}", flush=True)

        db.session.commit()
        print(f"done: inserted {n} registrations with prefix {prefix}", flush=True)


if __name__ == "__main__":
    main()
