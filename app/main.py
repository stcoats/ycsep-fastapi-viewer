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

# If you want to serve your 'index.html' from the same container:
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def serve_index():
    # Return the HTML at /static/index.html
    # so going to "/" loads it in the browser
    return FileResponse("app/static/index.html")

con = get_connection()

@app.get("/audio/{id}")
def get_audio(id: str):
    # Streams audio bytes from the DB
    row = con.execute(f"SELECT audio FROM data WHERE id = '{id}'").fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audio not found")
    return StreamingResponse(io.BytesIO(row[0]), media_type="audio/mpeg")

@app.get("/data")
def get_paginated_data(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    text: str = Query(""),
    sort: str = Query("id"),
    direction: str = Query("asc")
):
    """
    Returns JSON in { "total":..., "data":[...] }
    each item: { id, speaker, channel, start_time, end_time, text }
    """

    # Validate sort column
    allowed_cols = ["id", "channel", "video_id", "speaker", "start_time", "end_time", "text"]
    if sort not in allowed_cols:
        sort = "id"
    if direction not in ["asc", "desc"]:
        direction = "asc"

    # Build WHERE if text is given
    safe_text = text.replace("'", "''")
    where_clause = ""
    if safe_text:
        where_clause = f"WHERE text ILIKE '%{safe_text}%'"

    # Count total matches
    count_query = f"SELECT COUNT(*) FROM data {where_clause}"
    total = con.execute(count_query).fetchone()[0]

    offset = (page - 1) * size

    query = f"""
    SELECT id, channel, video_id, speaker, start_time, end_time, text
    FROM data
    {where_clause}
    ORDER BY {sort} {direction}
    LIMIT {size} OFFSET {offset}
    """
    df = con.execute(query).df()
    data = df.to_dict(orient="records")

    return {"total": total, "data": data}
