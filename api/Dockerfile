FROM ubuntu:18.04

RUN apt-get update -y
RUN apt-get upgrade -y

RUN apt-get install -y samba git

RUN apt-get update
RUN apt-get install -y python-pip vim

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get install -y build-essential
RUN apt-get -y install libldap2-dev libsasl2-dev slapd ldap-utils

# Install guacapy...
RUN git clone https://github.com/pschmitt/guacapy.git
RUN python guacapy/setup.py install 

# Extra requirements for API...
RUN pip install Flask Flask-RESTful python-ldap

EXPOSE 8080

ADD api.py .

CMD ["python", "api.py"]
