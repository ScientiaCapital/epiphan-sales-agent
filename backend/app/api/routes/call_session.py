"""WebSocket and REST endpoints for Voice AI call session integration.

WebSocket: GET /ws/call-session?token=xxx
  - Bidirectional JSON messaging during live calls
  - Auth via JWT query parameter (WebSocket doesn't support custom headers)

REST fallback: /api/call-session/*
  - Same CallSessionManager, same logic, just HTTP instead of WS
  - Use if the Voice AI app doesn't support WebSocket
"""

import contextlib
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.data.call_session_schemas import (
    CallLoggedData,
    ClientMessage,
    ClientMessageType,
    CompetitorQueryData,
    CompetitorQueryRequest,
    CompetitorResponseData,
    EndCallData,
    EndSessionRequest,
    ErrorData,
    ObjectionData,
    ObjectionRequest,
    ObjectionResponseData,
    ServerMessage,
    ServerMessageType,
    SessionStateResponse,
    StartCallData,
    StartSessionRequest,
    StartSessionResponse,
)
from app.middleware.auth import get_current_user, require_auth
from app.services.call_session.manager import call_session_manager

logger = logging.getLogger(__name__)

# REST router with JWT auth
router = APIRouter(prefix="/api/call-session", tags=["call-session"], dependencies=[Depends(require_auth)])

