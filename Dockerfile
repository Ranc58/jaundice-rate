FROM python:3.7-alpine3.7


RUN apk update \
    && apk add \
    && apk add \
      bash \
      build-base \
      gcc \
      gettext \
      libffi-dev \
    && rm -vrf /var/cache/apk/*

RUN mkdir /app

COPY requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install -r requirements.txt

COPY . /app
CMD python3 app.py
