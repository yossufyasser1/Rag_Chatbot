FROM python:3.9-slim

WORKDIR /app

# Install required system packages with space optimization
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    sqlite3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p vector_db

# Set environment variables
ENV GOOGLE_API_KEY="your-api-key-here"
ENV DOCS_DIR="/app/company_docs"
ENV CACHE_DIR="/app/vector_db"

# Database configuration
ENV DB_PATH="/app/conversations.db"

# Create volumes for persistent storage
VOLUME ["/app/conversations.db", "/app/vector_db"]

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application with Gunicorn for production
CMD gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 'Rag_Endpoint:app' 