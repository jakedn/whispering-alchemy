FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install git ffmpeg -y --no-install-recommends 
RUN pip3 install --no-cache-dir "git+https://github.com/openai/whisper.git" 

RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ./scripts/alchemize.py /app/scripts/alchemize.py

ENTRYPOINT ["python3", "./scripts/alchemize.py"]
