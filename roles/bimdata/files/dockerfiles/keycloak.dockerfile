ARG IMAGE
ARG TAG
FROM ${IMAGE}:${TAG}

ARG TRUSTSTORE_PASSWORD

COPY /keycloak/standalone-ha.xml /opt/jboss/keycloak/standalone/configuration/standalone-ha.xml
COPY /keycloak/bimdata-realm.json /opt/bimdata-realm.json
COPY /web/certs/ca.crt /etc/ssl/custom-ca.crt
RUN mkdir -p /opt/jboss/keycloak/standalone/configuration/keystores/
RUN /usr/bin/keytool -import -noprompt -alias Internal-CA -keystore /opt/jboss/keycloak/standalone/configuration/keystores/custom-ca.jks -file /etc/ssl/custom-ca.crt -storepass ${TRUSTSTORE_PASSWORD}
