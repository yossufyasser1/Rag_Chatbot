FROM python:3.9-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p vector_db conversation_logs

# Set environment variables
ENV GOOGLE_API_KEY="your-api-key-here"
ENV DOCS_DIR="/app/company_docs"
ENV CACHE_DIR="/app/vector_db"
ENV LOGS_DIR="/app/conversation_logs"

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "Rag_Endpoint.py"] 