from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from typing import List
from app.core.database import get_db
from app.models import User, Note
from app.schemas import TagUsage, TagMergeRequest
from app.dependencies import get_current_user

router = APIRouter()

@router.get("", response_model=List[TagUsage])
async def get_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # PostgreSQL specific query to count tags in a JSONB array
    sql = text("""
        SELECT tag, count(*) as count
        FROM notes, jsonb_array_elements_text(tags::jsonb) as tag
        WHERE user_id = :user_id
        GROUP BY tag
        ORDER BY count DESC;
    """)
    result = await db.execute(sql, {"user_id": current_user.id})
    return [{"name": row[0], "count": row[1]} for row in result.all()]

@router.put("/merge")
async def merge_tags(
    req: TagMergeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # This query replaces 'source' tag with 'target' tag in the tags array
    # It also ensures no duplicates by using jsonb_agg(DISTINCT ...)
    
    sql = text("""
        UPDATE notes
        SET tags = (
            SELECT jsonb_agg(DISTINCT CASE WHEN tag = :source THEN :target ELSE tag END)
            FROM jsonb_array_elements_text(tags::jsonb) AS tag
        )
        WHERE user_id = :user_id 
        AND tags::jsonb @> jsonb_build_array(:source)
    """)
    await db.execute(sql, {
        "user_id": current_user.id,
        "source": req.source,
        "target": req.target
    })
    await db.commit()
    return {"status": "success"}

@router.delete("/{name}")
async def delete_tag(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # This query removes the specified tag from the tags array
    sql = text("""
        UPDATE notes
        SET tags = (
            SELECT COALESCE(jsonb_agg(tag), '[]'::jsonb)
            FROM jsonb_array_elements_text(tags::jsonb) AS tag
            WHERE tag != :name
        )
        WHERE user_id = :user_id 
        AND tags::jsonb @> jsonb_build_array(:name)
    """)
    await db.execute(sql, {
        "user_id": current_user.id,
        "name": name
    })
    await db.commit()
    return {"status": "success"}
