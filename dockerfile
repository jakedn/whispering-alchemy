FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install git ffmpeg -y --no-install-recommends 
RUN pip3 install --no-cache-dir "git+https://github.com/openai/whisper.git" 

RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ./src/scripts/alchemize.py /app/scripts/alchemize.py

ENTRYPOINT ["python3", "./scripts/alchemize.py"]
