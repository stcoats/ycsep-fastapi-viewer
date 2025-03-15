FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files and db assembly script
COPY app/ app/
COPY assemble_db.sh .  # <-- This brings your script into /app
COPY db_parts/ db_parts/  # <-- assuming your .part files are in db_parts/

# Make script executable
RUN chmod +x assemble_db.sh

# Run the script during build
RUN ./assemble_db.sh

# Expose port
EXPOSE 7860

# Start FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]


