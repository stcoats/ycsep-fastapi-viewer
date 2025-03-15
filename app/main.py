from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from app.duckdb_utils import get_connection
import math

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Jinja2 (templates in ./templates)
templates = Jinja2Templates(directory="app/templates")

con = get_connection()

@app.get("/", response_class=HTMLResponse)
def search_page(request: Request, q: str = "", page: int = 1, size: int = 50):
    safe_q = q.replace("'", "''")
    where_clause = ""
    if safe_q.strip():
        where_clause = f"WHERE text ILIKE '%{safe_q}%'"

    # Count total rows for pagination
    total_query = f"SELECT COUNT(*) FROM data {where_clause}"
    total_rows = con.execute(total_query).fetchone()[0]

    # Figure out offset
    offset = (page - 1) * size

    # Grab subset
    query = f"""
    SELECT id, speaker, channel, video_id, start_time, end_time, text
    FROM data
    {where_clause}
    ORDER BY id
    LIMIT {size} OFFSET {offset}
    """
    rows = con.execute(query).fetchall()
    cols = con.execute(query).description

    # Convert rows into a list of dicts
    col_names = [c[0] for c in cols]
    row_dicts = []
    for r in rows:
        row_dicts.append(dict(zip(col_names, r)))

    total_pages = math.ceil(total_rows / size)

    return templates.TemplateResponse(
        "table.html",
        {
            "request": request,
            "rows": row_dicts,
            "page": page,
            "total_pages": total_pages,
            "query": q,
        },
    )
