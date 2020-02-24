FROM ubuntu:16.04
MAINTAINER Harry Kodden <harry.kodden@surfnet.nl>

RUN apt-get update && apt-get install -y apache2 libapache2-mod-auth-mellon wget curl
RUN a2enmod auth_mellon lua ssl proxy proxy_http proxy_wstunnel proxy_balancer lbmethod_byrequests headers && a2dissite 000-default

ADD conf /opt/templates/
ADD entrypoint.sh /

CMD ["bash", "/entrypoint.sh"]
