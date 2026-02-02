from huggingface_hub import hf_hub_download
import duckdb
import os
def get_connection():
 return duckdb.connect("/mnt/data/ycsep.duckdb", read_only=True)
