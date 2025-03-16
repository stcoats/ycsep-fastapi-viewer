from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.duckdb_utils import get_connection
import pandas as pd
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from /static (including index.html)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("app/static/index.html")

con = get_connection()

@app.get("/data")
def get_paginated_data(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    text: str = Query(""),
    sort: str = Query("id"),
    direction: str = Query("asc")
):
    """
    GET /data?page=1&size=100&text=anyWords&sort=id&direction=asc
    Returns { "total": <int>, "data": [ {id, channel, video_id, speaker, start_time, end_time, pos_tags, text}, ... ] }

    We'll do substring search across 'text' OR 'pos_tags' columns.
    Sorting can be by any of the listed columns (id, channel, speaker, etc.)
    """
    # Allowed columns to sort by
    allowed_cols = [
        "id", "channel", "video_id", "speaker",
        "start_time", "end_time", "pos_tags", "text"
    ]
    if sort not in allowed_cols:
        sort = "id"
    if direction not in ["asc", "desc"]:
        direction = "asc"

    # Build WHERE for substring search in text or pos_tags
    safe_text = text.replace("'", "''").strip()
    where_clause = ""
    if safe_text:
        where_clause = f"""
          WHERE (
            text ILIKE '%{safe_text}%'
            OR pos_tags ILIKE '%{safe_text}%'
          )
        """

    # Count total matching
    count_query = f"SELECT COUNT(*) FROM data {where_clause}"
    total = con.execute(count_query).fetchone()[0]

    offset = (page - 1) * size

    query = f"""
    SELECT
      id, channel, video_id, speaker,
      start_time, end_time, pos_tags, text
    FROM data
    {where_clause}
    ORDER BY {sort} {direction}
    LIMIT {size} OFFSET {offset}
    """
    df = con.execute(query).df()
    data = df.to_dict(orient="records")

    return {"total": total, "data": data}

@app.get("/audio/{id}")
def get_audio(id: str):
    """
    Streams the audio BLOB for the given id.
    If your DB uses int, do def get_audio(id: int): 
    Then be sure to adapt your front-end to pass an integer.
    """
    row = con.execute("SELECT audio FROM data WHERE id = ?", [id]).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audio not found")
    return StreamingResponse(io.BytesIO(row[0]), media_type="audio/mpeg")
