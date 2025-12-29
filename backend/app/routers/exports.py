from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models import User, Note
from app.dependencies import get_current_user
from pydantic import BaseModel
from typing import List
import io
import zipfile

router = APIRouter(
    prefix="/exports",
    tags=["exports"]
)

class BatchExportRequest(BaseModel):
    note_ids: List[str]

@router.post("/batch")
async def export_batch_zip(
    req: BatchExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export multiple notes as a ZIP of Markdown files.
    """
    result = await db.execute(select(Note).where(Note.id.in_(req.note_ids), Note.user_id == current_user.id))
    notes = result.scalars().all()
    
    if not notes:
        raise HTTPException(status_code=404, detail="No notes found to export")
        
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for note in notes:
             # Format Content (Reuse logic from markdown export if possible, but keep simple here)
            tags_str = "\n".join([f"  - {t}" for t in note.tags]) if note.tags else ""
            created_date = note.created_at.strftime('%Y-%m-%d %H:%M') if note.created_at else ""
            
            frontmatter = f"---\ntitle: \"{note.title}\"\ncreated: {created_date}\ntags:\n{tags_str}\nmood: {note.mood}\nsummary: \"{(note.summary or '').replace('\"', '\\\"')}\"\n---\n"
            
            content = f"{frontmatter}\n# {note.title}\n\n## Summary\n{note.summary}\n\n## Transcript\n{note.transcription_text}"
            
            # Filename safety
            safe_title = "".join([c for c in (note.title or "untitled") if c.isalpha() or c.isdigit() or c==' ']).rstrip()
            filename = f"{safe_title.replace(' ', '_')}_{note.id[:4]}.md"
            
            zip_file.writestr(filename, content)
            
    zip_buffer.seek(0)
    
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=voicebrain_export_batch.zip"}
    )

@router.get("/{note_id}/markdown")
async def export_markdown(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export a note as a Markdown file with YAML frontmatter.
    Ideal for Obsidian, Hugo, Jekyll, etc.
    """
    result = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == current_user.id))
    note = result.scalars().first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
        
    # Format Frontmatter
    tags_str = "\n".join([f"  - {t}" for t in note.tags]) if note.tags else ""
    created_date = note.created_at.strftime('%Y-%m-%d %H:%M')
    
    frontmatter = f"""---
title: "{note.title}"
created: {created_date}
tags:
{tags_str}
mood: {note.mood}
summary: "{note.summary.replace('"', '\\"')}"
---
"""
    
    # Body
    content = f"{frontmatter}\n# {note.title}\n\n## Summary\n{note.summary}\n\n## Transcript\n{note.transcription_text}"
    
    # Return as file download
    filename = f"{note.title.replace(' ', '_').lower()}.md"
    
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/{note_id}/tana")
async def export_tana(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export a note in Tana Paste format (indentation-based).
    """
    result = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == current_user.id))
    note = result.scalars().first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    analysis = note.ai_analysis or {}
    intent = analysis.get("intent", "note")
    
    # Tana Paste format
    lines = [
        "%%tana%%",
        f"- {note.title or 'Untitled Note'} #voicebrain",
        f"  - Summary:: {note.summary or ''}",
        f"  - Intent:: {intent}"
    ]
    
    if note.action_items:
        lines.append("  - Action Items")
        for item in note.action_items:
            lines.append(f"    - {item} #todo")
            
    if note.tags:
        tags_str = " ".join([f"#{t.replace(' ', '_')}" for t in note.tags])
        lines.append(f"  - Tags:: {tags_str}")

    content = "\n".join(lines)
    
    return Response(
        content=content,
        media_type="text/plain"
    )

@router.get("/all")
async def export_all_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export all user data (notes, metadata) as JSON.
    """
    result = await db.execute(select(Note).where(Note.user_id == current_user.id))
    notes = result.scalars().all()
    
    data = {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "tier": current_user.tier
        },
        "notes": []
    }
    
    for note in notes:
        data["notes"].append({
            "id": note.id,
            "title": note.title,
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "summary": note.summary,
            "transcription": note.transcription_text,
            "tags": note.tags,
            "ai_analysis": note.ai_analysis,
            "status": note.status
        })
        
    import json
    json_str = json.dumps(data, indent=2, default=str)
    
    filename = f"voicebrain_export_{current_user.id}.json"
    
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
