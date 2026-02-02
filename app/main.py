from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.duckdb_utils import get_connection
import io
import re
import zipfile

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

# DuckDB connection (read-only is fine)
con = get_connection()  # expects a table named `data` with columns below

# ---------- Channels list ----------
@app.get("/channels")
def get_channels():
    try:
        rows = con.execute("SELECT DISTINCT channel FROM data WHERE channel IS NOT NULL ORDER BY channel").fetchall()
        channels = [r[0] for r in rows]
        return JSONResponse(channels)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get channels: {e}")

# ---------- Data with channel filter & sorting ----------
@app.get("/data")
def get_paginated_data(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    text: str = Query(""),
    sort: str = Query("id"),
    direction: str = Query("asc"),
    channels: str = Query("")   # comma-separated from UI
):
    allowed_cols = ["id", "channel", "video_id", "speaker", "start_time", "end_time", "pos_tags", "text"]
    sort = sort if sort in allowed_cols else "id"
    direction = "desc" if direction.lower() == "desc" else "asc"

    # Build WHERE
    where_parts = []
    text_clean = text.strip().strip('"“”\'')
    if text_clean:
        # Convert spaces to \s+ and wrap in non-word boundaries; search text & pos_tags (case-insensitive)
        #phrase = re.sub(r'\s+', r'\\s+', text_clean)
        phrase = re.sub(r"'", r"''", text_clean) 
        pattern = f"(^|\\W){phrase}(\\W|$)"
        where_parts.append(f"(regexp_matches(text, '{pattern}', 'i') OR regexp_matches(pos_tags, '{pattern}', 'i'))")

    chan_list = [c.strip() for c in channels.split(",") if c.strip()]
    if chan_list:
        # Escape single quotes in channel values
        chan_esc = [c.replace("'", "''") for c in chan_list]
        in_list = ",".join([f"'{c}'" for c in chan_esc])
        where_parts.append(f"channel IN ({in_list})")

    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    offset = (page - 1) * size

    # Count
    try:
        total = con.execute(f"SELECT COUNT(*) FROM data {where_sql}").fetchone()[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Count query error: {e}")

    # Page
    query = f"""
        SELECT id, channel, video_id, speaker, start_time, end_time, pos_tags, text
        FROM data
        {where_sql}
        ORDER BY {sort} {direction}
        LIMIT {size} OFFSET {offset}
    """
    try:
        df = con.execute(query).df()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data query error: {e}")

    return {"total": total, "data": df.to_dict(orient="records")}

# ---------- Stream single MP3 (existing) ----------
@app.get("/audio/{id}")
def get_audio(id: str):
    row = con.execute("SELECT audio FROM data WHERE id = ?", [id]).fetchone()
    if not row or row[0] is None:
        raise HTTPException(status_code=404, detail="Audio not found")
    return StreamingResponse(io.BytesIO(row[0]), media_type="audio/mpeg")

# ---------- CSV download for current page ----------
@app.get("/download/csv")
def download_csv(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    text: str = Query(""),
    channels: str = Query("")
):
    # Reuse the same WHERE building as /data
    where_parts = []
    text_clean = text.strip().strip('"“”\'')
    if text_clean:
        #phrase = re.sub(r'\s+', r'\\s+', text_clean)
        phrase = re.sub(r"'", r"''", text_clean) 
        pattern = f"(^|\\W){phrase}(\\W|$)"
        where_parts.append(f"(regexp_matches(text, '{pattern}', 'i') OR regexp_matches(pos_tags, '{pattern}', 'i'))")

    chan_list = [c.strip() for c in channels.split(",") if c.strip()]
    if chan_list:
        chan_esc = [c.replace("'", "''") for c in chan_list]
        in_list = ",".join([f"'{c}'" for c in chan_esc])
        where_parts.append(f"channel IN ({in_list})")

    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    offset = (page - 1) * size

    q = f"""
        SELECT id, channel, video_id, speaker, start_time, end_time, text, pos_tags
        FROM data
        {where_sql}
        ORDER BY id ASC
        LIMIT {size} OFFSET {offset}
    """
    try:
        df = con.execute(q).df()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV query error: {e}")

    # Write CSV
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]),
                             media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=ycsep_page.csv"})

# ---------- MP3 ZIP for current page ----------
@app.get("/download/mp3zip")
def download_mp3zip(
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),
    text: str = Query(""),
    channels: str = Query("")
):
    # Same filters
    where_parts = []
    text_clean = text.strip().strip('"“”\'')
    if text_clean:
        #phrase = re.sub(r'\s+', r'\\s+', text_clean)
        phrase = re.sub(r"'", r"''", text_clean) 
        pattern = f"(^|\\W){phrase}(\\W|$)"
        where_parts.append(f"(regexp_matches(text, '{pattern}', 'i') OR regexp_matches(pos_tags, '{pattern}', 'i'))")

    chan_list = [c.strip() for c in channels.split(",") if c.strip()]
    if chan_list:
        chan_esc = [c.replace("'", "''") for c in chan_list]
        in_list = ",".join([f"'{c}'" for c in chan_esc])
        where_parts.append(f"channel IN ({in_list})")

    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    offset = (page - 1) * size

    # Fetch ids in page order
    try:
        ids = [r[0] for r in con.execute(
            f"SELECT id FROM data {where_sql} ORDER BY id ASC LIMIT {size} OFFSET {offset}"
        ).fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ZIP id query error: {e}")

    def stream_zip():
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for rid in ids:
                row = con.execute("SELECT audio FROM data WHERE id = ?", [rid]).fetchone()
                if not row or row[0] is None:
                    continue
                zf.writestr(f"{rid}.mp3", row[0])
        mem.seek(0)
        yield from mem

    return StreamingResponse(stream_zip(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=ycsep_page_audio.zip"})