# WebSocket router (no prefix — mounted directly on app)
ws_router = APIRouter(tags=["call-session-ws"])


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@ws_router.websocket("/ws/call-session")
async def call_session_websocket(
    websocket: WebSocket,
    token: str = Query(default=""),
) -> None:
    """WebSocket endpoint for live call session support.

    Protocol: JSON messages as {"type": "...", "data": {...}}

    Auth: JWT token passed as query parameter (?token=xxx).
    WebSocket doesn't support custom headers during handshake.
    """
    # Validate JWT before accepting connection
    try:
        await get_current_user(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid or missing token")
        return

    await websocket.accept()

    session_id: str | None = None

    try:
        while True:
            raw = await websocket.receive_json()

            try:
                msg = ClientMessage(**raw)
            except Exception:
                await _send_error(websocket, "Invalid message format")
                continue

            response = await _handle_message(msg, session_id)

            # Track session_id from start_call response
            if msg.type == ClientMessageType.START_CALL and "session_id" in response.get("data", {}):
                session_id = response["data"]["session_id"]

            await websocket.send_json(response)

            # Close after end_call
            if msg.type == ClientMessageType.END_CALL:
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", extra={"session_id": session_id})
    except Exception:
        logger.exception("WebSocket error", extra={"session_id": session_id})
        await _send_error(websocket, "Internal server error")


async def _handle_message(
    msg: ClientMessage,
    session_id: str | None,
) -> dict[str, Any]:
    """Route a client message to the appropriate handler."""
    if msg.type == ClientMessageType.START_CALL:
        return await _handle_start_call(msg.data)
    elif msg.type == ClientMessageType.COMPETITOR_QUERY:
        if not session_id:
            return _error_response("No active session — send start_call first")
        return await _handle_competitor_query(session_id, msg.data)
    elif msg.type == ClientMessageType.OBJECTION:
        if not session_id:
            return _error_response("No active session — send start_call first")
        return await _handle_objection(session_id, msg.data)
    elif msg.type == ClientMessageType.END_CALL:
        if not session_id:
            return _error_response("No active session — send start_call first")
        return await _handle_end_call(session_id, msg.data)
    else:
        return _error_response(f"Unknown message type: {msg.type}")


async def _handle_start_call(data: dict[str, Any]) -> dict[str, Any]:
    """Handle start_call message — generate brief and create session."""
    try:
        parsed = StartCallData(**data)
    except Exception:
        return _error_response("Invalid start_call data — need lead_id")

    session, brief_dict = await call_session_manager.start_session(
        lead_id=parsed.lead_id,
        lead_email=parsed.lead_email,
    )

    response_data = brief_dict.copy()
    response_data["session_id"] = session.session_id

    return ServerMessage(
        type=ServerMessageType.CALL_BRIEF,
        data=response_data,
    ).model_dump(mode="json")


async def _handle_competitor_query(session_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Handle competitor_query message — return battlecard response."""
    try:
        parsed = CompetitorQueryData(**data)
    except Exception:
        return _error_response("Invalid competitor_query data — need competitor_name and context")

    result = await call_session_manager.get_competitor_response(
        session_id=session_id,
        competitor_name=parsed.competitor_name,
        context=parsed.context,
    )

    if "error" in result:
        return _error_response(result["error"])

    return ServerMessage(
        type=ServerMessageType.COMPETITOR_RESPONSE,
        data=CompetitorResponseData(
            response=result.get("response", ""),
            proof_points=result.get("proof_points", []),
            follow_up=result.get("follow_up"),
        ).model_dump(mode="json"),
    ).model_dump(mode="json")


async def _handle_objection(session_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Handle objection message — return persona-matched response."""
    try:
        parsed = ObjectionData(**data)
    except Exception:
        return _error_response("Invalid objection data — need objection_text")

    result = await call_session_manager.get_objection_response(
        session_id=session_id,
        objection_text=parsed.objection_text,
    )

    if "error" in result:
        return _error_response(result["error"])

    return ServerMessage(
        type=ServerMessageType.OBJECTION_RESPONSE,
        data=ObjectionResponseData(
            response=result.get("response", ""),
            discovery_question=result.get("discovery_question"),
            persona_context=result.get("persona_context"),
        ).model_dump(mode="json"),
    ).model_dump(mode="json")


async def _handle_end_call(session_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Handle end_call message — log outcome and close session."""
    try:
        parsed = EndCallData(**data)
    except Exception:
        return _error_response("Invalid end_call data — need disposition and result")

    result = await call_session_manager.end_session(
        session_id=session_id,
        disposition=parsed.disposition,
        result=parsed.result,
        notes=parsed.notes,
        duration_seconds=parsed.duration_seconds,
        objections=parsed.objections,
        competitor_mentioned=parsed.competitor_mentioned,
    )

    if "error" in result and result.get("outcome_id") == "failed":
        return _error_response(result["error"])

    return ServerMessage(
        type=ServerMessageType.CALL_LOGGED,
        data=CallLoggedData(
            outcome_id=result.get("outcome_id", ""),
            follow_up_date=result.get("follow_up_date"),
            follow_up_type=result.get("follow_up_type"),
        ).model_dump(mode="json"),
    ).model_dump(mode="json")


def _error_response(message: str) -> dict[str, Any]:
    """Build a server error message."""
    return ServerMessage(
        type=ServerMessageType.ERROR,
        data=ErrorData(message=message).model_dump(mode="json"),
    ).model_dump(mode="json")


async def _send_error(websocket: WebSocket, message: str) -> None:
    """Send an error message over WebSocket."""
    with contextlib.suppress(Exception):
        await websocket.send_json(_error_response(message))


# =============================================================================
# REST Fallback Endpoints
# =============================================================================


@router.post("/start", response_model=StartSessionResponse)
async def start_session(request: StartSessionRequest) -> StartSessionResponse:
    """Start a call session and get the call brief.

    REST equivalent of the WebSocket start_call message.
    Returns session_id + full call brief for the lead.
    """
    session, brief_dict = await call_session_manager.start_session(
        lead_id=request.lead_id,
        lead_email=request.lead_email,
    )

    return StartSessionResponse(
        session_id=session.session_id,
        brief=brief_dict,
        brief_id=session.brief_id,
    )


@router.post("/{session_id}/competitor")
async def competitor_query(
    session_id: str,
    request: CompetitorQueryRequest,
) -> dict[str, Any]:
    """Query competitor intelligence during a call.

    REST equivalent of the WebSocket competitor_query message.
    """
    session = call_session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await call_session_manager.get_competitor_response(
        session_id=session_id,
        competitor_name=request.competitor_name,
        context=request.context,
    )

    return result


@router.post("/{session_id}/objection")
async def objection_query(
    session_id: str,
    request: ObjectionRequest,
) -> dict[str, Any]:
    """Get objection handling response during a call.

    REST equivalent of the WebSocket objection message.
    """
    session = call_session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await call_session_manager.get_objection_response(
        session_id=session_id,
        objection_text=request.objection_text,
    )

    return result


@router.post("/{session_id}/end")
async def end_session(
    session_id: str,
    request: EndSessionRequest,
) -> dict[str, Any]:
    """End a call session and log the outcome.

    REST equivalent of the WebSocket end_call message.
    """
    session = call_session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await call_session_manager.end_session(
        session_id=session_id,
        disposition=request.disposition,
        result=request.result,
        notes=request.notes,
        duration_seconds=request.duration_seconds,
        objections=request.objections,
        competitor_mentioned=request.competitor_mentioned,
    )

    return result


@router.get("/{session_id}", response_model=SessionStateResponse)
async def get_session(session_id: str) -> SessionStateResponse:
    """Get the current state of an active call session."""
    session = call_session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionStateResponse(
        session_id=session.session_id,
        lead_id=session.lead_id,
        lead_email=session.lead_email,
        brief_id=session.brief_id,
        started_at=session.started_at.isoformat(),
        objections_raised=session.objections_raised,
        competitors_mentioned=session.competitors_mentioned,
        persona_id=session.persona_id,
    )
