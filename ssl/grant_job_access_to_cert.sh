#!/bin/bash
#
# Usage: grant_job_access_to_cert.sh <nomad job name> <ssl.cert.domain>
# 
# It's assumed that the job is running (or at least extant) and that
# the ssl_certs/ssl_cert_domain nomad variable contains 'privkey' and
# 'chain' keys containing the contents of said files.
#
# Standard disclaimer that you likely shouldn't do ths outside a homelab.

JOB=$1
CERT=$2

if [ "$JOB" == "" ] || [ "$CERT" == "" ]
then
  echo "Usage: $0 <nomad_job_name> <ssl.cert.domain>"
  exit
fi

VAR_SUFFIX=${CERT//./_}

echo "reading ssl_certs/$VAR_SUFFIX"

nomad var get ssl_certs/$VAR_SUFFIX > /dev/null

if [ "$?" != 0 ]
then
  echo "Error verifying existence of ssl_certs/$VAR_SUFFIX nomad variable"
  exit
fi

echo "Checking nomad job: $JOB"

nomad job status $JOB > /dev/null

if [ "$?" != 0 ]
then
  echo "Error verifying existence of '$JOB'nomad job"
  exit
fi

POLICY_NAME="${JOB}-${VAR_SUFFIX}-policy"
POLICY_NAME="${POLICY_NAME//_/-}"

nomad acl policy apply -namespace default -job $JOB $POLICY_NAME - <<EOF
namespace "default" {
  variables {
    path "ssl_certs/${VAR_SUFFIX}" {
      capabilities = ["read", "list"]
    }
  }
}
EOF


if [ "$?" != 0 ]
then
  echo "Whoops."
  exit $?
fi

echo "Done."
