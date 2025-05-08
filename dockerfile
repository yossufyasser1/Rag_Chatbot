# Base image with Python 3.8+
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    HOST=0.0.0.0 \
    DOCS_DIR=/app/company_docs \
    CACHE_DIR=/app/vector_db \
    LOGS_DIR=/app/conversation_logs

# Install git and other dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Clone the repository for company documents
# Replace with your actual GitHub repository URL
ARG GITHUB_DOCS_REPO=https://github.com/yourusername/company-docs.git
ARG GITHUB_TOKEN=""

# Clone company docs repo (public repo)
RUN if [ -z "$GITHUB_TOKEN" ]; then \
        git clone ${GITHUB_DOCS_REPO} ${DOCS_DIR}; \
    else \
        git clone https://${GITHUB_TOKEN}@github.com/${GITHUB_DOCS_REPO#https://github.com/} ${DOCS_DIR}; \
    fi

# Create necessary directories
RUN mkdir -p ${CACHE_DIR} ${LOGS_DIR}

# Copy application code
COPY RAG_Chatbot_final.py Rag_Endpoint.py ./

# Expose the port
EXPOSE 8080

# Command to run the application
CMD ["python", "Rag_Endpoint.py"]