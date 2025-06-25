# Use an appropriate Python base image
FROM python:3.11.12-slim

# Set the working directory inside the container
WORKDIR /app/backend

# Copy just the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies, including uvicorn for FastAPI
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "uvicorn[standard]"

# Copy the rest of your application code
COPY . .

# Create directories for persistent data if they don't exist
RUN mkdir -p /app/backend/transcripts /app/backend/vectorstore

# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run the FastAPI application using Uvicorn
# 'api:app' means look for 'app' object in 'api.py'
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]