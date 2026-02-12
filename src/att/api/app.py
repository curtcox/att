"""FastAPI app entrypoint."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from att.api.routes.code import router as code_router
from att.api.routes.debug import router as debug_router
from att.api.routes.deploy import router as deploy_router
from att.api.routes.git import router as git_router
from att.api.routes.mcp import router as mcp_router
from att.api.routes.projects import router as projects_router
from att.api.routes.runtime import router as runtime_router
from att.api.routes.tests import router as tests_router


def create_app() -> FastAPI:
    app = FastAPI(title="ATT API", version="0.1.0")
    app.include_router(projects_router)
    app.include_router(code_router)
    app.include_router(git_router)
    app.include_router(runtime_router)
    app.include_router(tests_router)
    app.include_router(debug_router)
    app.include_router(deploy_router)
    app.include_router(mcp_router)

    @app.get("/api/v1/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/mcp/.well-known", tags=["system"])
    async def mcp_discovery() -> dict[str, str]:
        return {
            "name": "att-mcp",
            "transport": "streamable-http",
            "endpoint": "/mcp",
        }

    @app.websocket("/api/v1/projects/{project_id}/ws")
    async def project_events(project_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                message = await websocket.receive_text()
                await websocket.send_text(f"{project_id}:{message}")
        except WebSocketDisconnect:
            return

    return app


app = create_app()


def run() -> None:
    uvicorn.run("att.api.app:app", host="0.0.0.0", port=8000, reload=False)
