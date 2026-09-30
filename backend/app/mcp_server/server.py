"""MCP server exposing TutorIA's tutor to MCP clients (Fase 3.II, scenario B).

Runs in the same process as the FastAPI app and is mounted at /mcp over
streamable HTTP (see app.main). It is only a transport: every tutoring turn is
delegated to chat_service.process_chat_turn, the same code the REST router uses.
"""
from mcp.server.fastmcp import FastMCP

# Accessed as database.async_session (not imported by name) so the tool always
# uses the sessionmaker currently bound to the app, the same one get_db uses.
from app.db import database
from app.services.chat_service import (
    SessionNotFound,
    StudentNotFound,
    process_chat_turn,
)

# Mounted at /mcp by app.main, so the endpoint itself lives at the mount root.
mcp = FastMCP("tutoria", streamable_http_path="/")


@mcp.tool()
async def chat_with_tutor(
    student_id: int,
    message: str,
    session_id: int | None = None,
) -> dict:
    """Send a student's message to TutorIA, the pedagogical AI tutor, and get its reply.

    TutorIA adapts its teaching strategy to the student's level, uses the
    course material when the session is linked to a module, and keeps the
    conversation history per session. The reply is written for the student,
    in Spanish.

    Args:
        student_id: TutorIA's internal student id (not the Open edX user id).
        message: The student's message, verbatim.
        session_id: Id of an existing tutoring session to continue. Omit it to
            start a new session; reuse the returned session_id on later turns
            to keep the conversation context.

    Returns:
        {"assistant_message": the tutor's reply,
         "session_id": the session this turn belongs to}
    """
    # TODO(fase-3b): map Open edX user ids to TutorIA student ids.
    async with database.async_session() as db:
        try:
            result = await process_chat_turn(db, student_id, message, session_id)
        except StudentNotFound:
            raise ValueError(f"Student not found: student_id={student_id}")
        except SessionNotFound:
            raise ValueError(
                f"Session not found: session_id={session_id} "
                f"does not exist or does not belong to student_id={student_id}"
            )

    return {"assistant_message": result.response, "session_id": result.session_id}
