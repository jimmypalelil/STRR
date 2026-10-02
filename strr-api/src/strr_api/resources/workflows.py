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
"""Endpoints to inspect and visualize state machine workflows via Mermaid."""
import base64
import json
import zlib
from http import HTTPStatus

from flask import Blueprint, Response, jsonify, redirect, request
from statemachine.contrib.diagram import MermaidGraphMachine

from strr_api.workflows.application_workflow import ApplicationWorkflow
from strr_api.workflows.registration_workflow import RegistrationWorkflow

bp = Blueprint("workflows", __name__)

WORKFLOWS = {
    "application": {
        "title": "STRR Application Lifecycle",
        "description": "State machine governing application review, payment, NOC, approvals, and terminal states.",
        "class": ApplicationWorkflow,
    },
    "registration": {
        "title": "STRR Registration Lifecycle",
        "description": "State machine governing certificate registration, active periods, suspensions, renewals, and cancellations.",
        "class": RegistrationWorkflow,
    },
}


def build_mermaid_live_url(
    mermaid_code: str,
    mode: str = "view",
    layout: str = "elk",
) -> str:
    """Build a compressed, shareable mermaid.live URL using pako deflate format with clean ELK edge routing."""
    mermaid_config = {
        "theme": "default",
        "layout": layout,
        "elk": {
            "mergeEdges": False,
            "nodePlacementStrategy": "BRANDES_KOEPF",
            "cycleBreakingStrategy": "GREEDY",
        },
    }

    # Prepend front-matter configuration so it renders without edge bundling anywhere
    if not mermaid_code.startswith("---"):
        frontmatter = (
            f"---\n"
            f"config:\n"
            f"  layout: {layout}\n"
            f"  elk:\n"
            f"    mergeEdges: false\n"
            f"    nodePlacementStrategy: BRANDES_KOEPF\n"
            f"---\n"
        )
        mermaid_code = frontmatter + mermaid_code

    payload = {
        "code": mermaid_code,
        "mermaid": json.dumps(mermaid_config, indent=2),
        "autoSync": True,
        "updateDiagram": True,
    }
    json_bytes = json.dumps(payload).encode("utf-8")
    compressed = zlib.compress(json_bytes, level=9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    return f"https://mermaid.live/{mode}#pako:{encoded}"


def render_mermaid_for_workflow(workflow_cls, direction: str = "TB") -> str:
    """Extract Mermaid code with specified layout direction (default TB to avoid edge crowding)."""
    machine = MermaidGraphMachine(workflow_cls)
    machine.direction = direction
    return machine.get_mermaid()


@bp.route("/", methods=["GET"])
def list_workflows():
    """
    List all available state machine workflows.
    ---
    tags:
      - workflows
    responses:
      200:
        description: Directory of available state machine workflows with direct mermaid.live URLs.
    """
    result = {}
    for name, info in WORKFLOWS.items():
        code = render_mermaid_for_workflow(info["class"], direction="TB")
        result[name] = {
            "title": info["title"],
            "description": info["description"],
            "view_url": build_mermaid_live_url(code, mode="view"),
            "edit_url": build_mermaid_live_url(code, mode="edit"),
            "raw_url": f"/workflows/{name}/mermaid",
        }
    return jsonify(result), HTTPStatus.OK


@bp.route("/<workflow_name>", methods=["GET"])
def get_workflow_diagram(workflow_name: str):
    """
    Get state machine diagram or 302 redirect to interactive visualizer.
    ---
    tags:
      - workflows
    parameters:
      - in: path
        name: workflow_name
        type: string
        required: true
        description: Workflow identifier
        enum: ["application", "registration"]
      - in: query
        name: format
        type: string
        required: false
        description: Response format (default redirects 302 to mermaid.live)
        enum: ["mermaid", "text", "json"]
      - in: query
        name: dir
        type: string
        required: false
        description: 'Layout direction (TB: top-to-bottom avoids edge bundling, LR: left-to-right)'
        enum: ["TB", "LR"]
        default: "TB"
      - in: query
        name: layout
        type: string
        required: false
        description: Diagram layout engine (elk prevents edge bundling, dagre is classic)
        enum: ["elk", "dagre"]
        default: "elk"
      - in: query
        name: mode
        type: string
        required: false
        description: Mermaid live viewer mode (view or edit)
        enum: ["view", "edit"]
        default: "view"
    responses:
      302:
        description: Redirect to interactive diagram on mermaid.live with compressed graph payload.
      200:
        description: Diagram returned in requested format (plain text or JSON).
      404:
        description: Workflow not found.
    """
    if workflow_name not in WORKFLOWS:
        return jsonify({
            "error": f"Workflow '{workflow_name}' not found. Available: {list(WORKFLOWS.keys())}"
        }), HTTPStatus.NOT_FOUND

    info = WORKFLOWS[workflow_name]
    workflow_cls = info["class"]

    direction = request.args.get("dir", "TB").upper()
    if direction not in ("TB", "LR"):
        direction = "TB"

    layout = request.args.get("layout", "elk").lower()
    if layout not in ("elk", "dagre"):
        layout = "elk"

    mermaid_code = render_mermaid_for_workflow(workflow_cls, direction=direction)

    output_format = request.args.get("format", "").lower()
    if output_format in ("text", "mermaid") or request.headers.get("Accept") == "text/plain":
        return Response(mermaid_code, mimetype="text/plain; charset=utf-8", status=HTTPStatus.OK)

    mode = "edit" if request.args.get("mode") == "edit" else "view"
    live_url = build_mermaid_live_url(mermaid_code, mode=mode, layout=layout)

    if output_format == "json":
        return jsonify({
            "workflow": workflow_name,
            "title": info["title"],
            "live_url": live_url,
            "direction": direction,
            "layout": layout,
            "format": "mermaid",
            "diagram": mermaid_code,
        }), HTTPStatus.OK

    # Default: 302 redirect directly to mermaid.live with the diagram embedded in the URL
    return redirect(live_url, code=HTTPStatus.FOUND)


@bp.route("/<workflow_name>/mermaid", methods=["GET"])
def get_raw_mermaid(workflow_name: str):
    """
    Get raw Mermaid stateDiagram-v2 definition.
    ---
    tags:
      - workflows
    parameters:
      - in: path
        name: workflow_name
        type: string
        required: true
        description: Workflow identifier
      - in: query
        name: dir
        type: string
        required: false
        description: 'Layout direction (TB: top-to-bottom, LR: left-to-right)'
        enum: ["TB", "LR"]
        default: "TB"
    responses:
      200:
        description: Raw Mermaid stateDiagram-v2 source text.
      404:
        description: Workflow not found.
    """
    if workflow_name not in WORKFLOWS:
        return jsonify({"error": f"Workflow '{workflow_name}' not found."}), HTTPStatus.NOT_FOUND

    direction = request.args.get("dir", "TB").upper()
    if direction not in ("TB", "LR"):
        direction = "TB"

    workflow_cls = WORKFLOWS[workflow_name]["class"]
    mermaid_code = render_mermaid_for_workflow(workflow_cls, direction=direction)
    return Response(mermaid_code, mimetype="text/plain; charset=utf-8", status=HTTPStatus.OK)
