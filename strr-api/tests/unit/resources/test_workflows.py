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
"""Tests for unauthenticated /workflows diagram endpoints."""
from http import HTTPStatus


def test_list_workflows_directory(client):
    """Verify that /workflows/ returns workflow directory with mermaid.live URLs."""
    rv = client.get("/workflows/")
    assert rv.status_code == HTTPStatus.OK
    data = rv.json
    assert "application" in data
    assert "registration" in data
    assert data["application"]["view_url"].startswith("https://mermaid.live/view#pako:")
    assert data["registration"]["view_url"].startswith("https://mermaid.live/view#pako:")


def test_get_application_workflow_redirects_302(client):
    """Verify that /workflows/application returns 302 redirecting to mermaid.live/view."""
    rv = client.get("/workflows/application")
    assert rv.status_code == HTTPStatus.FOUND
    assert rv.headers.get("Location").startswith("https://mermaid.live/view#pako:")


def test_get_registration_workflow_redirects_302(client):
    """Verify that /workflows/registration returns 302 redirecting to mermaid.live/view."""
    rv = client.get("/workflows/registration")
    assert rv.status_code == HTTPStatus.FOUND
    assert rv.headers.get("Location").startswith("https://mermaid.live/view#pako:")


def test_get_workflow_edit_mode_redirect(client):
    """Verify that ?mode=edit redirects to mermaid.live/edit."""
    rv = client.get("/workflows/application?mode=edit")
    assert rv.status_code == HTTPStatus.FOUND
    assert rv.headers.get("Location").startswith("https://mermaid.live/edit#pako:")


def test_get_workflow_raw_mermaid_format(client):
    """Verify that ?format=mermaid returns raw text/plain Mermaid code with TB direction."""
    rv = client.get("/workflows/application?format=mermaid")
    assert rv.status_code == HTTPStatus.OK
    assert "text/plain" in rv.content_type
    assert rv.text.startswith("stateDiagram-v2")
    assert "direction TB" in rv.text
    assert "draft --> payment_due" in rv.text


def test_get_workflow_raw_mermaid_endpoint(client):
    """Verify that /workflows/<name>/mermaid route returns raw text/plain Mermaid code."""
    rv = client.get("/workflows/registration/mermaid")
    assert rv.status_code == HTTPStatus.OK
    assert "text/plain" in rv.content_type
    assert rv.text.startswith("stateDiagram-v2")
    assert "direction TB" in rv.text
    assert "active --> suspended" in rv.text


def test_get_workflow_json_format(client):
    """Verify that ?format=json returns valid JSON diagram structure, layout, and live URL."""
    rv = client.get("/workflows/application?format=json")
    assert rv.status_code == HTTPStatus.OK
    assert "application/json" in rv.content_type
    data = rv.json
    assert data["workflow"] == "application"
    assert data["format"] == "mermaid"
    assert data["direction"] == "TB"
    assert data["layout"] == "elk"
    assert data["live_url"].startswith("https://mermaid.live/view#pako:")
    assert "stateDiagram-v2" in data["diagram"]


def test_get_nonexistent_workflow_returns_404(client):
    """Verify that an unknown workflow returns 404."""
    rv = client.get("/workflows/nonexistent_workflow")
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert "error" in rv.json
