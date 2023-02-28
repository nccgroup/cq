FROM python:3.9
COPY . /cq
WORKDIR /cq
RUN pip install regex
