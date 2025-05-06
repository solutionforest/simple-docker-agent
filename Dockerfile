FROM python:3.13-slim

WORKDIR /app

COPY agent.py .

RUN pip install flask docker psutil humanize gunicorn

CMD ["gunicorn", "-b", "0.0.0.0:8080", "agent:app"]