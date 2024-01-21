FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install git -y
RUN pip3 install "git+https://github.com/openai/whisper.git" 
RUN apt-get install -y ffmpeg
COPY convert.py .

ENTRYPOINT ["python3", "./convert.py"]