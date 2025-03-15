#!/bin/sh
set -e

echo "📦 Downloading DB parts from Allas..."

cd /mnt/data/

# Download all parts
for part in aa ab ac ad; do
  wget -O ycsep.duckdb.part.$part https://a3s.fi/swift/v1/AUTH_319b50570e56446f94b58088b66fcdb2/ycsep-db/ycsep.duckdb.part.$part
done

# Concatenate
echo "🔗 Reassembling DuckDB file..."
cat ycsep.duckdb.part.* > ycsep.duckdb

# Optionally remove part files
rm ycsep.duckdb.part.*

echo "✅ Done: ycsep.duckdb is ready in /mnt/data/"
