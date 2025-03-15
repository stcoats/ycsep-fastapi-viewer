from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

# Make absolutely sure this matches the internal container path
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join("app", "static", "index.html")
    return FileResponse(index_path, media_type="text/html")
