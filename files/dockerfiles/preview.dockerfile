# Need to declare the ARG
ARG IMAGE
ARG TAG

FROM ${IMAGE}:${TAG}

# Add custom CA to OS trusted certificates
COPY ./ca.crt /usr/local/share/ca-certificates/onprem-ca.crt
RUN update-ca-certificates

RUN mkdir -p $HOME/.pki/nssdb && \
  certutil -N -d sql:$HOME/.pki/nssdb --empty-password && \
  certutil -A -d sql:$HOME/.pki/nssdb -A -n 'Bimdata Onprem Custom CA' -i /usr/local/share/ca-certificates/onprem-ca.crt -t C,C,C
