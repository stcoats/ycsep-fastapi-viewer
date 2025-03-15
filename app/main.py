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

# Serve HTML frontend
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("app/static/index.html")

con = get_connection()

@app.get("/search")
def search(text: str = Query("")):
    query = text.replace("'", "''")
    df = con.execute(
        f"""
        SELECT id, channel, video_id, speaker, start_time, end_time, upload_date, text, pos_tags
        FROM data
        WHERE text ILIKE '%{query}%'
        LIMIT 100
        """
    ).df()
    return df.to_dict(orient="records")

@app.get("/audio/{id}")
def get_audio(id: str):
    row = con.execute(f"SELECT audio FROM data WHERE id = '{id}'").fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audio not found")
    audio_bytes = row[0]
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")

# ✅ NEW paginated/sortable data endpoint
@app.get("/data")
def get_paginated_data(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    sort: str = Query("id"),
    dir: str = Query("asc"),
    text: str = Query("")
):
    allowed_sort_columns = ["id", "channel", "video_id", "speaker", "start_time", "end_time", "text"]
    if sort not in allowed_sort_columns:
        raise HTTPException(status_code=400, detail="Invalid sort column")
    if dir not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid sort direction")

    offset = (page - 1) * size
    text_filter = f"WHERE text ILIKE '%{text.replace("'", "''")}%' " if text else ""
    
    query = f"""
        SELECT id, channel, video_id, speaker, start_time, end_time, text
        FROM data
        {text_filter}
        ORDER BY {sort} {dir}
        LIMIT {size} OFFSET {offset}
    """
    df = con.execute(query).df()

    # Get total count for pagination
    count_query = f"SELECT COUNT(*) FROM data {text_filter}"
    total = con.execute(count_query).fetchone()[0]

    return {"total": total, "data": df.to_dict(orient="records")}
