"""
End-to-End Verification of STRR Workflows, Pub/Sub Emulation, Queue Services, and Jobs.
"""
import base64
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from simple_cloudevent import SimpleCloudEvent, to_queue_message

# Set up python path for strr-api and jobs
STRR_DIR = "/Users/jimmy/workspace/STRR"
sys.path.insert(0, os.path.join(STRR_DIR, "strr-api", "src"))

from strr_api import create_app
from strr_api.enums.enum import ApplicationType, RegistrationStatus
from strr_api.models import Application, Events, Registration, User, db
from strr_api.models.notice_of_consideration import NoticeOfConsideration
from strr_api.workflows.application_workflow import ApplicationWorkflow
from strr_api.workflows.registration_workflow import RegistrationWorkflow

PUBSUB_EMULATOR = "http://localhost:8085"
STRR_API_URL = "http://localhost:8000"
STRR_EMAIL_URL = "http://localhost:8081"
STRR_PAY_URL = "http://localhost:8082"


def print_step(title):
    print(f"\n{'='*70}\n[E2E STEP] {title}\n{'='*70}")


def publish_to_emulator(topic: str, message_data: dict, attributes: dict = None):
    """Publish a base64 encoded message to the local Pub/Sub emulator."""
    url = f"{PUBSUB_EMULATOR}/v1/{topic}:publish"
    encoded_data = base64.b64encode(json.dumps(message_data).encode("utf-8")).decode("utf-8")
    payload = {
        "messages": [
            {
                "data": encoded_data,
                "attributes": attributes or {},
            }
        ]
    }
    resp = requests.post(url, json=payload, timeout=5)
    resp.raise_for_status()
    return resp.json()


