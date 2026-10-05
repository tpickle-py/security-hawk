"""Views for Security Hawk Model Context Protocol (MCP) server."""

from __future__ import annotations

import json
import logging

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from mcp.auth import get_mcp_config, verify_mcp_request
from mcp.tools import MCP_TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)


def _find_tool_category(tool_name: str) -> str:
    for t in MCP_TOOL_DEFINITIONS:
        if t["name"] == tool_name:
            return t.get("category", "read")
    return "read"


@csrf_exempt
def rpc_endpoint(request: HttpRequest) -> JsonResponse:
    """JSON-RPC 2.0 endpoint for MCP clients."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        body = json.loads(request.body)
    except Exception as e:
        return JsonResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {e}"}}, status=400)

    msg_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    conf = get_mcp_config()
    if not conf["enabled"]:
        return JsonResponse(
            {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32600, "message": "MCP server is disabled."}},
            status=403,
        )

    if method == "tools/list":
        # Check read access
        allowed, err_msg = verify_mcp_request(request, "read")
        if not allowed:
            return JsonResponse({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": err_msg}}, status=403)

        return JsonResponse({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": MCP_TOOL_DEFINITIONS}})

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return JsonResponse({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": "Missing tool name."}}, status=400)

        category = _find_tool_category(tool_name)
        allowed, err_msg = verify_mcp_request(request, category)
        if not allowed:
            return JsonResponse({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": err_msg}}, status=403)

        result = execute_tool(tool_name, arguments, mask_sensitive=conf["mask_sensitive_data"])
        return JsonResponse({"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(result)}]}})

    return JsonResponse({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}, status=404)


def list_tools(request: HttpRequest) -> JsonResponse:
    """REST endpoint returning available MCP tools."""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    allowed, err_msg = verify_mcp_request(request, "read")
    if not allowed:
        return JsonResponse({"error": err_msg}, status=403)

    return JsonResponse({"tools": MCP_TOOL_DEFINITIONS})


@csrf_exempt
def execute_tool_view(request: HttpRequest) -> JsonResponse:
    """REST endpoint to execute an MCP tool."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except Exception as e:
        return JsonResponse({"error": f"Invalid JSON payload: {e}"}, status=400)

    tool_name = data.get("name")
    arguments = data.get("arguments", {})

    if not tool_name:
        return JsonResponse({"error": "Missing tool name"}, status=400)

    category = _find_tool_category(tool_name)
    allowed, err_msg = verify_mcp_request(request, category)
    if not allowed:
        return JsonResponse({"error": err_msg}, status=403)

    conf = get_mcp_config()
    res = execute_tool(tool_name, arguments, mask_sensitive=conf["mask_sensitive_data"])
    return JsonResponse(res)


def status_view(request: HttpRequest) -> JsonResponse:
    """Return status and active access level of the MCP endpoint."""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    conf = get_mcp_config()
    return JsonResponse(
        {
            "status": "active" if conf["enabled"] else "disabled",
            "access_level": conf["access_level"],
            "api_key_required": bool(conf.get("api_key", "").strip()),
            "mask_sensitive_data": conf["mask_sensitive_data"],
            "tools_count": len(MCP_TOOL_DEFINITIONS),
        }
    )
