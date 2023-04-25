#!/bin/bash
# 
# Loads file contents into a nomad variable.
# 
# Usage: file_to_nomad_var.sh <filename> <variablename> <var_key>
# 
# filename can be - for stdin.
# 
# read the var back out with:
#  - nomad var get <variablename>

function print_usage() {
  echo "Usage: ${0} <nomad var> <var key>"
}

filename=$1
nomad_var=$2
var_key=$3

if [ "${filename}" !=  "-" ];
then
  if [ ! -f "${filename}" ]
  then
    echo "${filename} does not exist"
    exit
  fi
fi

var_contents=$(cat ${filename})

if [[ "${nomad_var}" == "" || "${var_key}" == "" ]];
then
  print_usage
  exit
fi

echo "Copying ${filename} to ${nomad_var}:${var_key}..."

nomad var put -force -in hcl - <<EOF
path = "${nomad_var}"

items {
    ${var_key} = <<OMGUNIQUETOKEN
${var_contents}
OMGUNIQUETOKEN
}
EOF

