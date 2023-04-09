FROM python:3.8

COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

RUN git clone https://github.com/gerrowadat/nomad-homelab /nomad-homelab
RUN pip3 install -r /nomad-homelab/ssl/letsencrypt-to-nomad-vars/requirements.txt

WORKDIR /nomad-homelab/ssl/letsencrypt-to-nomad-vars

# The nomad server to talk to (localhost if you're just runing this on servers)
ENV NOMAD_SERVER "localhost"
# The local directory for letsencrypt
ENV LETSENCRYPT_BASE "/etc/letsencrypt"
# A nomad token that has access to variables.
ENV NOMAD_VARIABLE_TOKEN ""
# The domains to do.
ENV DOMAINS ""
# How often to run, 0 to run once.
ENV CHECK_FREQUENCY_HRS "0"


ENTRYPOINT [ "/entrypoint.sh" ]
CMD ["python3"]
