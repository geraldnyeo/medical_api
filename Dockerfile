FROM ubuntu
RUN apt-get update && apt-get -y update

RUN apt-get -y update \
    && apt-get install -y wget \
    && apt-get install -y jq \
    && apt-get install -y lsb-release \
    && apt-get install -y openjdk-21-jdk-headless \
    && apt-get install -y python3-pip \
    && apt-get install -y python3-venv \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
        /usr/share/man /usr/share/doc /usr/share/doc-base
    
ENV PYSPARK_DRIVER_PYTHON=python3
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_SUBMIT_ARGS="--master local[3] pyspark-shell"

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

EXPOSE 8000

COPY requirements.txt /
RUN python3 -m venv env \
    && . env/bin/activate \
    && python3 -m pip install -r requirements.txt

COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

COPY ./src/ /src/

ENTRYPOINT ["/entrypoint.sh"]