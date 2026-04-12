FROM python:3.11-slim

# 1. System deps
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /project

# 2. Dependencies (Cache Layer)
COPY requirements/base.txt .
RUN pip install --no-cache-dir -r base.txt

# 3. Code and Metadata
COPY . .

# 4. Install the project (Now it will find the correct build-backend)
RUN pip install --no-cache-dir .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]