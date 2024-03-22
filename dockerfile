FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install git -y
RUN pip3 install "git+https://github.com/openai/whisper.git" 
RUN apt-get install -y ffmpeg

ENTRYPOINT ["python3", "./scripts/convert.py"]
