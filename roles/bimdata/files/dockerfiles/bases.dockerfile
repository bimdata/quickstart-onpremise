# Need to declare the ARG
ARG IMAGE
ARG TAG

FROM ${IMAGE}:${TAG}

# Add custom CA to OS trusted certificates
COPY ./web/certs/ca.crt /usr/local/share/ca-certificates/custom-ca.crt
RUN update-ca-certificates

# Add dockerize, we need it to wait for some apps when we start all containers
COPY ./dockerize.tar.gz /tmp/dockerize.tar.gz
RUN tar -C /usr/local/bin -xzvf /tmp/dockerize.tar.gz
RUN rm /tmp/dockerize.tar.gz
