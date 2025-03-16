from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.duckdb_utils import get_connection
import pandas as pd
import io
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (index.html) from /static
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
    GET /data?page=1&size=100&text=someWords&sort=id&direction=asc

    We do a single "word-boundary" REGEXP search across text AND pos_tags:
      - If user typed "lor" => only matches \b lor \b
      - If user typed "no lah" => only matches the phrase as separate tokens, e.g. \b no \s+ lah \b
        -> won't match 'dunno lah' or 'no lahk'

    Both quoted or unquoted input are treated the same here: 
      - We remove any leading/trailing quotes if present
      - Then replace spaces with \s+ 
      - Then do a boundary-based search: (?i)\b...phrase...\b
    So "no lah" => (?i)\bno\s+lah\b
    So "lor" => (?i)\blor\b
    """

    # Allowed sort columns
    allowed_cols = ["id", "channel", "video_id", "speaker", "start_time", "end_time", "pos_tags", "text"]
    if sort not in allowed_cols:
        sort = "id"
    if direction not in ["asc", "desc"]:
        direction = "asc"

    safe_text = text.strip()
    if len(safe_text) >= 2 and safe_text.startswith('"') and safe_text.endswith('"'):
        # If user typed quotes like "no lah"
        safe_text = safe_text[1:-1].strip()  # remove leading/trailing quotes

    # Replace all spaces with \s+ so "no lah" => "no\s+lah"
    # This ensures multiple tokens are matched as a single phrase with space(s) in between.
    raw_search = re.sub(r'\s+', r'\\s+', safe_text)

    where_clause = ""
    if raw_search:
        # We'll do a boundary-based, case-insensitive regex: (?i)\braw_search\b
        # e.g.  WHERE (text REGEXP '(?i)\bno\s+lah\b' OR pos_tags REGEXP '(?i)\bno\s+lah\b')
        where_clause = f"""
        WHERE (
          text REGEXP '(?i)\\\\b{raw_search}\\\\b'
          OR pos_tags REGEXP '(?i)\\\\b{raw_search}\\\\b'
        )
        """

    # Count total
    count_sql = f"SELECT COUNT(*) FROM data {where_clause}"
    total = con.execute(count_sql).fetchone()[0]

    offset = (page - 1) * size

    sql = f"""
    SELECT
      id, channel, video_id, speaker,
      start_time, end_time, pos_tags, text
    FROM data
    {where_clause}
    ORDER BY {sort} {direction}
    LIMIT {size} OFFSET {offset}
    """
    df = con.execute(sql).df()
    data = df.to_dict(orient="records")

    return {"total": total, "data": data}

@app.get("/audio/{id}")
def get_audio(id: str):
    row = con.execute("SELECT audio FROM data WHERE id = ?", [id]).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audio not found")
    return StreamingResponse(io.BytesIO(row[0]), media_type="audio/mpeg")
