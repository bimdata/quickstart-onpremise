# Need to declare the ARG
ARG IMAGE
ARG TAG

FROM ${IMAGE}:${TAG}

# Add custom CA to OS trusted certificates
COPY ./web/certs/ca.crt /usr/local/share/ca-certificates/custom-ca.crt
RUN update-ca-certificates

# Need to use chrome at least one time
# This will create a temporary cert, launch and https server, and run chrome.
# (Chrome need to access to an https site to create the nssbd but we can't know if a website is reachable, this fix this issue)
RUN  openssl req -new -newkey rsa:2048 -days 1 -nodes -x509 \
    -subj "/C=FR/ST=Auvergne-Rhône-Alpes/L=Lyon/O=Bimdata-self-signed/CN=CA"  \
    -keyout /tmp/key.pem -out /tmp/cert.pem && \
    openssl s_server -key /tmp/key.pem -cert /tmp/cert.pem -accept 443 -www & \
    /opt/google/chrome-unstable/chrome --headless --no-sandbox https://localhost && \
    kill `pidof openssl` && rm /tmp/key.pem /tmp/cert.pem
RUN mkdir -p $HOME/.pki/nssdb
RUN certutil -d sql:$HOME/.pki/nssdb -A -n 'Custom CA' -i /usr/local/share/ca-certificates/custom-ca.crt -t TCP,TCP,TCP
