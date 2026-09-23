FROM python:3.12-slim
RUN pip install --no-cache-dir "fastapi>=0.115" "uvicorn[standard]>=0.34"
WORKDIR /srv
COPY main.py /srv/main.py
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
