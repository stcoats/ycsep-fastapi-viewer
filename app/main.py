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
    GET /data?page=1&size=100&text=lor&sort=id&direction=asc
    We'll do boundary-based matching across text & pos_tags:
      - We consider a boundary to be start/end of string or a non-alphanumeric char.
      - So 'lor' won't match 'explore' and 'no lah' won't match 'dunno lah'.

    We'll do this via something like:
      text REGEXP '(^|[^[:alnum:]])lor([^[:alnum:]]|$)' 'i'
    If user typed multiple words 'no lah', we insert \s+ for the space, so:
      no lah => no\s+lah => '(^|[^[:alnum:]])no\s+lah([^[:alnum:]]|$)' 'i'

    Sorting can be by [id, channel, video_id, speaker, start_time, end_time, pos_tags, text].
    """

    # Which columns can we sort by
    allowed_cols = ["id", "channel", "video_id", "speaker", "start_time", "end_time", "pos_tags", "text"]
    if sort not in allowed_cols:
        sort = "id"
    if direction not in ["asc", "desc"]:
        direction = "asc"

    raw_text = text.strip()
    where_clause = ""

    if raw_text:
        # Replace spaces with \s+ so "no lah" => "no\s+lah"
        # We'll create a pattern: (^|[^[:alnum:]])phrase([^[:alnum:]]|$)
        # and pass 'i' as a separate argument for case-insensitive matching
        phrase = re.sub(r'\s+', r'\\s+', raw_text)  # so no lah => no\s+lah
        # then build the final bracket-based pattern
        # e.g. (^|[^[:alnum:]])no\s+lah([^[:alnum:]]|$)
        pattern = f'(^|[^[:alnum:]]){phrase}([^[:alnum:]]|$)'

        where_clause = f"""
        WHERE (
          text REGEXP '{pattern}' 'i'
          OR pos_tags REGEXP '{pattern}' 'i'
        )
        """

    # Count total matching
    count_sql = f"SELECT COUNT(*) FROM data {where_clause}"
    total = con.execute(count_sql).fetchone()[0]

    offset = (page - 1) * size

    # Build final query with sorting
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
    """
    Streams the audio BLOB for the given id.
    """
    row = con.execute("SELECT audio FROM data WHERE id = ?", [id]).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audio not found")
    return StreamingResponse(io.BytesIO(row[0]), media_type="audio/mpeg")
