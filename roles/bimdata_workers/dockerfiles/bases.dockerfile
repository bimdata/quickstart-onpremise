# Need to declare the ARG
ARG IMAGE
ARG TAG

FROM ${IMAGE}:${TAG}

# Add custom CA to OS trusted certificates
COPY ./web/certs/ca.crt /usr/local/share/ca-certificates/custom-ca.crt
RUN update-ca-certificates
