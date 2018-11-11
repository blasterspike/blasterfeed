FROM alpine:latest

RUN apk add python3 \
            libxslt-dev \
            jpeg-dev && \
    apk add -t build-dependencies \
            gcc \
            python3-dev \
            linux-headers \
            musl-dev

RUN mkdir /home/blasterfeed/
COPY blasterfeed3k.py \
     my_timezones.py \
     requirements.txt \
     sqlitecache.py \
     /home/blasterfeed/

RUN pip3 install -r /home/blasterfeed/requirements.txt

# Clean up
RUN apk del build-dependencies && \
    rm -rf /var/cache/apk/* /tmp/*

ENTRYPOINT ["python3", "/home/blasterfeed/blasterfeed3k.py"]