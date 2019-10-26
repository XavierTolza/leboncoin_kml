FROM ubuntu:latest
RUN apt update && apt upgrade -y
RUN apt install -y python3 python3-pip firefox wget
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN ln -s /usr/bin/pip3 /usr/bin/pip

RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux64.tar.gz
RUN tar xvf geckodriver-v0.26.0-linux64.tar.gz && rm geckodriver-v0.26.0-linux64.tar.gz
RUN mv geckodriver /usr/bin

WORKDIR /app
ADD requirements.txt /app/
RUN pip install -r requirements.txt && rm requirements.txt
ADD leboncoin_kml /app/leboncoin_kml
ADD main.py /app/

VOLUME ["/out"]
ENTRYPOINT python -u main.py --headless --output /out/output.txt -s 40