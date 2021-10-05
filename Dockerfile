FROM alpine:latest

COPY blasterfeed3k.py \
     my_timezones.py \
     requirements.txt \
     sqlitecache.py \
     /home/

RUN apk add python3 \
            libxslt-dev \
            jpeg-dev && \
    apk add -t build-dependencies \
            gcc \
            python3-dev \
            linux-headers \
            musl-dev \
            py3-pip && \
    pip3 install -r /home/requirements.txt && \
    # Clean up
    apk del build-dependencies && \
    rm -rf /var/cache/apk/* /tmp/*

ENTRYPOINT ["python3", "/home/blasterfeed3k.py"]