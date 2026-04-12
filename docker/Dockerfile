FROM python:3.11-slim

WORKDIR /project                          # ← was /app

COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt

COPY . .                                  # ← copy the whole project root

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app/main.py", \
  "--server.port=8501", \
  "--server.address=0.0.0.0"]