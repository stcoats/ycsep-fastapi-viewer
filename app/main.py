from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.duckdb_utils import get_connection
import pandas as pd
import io

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Serve index.html on "/" and "/index.html"
@app.get("/")
@app.get("/index.html")
def get_index():
    return FileResponse("app/static/index.html")

# DuckDB connection
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
    return StreamingResponse(io.BytesIO(row[0]), media_type="audio/mpeg")

@app.get("/data")
def get_all_data():
    df = con.execute(
        "SELECT id, channel, video_id, speaker, start_time, end_time, upload_date, text, pos_tags FROM data"
    ).df()
    return df.to_dict(orient="records")
