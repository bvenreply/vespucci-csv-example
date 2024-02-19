FROM busybox

RUN mkdir /rtw

RUN chown 9001:9001 /rtw

COPY --chown=9001:9001 ./datasets/example /dataset

USER 9001:9001

CMD [ \
    "sh", \
    "-c", \
    "cp -a /dataset /rtw/dataset" \
]
