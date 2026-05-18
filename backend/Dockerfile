FROM python:3.12-slim

# ffmpeg required by Whisper for audio/video decoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    python3-setuptools \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade --no-cache-dir pip wheel && \
    pip install "setuptools<72"

WORKDIR /app

COPY requirements.txt .
# openai-whisper setup.py requires pkg_resources (removed in setuptools>=72);
# --no-build-isolation lets it use the host setuptools<72 we just installed.
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20240930
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download Whisper model so containers start fast
ARG WHISPER_MODEL_SIZE=base
RUN python -c "import whisper; whisper.load_model('${WHISPER_MODEL_SIZE}')"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
