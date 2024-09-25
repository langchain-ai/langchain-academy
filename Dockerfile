FROM python:3.12-bookworm as poetry


SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && \
    apt-get -y install locales curl git vim sqlite3 && \
    localedef -f UTF-8 -i ja_JP ja_JP.UTF-8 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# for Japanese
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8
ENV TZ JST-9

# poetry
ENV PATH /root/.local/bin:$PATH
ENV POETRY_VIRTUALENVS_IN_PROJECT=1

RUN pip install --upgrade pip \
    && curl -sSL https://install.python-poetry.org | python -


WORKDIR /app

