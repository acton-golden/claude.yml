import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/obsidian", tags=["obsidian"])

OBSIDIAN_API_URL = os.getenv("OBSIDIAN_API_URL", "http://localhost:27123")
OBSIDIAN_API_KEY = os.getenv("OBSIDIAN_API_KEY", "")


def _headers():
    return {"Authorization": f"Bearer {OBSIDIAN_API_KEY}"}


@router.get("/notes")
async def list_notes(path: str = "/"):
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(f"{OBSIDIAN_API_URL}/vault/{path.lstrip('/')}", headers=_headers())
        if resp.status_code == 404:
            raise HTTPException(404, "Path not found in vault")
        resp.raise_for_status()
        return resp.json()


@router.get("/note")
async def get_note(path: str):
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(
            f"{OBSIDIAN_API_URL}/vault/{path.lstrip('/')}",
            headers={**_headers(), "Accept": "text/markdown"},
        )
        if resp.status_code == 404:
            raise HTTPException(404, "Note not found")
        resp.raise_for_status()
        return {"path": path, "content": resp.text}


class NoteWrite(BaseModel):
    path: str
    content: str


@router.put("/note")
async def write_note(note: NoteWrite):
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.put(
            f"{OBSIDIAN_API_URL}/vault/{note.path.lstrip('/')}",
            headers={**_headers(), "Content-Type": "text/markdown"},
            content=note.content.encode(),
        )
        resp.raise_for_status()
        return {"status": "saved", "path": note.path}


@router.get("/search")
async def search_notes(query: str):
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.post(
            f"{OBSIDIAN_API_URL}/search/simple/",
            headers=_headers(),
            params={"query": query},
        )
        resp.raise_for_status()
        return resp.json()
