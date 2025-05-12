# Use Python 3.9 base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Clone your repository (or copy source code)
RUN git clone https://github.com/yossufyasser1/Rag_Chatbot.git .

# Remove unnecessary folders
RUN rm -rf company_docs

# Create persistent data directories
RUN mkdir -p vector_db conversation_logs

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Modify Flask port in Rag_Endpoint.py to use 8080
RUN sed -i 's/port = int(os.environ.get("PORT", 5000))/port = int(os.environ.get("PORT", 8080))/' Rag_Endpoint.py

# Expose the Flask port
EXPOSE 8080

# Start the Flask app
CMD ["python", "Rag_Endpoint.py"]
