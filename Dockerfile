FROM python:3.8

COPY requirements.txt /

RUN pip3 install --upgrade pip \
    && pip3 install -r requirements.txt \
    && apt update -qq \
    && echo 'alias hts="python /opt/src/hts.py "' >> ~/.bashrc \
    && apt install -y vim \
    && apt install -y less
