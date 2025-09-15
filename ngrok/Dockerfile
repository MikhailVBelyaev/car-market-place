FROM alpine:3.19

WORKDIR /app

RUN apk add --no-cache curl unzip \
    && curl -s https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-v3-stable-linux-amd64.zip -o ngrok.zip \
    && unzip ngrok.zip -d /usr/local/bin \
    && rm ngrok.zip

ENTRYPOINT ["ngrok"]