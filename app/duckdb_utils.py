from huggingface_hub import hf_hub_download
import duckdb
import os

HF_REPO_ID = "stcoats/temp-duckdb-upload"
HF_FILENAME = "ycsep.duckdb"
LOCAL_PATH = "./ycsep.duckdb"

def get_connection():
    if not os.path.exists(LOCAL_PATH):
        hf_hub_download(
            repo_id=HF_REPO_ID,
            repo_type="dataset",
            filename=HF_FILENAME,
            local_dir=".",
            local_dir_use_symlinks=False
        )
    return duckdb.connect(LOCAL_PATH, read_only=True)

