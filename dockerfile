# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install git and required system dependencies
RUN apt-get update && apt-get install -y git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Clone the repository (replace with your GitHub repo URL)
RUN git clone https://github.com/yossufyasser1/Rag_Chatbot.git .

# Remove the company_docs directory if it exists (you mentioned you don't need it)
RUN rm -rf company_docs

# Create directories for vector_db and conversation_logs
RUN mkdir -p vector_db conversation_logs

# Install Python dependencies
RUN pip install --no-cache-dir langchain langchain-community faiss-cpu google-generativeai \
    pypdf docx2txt "unstructured[md]" flask flask-cors

# Copy your existing vector_db (you'll need to handle this when setting up the container)
# This will be done via volume mounting when running the container

# Expose port 8080
EXPOSE 8080

# Modify the Flask port in Rag_Endpoint.py to use port 8080 and listen on all interfaces
RUN sed -i 's/port = int(os.environ.get("PORT", 5000))/port = int(os.environ.get("PORT", 8080))/' Rag_Endpoint.py

# Run the Flask application
CMD ["python", "Rag_Endpoint.py"]