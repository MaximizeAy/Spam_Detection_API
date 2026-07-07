# Use Python 3.11 to ensure pre-compiled wheels for Pandas/Scikit-learn
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required by Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY rule_engine.py .
COPY fusion.py .
COPY metadata.json .

# Copy the ML model
COPY models/ ./models/

# Create the logs directory and give write permissions
RUN mkdir -p logs

# Create a non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]