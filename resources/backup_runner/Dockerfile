FROM python:3.7-slim as backup_runner

LABEL maintainer="https://github.com/0xdabbad00/"
LABEL Project="https://github.com/summitroute/backup_runner"

WORKDIR /opt/backup_runner
COPY entrypoint.sh /opt/backup_runner/entrypoint.sh

ENTRYPOINT /opt/backup_runner/entrypoint.sh