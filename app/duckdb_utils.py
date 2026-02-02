import duckdb
import os
import urllib.request

def get_connection():
    db_path = "v2_data.db"
    db_url = "https://a3s.fi/swift/v1/YCSEP_v2/v2_data.db"

    # Download the ~1GB database if it's not already in the container
    if not os.path.exists(db_path):
        print(f"Downloading DB from {db_url}...")
        urllib.request.urlretrieve(db_url, db_path)

    # Connect to the local copy
    return duckdb.connect(db_path, read_only=True)