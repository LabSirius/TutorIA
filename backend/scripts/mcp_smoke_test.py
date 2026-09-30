"""Smoke test for TutorIA's MCP server (tool: chat_with_tutor).

Connects over streamable HTTP, lists the tools, sends one chat turn and prints
the tutor's reply and the session id. Exits with a non-zero code on failure.

Requirements: the backend running, a student with the given id and the chat
model pulled in Ollama. The script ships in the backend image, where `mcp` is
already installed.

Usage (from the repository root):
    docker exec -it tutoria_backend python scripts/mcp_smoke_test.py [URL] [STUDENT_ID]
"""
import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

DEFAULT_URL = "http://localhost:8000/mcp/"
DEFAULT_STUDENT_ID = 1
MESSAGE = "Hola, quiero aprender Python"


async def main(url: str, student_id: int) -> int:
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"Connected to '{init.serverInfo.name}' at {url}")

            tools = await session.list_tools()
            print("Tools:", ", ".join(tool.name for tool in tools.tools))

            result = await session.call_tool(
                "chat_with_tutor", {"student_id": student_id, "message": MESSAGE}
            )
            text = result.content[0].text if result.content else ""
            if result.isError:
                print(f"Tool error: {text}", file=sys.stderr)
                return 1

            # A plain dict return is delivered as JSON text content.
            payload = result.structuredContent or json.loads(text)
            print("assistant_message:", payload["assistant_message"])
            print("session_id:", payload["session_id"])
            return 0


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    student_id = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_STUDENT_ID
    sys.exit(asyncio.run(main(url, student_id)))
