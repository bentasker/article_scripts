FROM python:alpine

ENV HASH_DIR /hashdir/
ENV DRY_RUN "N"
ENV SKIP_TAGS ""
ENV TRACKING_MODE "LASTPAGE"

RUN pip install feedparser requests threads-net coincurve pynostr[websocket-client] atproto bs4\
    && mkdir /app \
    && mkdir /hashdir 
#    && useradd rssfeed \
#    && chown -R rssfeed /hashdir
    
#USER rssfeed
ENV PYTHONUNBUFFERED 1

#VOLUME /hashdir
COPY py_post_on_rss_change.py /app/

WORKDIR /app
CMD /app/py_post_on_rss_change.py