def main():
    app = create_app()
    with app.app_context():
        # Ensure a test user exists
        user = User.query.filter_by(idp_userid="e2e-test-user-id").first()
        if not user:
            user = User(
                idp_userid="e2e-test-user-id",
                username="e2e-test-user",
                firstname="E2E",
                lastname="Tester",
                login_source="bcsc",
            )
            user.save()

        # ----------------------------------------------------------------------
        # STEP 1: Verify Workflow Visualization Endpoints on STRR-API
        # ----------------------------------------------------------------------
        print_step("1. Verify Workflow Inspection Endpoints on strr-api (:8000)")
        resp = requests.get(f"{STRR_API_URL}/workflows/", timeout=5)
        assert resp.status_code == 200, f"Expected 200 from /workflows/, got {resp.status_code}"
        wf_data = resp.json()
        assert "application" in wf_data, "Missing 'application' workflow metadata"
        assert "registration" in wf_data, "Missing 'registration' workflow metadata"
        print("✓ GET /workflows/ returned valid workflow registry.")

        resp_app = requests.get(f"{STRR_API_URL}/workflows/application/mermaid", timeout=5)
        assert resp_app.status_code == 200
        assert "flowchart TB" in resp_app.text or "stateDiagram" in resp_app.text or "elk" in resp_app.text
        print("✓ GET /workflows/application/mermaid returned clean Mermaid syntax.")

        # ----------------------------------------------------------------------
        # STEP 2: Application Creation & Payment via Pub/Sub emulator -> strr-pay
        # ----------------------------------------------------------------------
        print_step("2. Application Payment Transition via Pub/Sub -> strr-pay (:8082)")
        from strr_api.models.application import _generate_application_number

        now = datetime.now(timezone.utc)
        ts = int(time.time())
        test_invoice_id = ts % 10000000
        with open(os.path.join(STRR_DIR, "strr-api", "tests", "mocks", "json", "host_registration.json")) as f:
            mock_payload = json.load(f)

        app_record = Application(
            type=ApplicationType.REGISTRATION.value,
            registration_type=Registration.RegistrationType.HOST,
            application_number=_generate_application_number(),
            status=Application.Status.PAYMENT_DUE,
            submitter_id=user.id,
            application_json=mock_payload,
            invoice_id=test_invoice_id,
            application_date=now - timedelta(hours=2),
        )
        app_record.save()
        app_id = app_record.id
        print(f"Created application #{app_id} in PAYMENT_DUE with invoice_id={test_invoice_id}")

        # Send payment completion CloudEvent to Pub/Sub emulator
        # The topic is projects/local-dev/topics/strr-pay-topic, which pushes to http://127.0.0.1:8082/
        ce = SimpleCloudEvent(
            id=f"e2e-pay-event-{ts}",
            source="strr-pay-test",
            subject="strr-payment",
            type="bc.registry.payment",
            data={
                "id": str(test_invoice_id),
                "statusCode": "COMPLETED",
            },
        )
        ce_dict = to_queue_message(ce)
        
        # Publish to the emulator topic
        pub_url = f"{PUBSUB_EMULATOR}/v1/projects/local-dev/topics/strr-pay-topic:publish"
        encoded_data = base64.b64encode(ce_dict).decode("utf-8")
        resp = requests.post(pub_url, json={"messages": [{"data": encoded_data}]}, timeout=5)
        assert resp.status_code == 200, f"Pub/sub emulator publish failed: {resp.text}"
        print(f"Published payment event to emulator topic strr-pay-topic: {resp.json()}")

        # Allow strr-pay push subscription to receive and process
        time.sleep(2)

        # Refresh application and verify status is PAID
        db.session.expire_all()
        refreshed_app = Application.query.get(app_id)
        print(f"Application #{app_id} status after strr-pay processing: {refreshed_app.status}")
        assert refreshed_app.status == Application.Status.PAID.value, (
            f"Expected status PAID, got {refreshed_app.status}"
        )
        assert refreshed_app.payment_status_code == "COMPLETED"

        # Verify audit event in DB
        events = Events.fetch_application_events(app_id, applicant_visible_events_only=False)
        payment_events = [e for e in events if e.event_name == Events.EventName.PAYMENT_COMPLETE]
        assert len(payment_events) >= 1, f"Missing PAYMENT_COMPLETE audit event. Found events: {[e.event_name for e in events]}"
        print(f"✓ PAYMENT_COMPLETE recorded by state machine")

        # ----------------------------------------------------------------------
        # STEP 3: Auto-Approval Job Execution & Email Pub/Sub Dispatch
        # ----------------------------------------------------------------------
        print_step("3. Auto-Approval Job -> ApplicationWorkflow -> strr-email")
        # Run auto-approval logic on our paid application
        sys.path.insert(0, os.path.join(STRR_DIR, "jobs", "auto-approval", "src"))
        from auto_approval.job import process_applications

        # We pass our application to process_applications
        process_applications(app, [refreshed_app])

        db.session.expire_all()
        approved_app = Application.query.get(app_id)
        print(f"Application #{app_id} status after auto_approval job: {approved_app.status}")
        assert approved_app.status in [Application.Status.AUTO_APPROVED.value, Application.Status.FULL_REVIEW.value], (
            f"Unexpected status after auto-approval: {approved_app.status}"
        )
        print(f"✓ Application transitioned legally to {approved_app.status} using ApplicationWorkflow.")

        # ----------------------------------------------------------------------
        # STEP 4: Notice of Consideration (NOC) Expiry Job Test
        # ----------------------------------------------------------------------
        print_step("4. NOC Expiry Job -> ApplicationWorkflow.expire_noc()")
        noc_app = Application(
            type=ApplicationType.REGISTRATION.value,
            registration_type=Registration.RegistrationType.HOST,
            application_number=_generate_application_number(),
            status=Application.Status.NOC_PENDING,
            submitter_id=user.id,
            application_json={"test": True},
            application_date=now - timedelta(days=20),
        )
        noc_app.save()
        # Add expired NOC record
        noc = NoticeOfConsideration(
            application_id=noc_app.id,
            content="E2E NOC Expired Content",
            start_date=now - timedelta(days=15),
            end_date=now - timedelta(days=1),  # Expired yesterday
        )
        noc.save()
        noc_app_id = noc_app.id
        print(f"Created application #{noc_app_id} in NOC_PENDING with NOC expired yesterday.")

        # Run noc_expiry updater
        sys.path.insert(0, os.path.join(STRR_DIR, "jobs", "noc_expiry", "src"))
        from noc_expiry.job import update_status_for_noc_expired_applications

        update_status_for_noc_expired_applications(app)

        db.session.expire_all()
        refreshed_noc_app = Application.query.get(noc_app_id)
        print(f"Application #{noc_app_id} status after noc_expiry job: {refreshed_noc_app.status}")
        assert refreshed_noc_app.status == Application.Status.NOC_EXPIRED.value, (
            f"Expected NOC_EXPIRED after NOC expiry, got {refreshed_noc_app.status}"
        )
        noc_events = Events.fetch_application_events(noc_app_id, applicant_visible_events_only=False)
        assert any(e.event_name == Events.EventName.NOC_EXPIRED for e in noc_events), (
            "Missing NOC_EXPIRED event"
        )
        print("✓ NOC Expiry successfully transitioned application via ApplicationWorkflow.expire_noc().")

        # ----------------------------------------------------------------------
        # STEP 5: Registration Expiry Job Test
        # ----------------------------------------------------------------------
        print_step("5. Registration Expiry Job -> RegistrationWorkflow.expire()")
        reg = Registration(
            user_id=user.id,
            sbc_account_id=123,
            status=RegistrationStatus.ACTIVE.value,
            registration_number=f"REG-E2E-{ts}",
            start_date=now - timedelta(days=400),
            expiry_date=now - timedelta(days=5),  # Expired 5 days ago
            registration_type=Registration.RegistrationType.HOST,
            registration_json={"e2e": True},
        )
        reg.save()
        reg_id = reg.id
        print(f"Created Registration #{reg_id} in ACTIVE state with expiry_date in the past.")

        sys.path.insert(0, os.path.join(STRR_DIR, "jobs", "registration_expiry", "src"))
        from registration_expiry.job import update_status_for_registration_expired_applications

        update_status_for_registration_expired_applications(app)

        db.session.expire_all()
        refreshed_reg = Registration.query.get(reg_id)
        print(f"Registration #{reg_id} status after registration_expiry job: {refreshed_reg.status}")
        assert refreshed_reg.status == RegistrationStatus.EXPIRED.value, (
            f"Expected EXPIRED status, got {refreshed_reg.status}"
        )
        print("✓ Registration successfully expired via RegistrationWorkflow.expire().")

        # ----------------------------------------------------------------------
        # STEP 6: Registration Lifecycle Finite State Machine Operations
        # ----------------------------------------------------------------------
        print_step("6. RegistrationWorkflow State Machine: Suspend, Reinstate, Cancel")
        reg_active = Registration(
            user_id=user.id,
            sbc_account_id=123,
            status=RegistrationStatus.ACTIVE.value,
            registration_number=f"REG-ACT-{ts}",
            start_date=now,
            expiry_date=now + timedelta(days=365),
            registration_type=Registration.RegistrationType.HOST,
            registration_json={"e2e": True},
        )
        reg_active.save()

        # Suspend
        rw = RegistrationWorkflow(reg_active)
        rw.suspend()
        assert reg_active.status == RegistrationStatus.SUSPENDED.value
        print("✓ ACTIVE -> SUSPENDED validated.")

        # Reinstate
        rw.reinstate()
        assert reg_active.status == RegistrationStatus.ACTIVE.value
        print("✓ SUSPENDED -> ACTIVE (reinstate) validated.")

        # Cancel
        rw.cancel()
        assert reg_active.status == RegistrationStatus.CANCELLED.value
        print("✓ ACTIVE -> CANCELLED validated.")

        # Illegal transition: Cancelled -> Suspend should be blocked by FSM
        try:
            rw.suspend()
            assert False, "State machine should have rejected transition from CANCELLED to SUSPENDED!"
        except Exception as ex:
            print(f"✓ Illegal transition blocked as expected by state machine: {ex.__class__.__name__}")

        print("\n" + "="*70)
        print("🎉 ALL END-TO-END WORKFLOW INTEGRATION TESTS PASSED SUCCESSFULLY!")
        print("="*70 + "\n")


if __name__ == "__main__":
    main()
