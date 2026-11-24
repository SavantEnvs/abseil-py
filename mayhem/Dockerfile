# syntax=docker/dockerfile:1.7
#
# Commit-image Dockerfile (SMALL form) for abseil/abseil-py (pure Python, Atheris), built on the org
# base image, which provides debian + python3 + pip + clang + the non-root identities + the
# build-contract ENV. mayhem/build.sh installs the pinned atheris wheel into the $HOME-independent
# /opt/toolchains/python (SPEC §6.2 item 8) and builds the thin ELF launchers Mayhem runs.
#
# Build (from the repo root):
#   DOCKER_BUILDKIT=1 docker build -f mayhem/Dockerfile \
#       --build-arg COMMIT=$(git rev-parse HEAD) -t abseil-py-commit:test .

FROM ghcr.io/savantenvs/base:20261023

ARG COMMIT
ARG REPO_URL
# SOURCE_DATE_EPOCH stays an ARG (never ENV — an empty value breaks clang); build.sh unsets it when empty.
ARG SOURCE_DATE_EPOCH
# Sanitizer override knob (no default, so the base ENV flows through when unset).
ARG SANITIZER_FLAGS
ARG MAYHEM_JOBS=

# Python toolchain cache: owned by the builder, world-readable, so any uid can import atheris.
USER root
RUN mkdir -p /opt/toolchains/python && chown 2000:2000 /opt/toolchains/python \
 && chmod 0755 /opt/toolchains/python
USER mayhem
WORKDIR /mayhem
COPY --chown=2000:2000 . /mayhem

RUN bash mayhem/build.sh

# The functional suite runs at build time — a failing suite fails the image build.
RUN if [ -f mayhem/test.sh ]; then bash mayhem/test.sh; else echo "no mayhem/test.sh"; fi

LABEL org.opencontainers.image.source="${REPO_URL}" \
      org.opencontainers.image.revision="${COMMIT}" \
      rlenv.tier="commit" \
      rlenv.source_date_epoch="${SOURCE_DATE_EPOCH}" \
      rlenv.user="mayhem"

USER mayhem
WORKDIR /mayhem
