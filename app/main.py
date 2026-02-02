from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.duckdb_utils import get_connection
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("app/static/index.html")

# Initialize connection and download DB if needed
con = get_connection()
ALLAS_AUDIO_BASE = "https://a3s.fi/swift/v1/YCSEP_v2/"

@app.get("/data")
def get_paginated_data(text: str = Query("")):
    if not text:
        return {"total": 0, "data": []}

    # Uses the BM25 search and phrase grouping logic from your working script
    query = """
        SELECT 
            min(id) as id,
            listagg(text, ' ') WITHIN GROUP (ORDER BY id) as text,
            file as video_id,
            min(start_time) as start_time,
            'N/A' as channel,
            'N/A' as speaker,
            0 as end_time,
            '' as pos_tags
        FROM (
            SELECT *, (id - row_number() OVER (ORDER BY id)) as grp
            FROM data
            WHERE id IN (SELECT id FROM data WHERE fts_main_data.match_bm25(id, ?) IS NOT NULL)
        )
        GROUP BY video_id, grp
        LIMIT 40
    """
    try:
        df = con.execute(query, [text]).df()
        
        # Format the URL to point directly to the audio on Allas
        df['audio_url'] = df.apply(lambda r: f"{ALLAS_AUDIO_BASE}{r['video_id']}#t={r['start_time']:.2f}", axis=1)
        
        results = df.to_dict(orient="records")
        return {"total": len(results), "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {e}")

# Audio endpoint redirects to Allas URL
@app.get("/audio/{id}")
def get_audio(id: str):
    # This logic assumes the 'video_id' and 'start_time' are used for the URL in the UI
    raise HTTPException(status_code=400, detail="Use the audio_url provided in the data response.")