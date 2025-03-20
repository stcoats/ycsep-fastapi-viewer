import duckdb

def get_connection():
    return duckdb.connect("app/forensic.duckdb")


