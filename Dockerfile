FROM python:3.11.10
USER root

RUN apt-get update
RUN apt-get -y install locales && \
    localedef -f UTF-8 -i ja_JP ja_JP.UTF-8
ENV LANG="ja_JP.UTF-8"
ENV LANGUAGE="ja_JP:ja"
ENV LC_ALL="ja_JP.UTF-8"
ENV TZ="JST-9"
ENV TERM="xterm"

RUN mkdir /langchain-academy
WORKDIR /langchain-academy

RUN apt-get -y install vim less

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools wheel
RUN pip install notebook

RUN pip install poetry \
  && poetry config virtualenvs.create false

COPY ./pyproject.toml ./poetry.lock /langchain-academy
RUN poetry config virtualenvs.create false
RUN poetry install
