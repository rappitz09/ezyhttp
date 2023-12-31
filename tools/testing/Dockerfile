ARG PYTHON_VERSION
FROM python:$PYTHON_VERSION

ARG ezyhttp_NO_EXTENSIONS
ENV ezyhttp_NO_EXTENSIONS=$ezyhttp_NO_EXTENSIONS

WORKDIR /deps
ADD ./requirements ./requirements
ADD Makefile .
RUN make install

ADD ./tools/testing/entrypoint.sh /

WORKDIR /src
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
