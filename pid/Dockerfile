FROM ubuntu:16.04

MAINTAINER Harry Kodden <harry.kodden@surfnet.nl>

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get install -y --no-install-recommends \
    build-essential git \
    python3 python3-virtualenv python3-dev
RUN apt-get install -y postgresql python-psycopg2 libpq-dev libffi-dev libmysqlclient-dev --fix-missing

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m virtualenv --python=/usr/bin/python3 $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN git clone https://github.com/privacyidea/privacyidea.git

RUN cd privacyidea && pip install -r requirements.txt && ln -s $PWD/pi-manage /usr/local/bin

RUN pip install mysqlclient

RUN mkdir -p /etc/privacyidea /var/log/privacyidea

WORKDIR /etc/privacyidea

EXPOSE 5000

CMD [ "/bin/bash" ]
