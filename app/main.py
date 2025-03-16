from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

import pandas as pd
from app.duckdb_utils import get_connection

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="app/templates")
con = get_connection()

@app.get("/", response_class=HTMLResponse)
def show_table(request: Request, q: str = Query("")):
    """
    Renders table.html with up to 50 matching rows from the DB.
    """
    safe_q = q.replace("'", "''").strip()
    where_clause = ""
    if safe_q:
        where_clause = f"WHERE text ILIKE '%{safe_q}%'"

    query = f"""
        SELECT id, channel, video_id, speaker, start_time, end_time, text
        FROM data
        {where_clause}
        LIMIT 50
    """
    df = con.execute(query).df()

    # Convert DataFrame to list-of-dicts
    rows = df.to_dict(orient="records")

    return templates.TemplateResponse(
        "table.html",
        {
            "request": request,
            "rows": rows,
            "query": q
        },
    )
