FROM python:3.10-slim

WORKDIR /usr/src/overpass

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p $HOME/.overpass-dev/databases

RUN echo "{\"db_directory\": \"/root/.overpass-dev/databases\"}" > $HOME/.overpass-dev/config.json

CMD python3 main.py
