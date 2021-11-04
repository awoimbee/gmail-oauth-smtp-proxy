# syntax = docker/dockerfile:1.0-experimental

## NOTE : This image uses BuildKit, see
## https://docs.docker.com/develop/develop-images/build_enhancements/
## for more information.
## TLDR: Use docker build with DOCKER_BUILDKIT=1 in the environment

FROM python:3.9-slim-buster AS base
LABEL authors="<arthur.woimbee@gmail.com>"

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1



FROM base as builder

ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VERSION=1.1.10

RUN --mount=type=cache,target=/root/.cache \
    pip install "poetry==$POETRY_VERSION"

WORKDIR /src



FROM builder AS deps_builder

# Export to requirements.txt is needed because poetry doesn't support "--prefix"
# Sadly we have to copy pyproject.toml too
COPY pyproject.toml poetry.lock ./
RUN poetry export --without-hashes -n --no-ansi -f requirements.txt -o requirements.txt
RUN --mount=type=secret,id=netrc,dst=/root/.netrc \
    --mount=type=cache,target=/root/.cache \
    pip install --prefix=/runtime --force-reinstall -r requirements.txt



FROM builder as app_builder

COPY . .
RUN poetry build -f wheel -n --no-ansi \
    && pip install ./dist/* --prefix=/runtime --no-index --no-deps



FROM base AS runtime

WORKDIR /opt/app

# Create group & user www-data with correct id
RUN userdel -f www-data \
    && if getent group www-data ; then groupdel www-data; fi \
    && groupadd -g 33 www-data \
    && useradd -l -u 33 -g www-data www-data

USER www-data

COPY --from=deps_builder /runtime /usr/local
COPY --from=app_builder /runtime /usr/local

ENTRYPOINT ["python", "-m", "gmail_smtp_proxy.main"]
