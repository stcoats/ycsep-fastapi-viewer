from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from app.duckdb_utils import get_connection
import pandas as pd
import io

app = FastAPI()

con = get_connection()

@app.get("/search")
def search(q: str = Query("")):
    """Return up to 100 rows from data table matching substring `q` in `text`."""
    safe = q.replace("'", "''")
    df = con.execute(
        f"""
        SELECT id, channel, video_id, speaker, start_time, end_time, upload_date, text, pos_tags
        FROM data
        WHERE text ILIKE '%{safe}%'
        LIMIT 100
        """
    ).df()
    return df.to_dict(orient="records")

@app.get("/audio/{id}")
def get_audio(id: str):
    """
    Stream MP3 audio from the `audio` BLOB column (if present).
    """
    row = con.execute(f"SELECT audio FROM data WHERE id = '{id}'").fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audio not found")
    audio_bytes = row[0]
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")
