FROM python:3.8

COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

RUN apt update
RUN apt -y install restic

RUN git clone https://github.com/gerrowadat/nomad-homelab /nomad-homelab
RUN pip3 install -r /nomad-homelab/resticrunner/requirements.txt

WORKDIR /nomad-homelab/resticrunner

# Configuration file
ENV CONFIG_INI "/secrets/config.ini"
# List of restic jobs to run
ENV RESTIC_JOBS ""

# http address and port
ENV HTTP_ADDRESS "0.0.0.0"
ENV HTTP_PORT "8901"

ENTRYPOINT [ "/entrypoint.sh" ]
CMD ["python3"]
