FROM python:3.9-slim

WORKDIR /app

# Install required system packages including SQLite and Git
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    git \
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

# Git configuration
ENV GIT_USER_NAME="Chatbot Database Sync"
ENV GIT_USER_EMAIL="chatbot@example.com"
ENV GIT_REPO_URL=""
ENV GIT_SYNC_INTERVAL_MINUTES="60"

# Create volumes for persistent storage
VOLUME ["/app/conversations.db", "/app/vector_db"]

# Add sync script
RUN echo '#!/bin/bash\n\
while true; do\n\
  if [ -n "$GIT_REPO_URL" ] && [ -f "$DB_PATH" ]; then\n\
    echo "$(date) - Syncing database to GitHub..."\n\
    git config --global user.name "$GIT_USER_NAME"\n\
    git config --global user.email "$GIT_USER_EMAIL"\n\
    git add "$DB_PATH"\n\
    git commit -m "Auto-sync database $(date)"\n\
    git push\n\
    echo "$(date) - Database sync complete"\n\
  else\n\
    echo "$(date) - Git sync disabled or database not found"\n\
  fi\n\
  sleep ${GIT_SYNC_INTERVAL_MINUTES}m\n\
done' > /app/sync_database.sh && chmod +x /app/sync_database.sh

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application with database sync
CMD sh -c "if [ -n \"$GIT_REPO_URL\" ]; then /app/sync_database.sh & fi; python Rag_Endpoint.py" 