import os
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import paramiko

router = APIRouter(prefix="/ssh", tags=["ssh"])

VPS_HOST = os.getenv("VPS_HOST", "")
VPS_PORT = int(os.getenv("VPS_PORT", "22"))
VPS_USER = os.getenv("VPS_USER", "root")
VPS_KEY_PATH = os.getenv("VPS_KEY_PATH", "")
VPS_PASSWORD = os.getenv("VPS_PASSWORD", "")


def _make_client() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs: dict = dict(hostname=VPS_HOST, port=VPS_PORT, username=VPS_USER, timeout=10)
    if VPS_KEY_PATH:
        connect_kwargs["key_filename"] = VPS_KEY_PATH
    elif VPS_PASSWORD:
        connect_kwargs["password"] = VPS_PASSWORD
    else:
        raise RuntimeError("No VPS credentials configured")
    client.connect(**connect_kwargs)
    return client


class RunRequest(BaseModel):
    command: str


@router.post("/run")
async def run_command(req: RunRequest):
    if not VPS_HOST:
        raise HTTPException(503, "VPS_HOST not configured")
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _run_sync, req.command)
        return result
    except Exception as exc:
        raise HTTPException(500, str(exc))


def _run_sync(command: str) -> dict:
    client = _make_client()
    try:
        _, stdout, stderr = client.exec_command(command, timeout=30)
        return {
            "stdout": stdout.read().decode(),
            "stderr": stderr.read().decode(),
            "exit_code": stdout.channel.recv_exit_status(),
        }
    finally:
        client.close()


@router.websocket("/terminal")
async def terminal_ws(websocket: WebSocket):
    await websocket.accept()
    if not VPS_HOST:
        await websocket.send_text("ERROR: VPS_HOST not configured\r\n")
        await websocket.close()
        return

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs: dict = dict(hostname=VPS_HOST, port=VPS_PORT, username=VPS_USER, timeout=10)
    if VPS_KEY_PATH:
        connect_kwargs["key_filename"] = VPS_KEY_PATH
    elif VPS_PASSWORD:
        connect_kwargs["password"] = VPS_PASSWORD

    try:
        client.connect(**connect_kwargs)
        channel = client.invoke_shell(term="xterm-256color", width=220, height=50)

        async def read_output():
            loop = asyncio.get_event_loop()
            while True:
                data = await loop.run_in_executor(None, channel.recv, 4096)
                if not data:
                    break
                await websocket.send_text(data.decode("utf-8", errors="replace"))

        asyncio.create_task(read_output())

        async for message in websocket.iter_text():
            channel.send(message)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        await websocket.send_text(f"ERROR: {exc}\r\n")
    finally:
        client.close()
