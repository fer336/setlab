FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY transicion.py generar_loops.py ./

# Los temas se montan en /temas y el resultado queda en /temas/salida
WORKDIR /temas
ENTRYPOINT ["python", "/app/transicion.py", "--salida", "/temas/salida"]
