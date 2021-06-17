FROM node:10

WORKDIR /opt

ADD package.json /opt
ADD package-lock.json /opt
RUN npm ci
COPY ./ /opt
COPY etc/nginx.conf /opt/default.conf
