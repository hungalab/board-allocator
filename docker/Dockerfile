FROM python:3.8

RUN apt-get update && apt-get install -y \
    gir1.2-gtk-3.0 \
    gosu \
    libcairo2-dev \
    libgirepository1.0-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

RUN pip install deap==1.3.1
RUN pip install matplotlib==3.4.2
RUN pip install networkx==2.6.2
RUN pip install pycairo==1.16.2
RUN pip install PyGObject==3.36.0

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod u+x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD ["/bin/bash"]