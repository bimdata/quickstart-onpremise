FROM node:16

WORKDIR /opt

COPY package.json package-lock.json /opt/

RUN npm ci

COPY . /opt/
COPY etc/nginx.conf /opt/etc/nginx.conf
