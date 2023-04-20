#!/bin/bash
set -e

"$@" /nomad-homelab/resticrunner/resticrunner.py --alsologtostderr --config_inifile=${CONFIG_INI} --restic_jobs=${RESTIC_JOBS} --http_server_address=${HTTP_ADDRESS} --http_port=${HTTP_PORT}
