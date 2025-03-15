from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from app.duckdb_utils import get_connection
import io
import base64

app = FastAPI()
con = get_connection()

@app.get("/search")
def search(text: str = Query("")):
    query = text.replace("'", "''")
    df = con.execute(
        f\"\"\"
        SELECT id, channel, video_id, speaker, start_time, end_time, upload_date, text, pos_tags
        FROM data
        WHERE text ILIKE '%{query}%'
        LIMIT 100
        \"\"\"
    ).df()
    return df.to_dict(orient='records')

@app.get("/audio/{id}")
def get_audio(id: int):
    row = con.execute(f"SELECT audio FROM data WHERE id = {id}").fetchone()
    if not row:
        return {"error": "Not found"}
    audio_bytes = row[0]
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")
