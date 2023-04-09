#!/bin/bash
set -e

function do_check() {
  for DOMAIN in $DOMAINS
  do
    echo "Checking variables for domain ${DOMAIN}"
    python3 /nomad-homelab/ssl/letsencrypt-to-nomad-vars/letsencrypt-to-nomad-vars.py --nomad_server=${NOMAD_SERVER} --letsencrypt_base=${LETSENCRYPT_BASE} --export_cert=${DOMAIN}
  done
}

if [ "$NOMAD_VARIABLE_TOKEN" == "" ]
then
  if [ -e "/secrets/variable-admin.token" ]
  then
    NOMAD_VARIABLE_TOKEN=`cat /secrets/variable-admin.token`
  fi
  if [ "$NOMAD_VARIABLE_TOKEN" == "" ]
  then
    echo "You need to set NOMAD_VARIABE_TOKEN in the environment."
    exit
  fi
fi

if [ "$DOMAINS" == "" ]
then
  echo "You need to set DOMAINS in the environment."
  exit
fi

export NOMAD_TOKEN=${NOMAD_VARIABLE_TOKEN}

if [ "${CHECK_FREQUENCY_HRS}" == "0" ]
then
  echo "Running once."
  do_check
  exit
fi

while true
do
  do_check
  echo "Sleeping ${CHECK_FREQUENCY_HRS} hours..."
  sleep $(( ${CHECK_FREQUENCY_HRS} * 60 * 60 ))
done
