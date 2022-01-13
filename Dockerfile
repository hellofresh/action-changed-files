# Container image that runs your code
FROM python:3.10-alpine

# TODO: if we use the urllib3 instead of requests here, we can skip this step
RUN pip install requests

COPY neo/neo.py /usr/bin/neo

ENTRYPOINT ["/usr/bin/neo"]