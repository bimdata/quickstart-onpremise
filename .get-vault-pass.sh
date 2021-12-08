#! /bin/bash

vault_file="./.ansible_vault_password"

if [[ -n ${ANSIBLE_VAULT_PASSWORD+x} ]] ; then
  echo $ANSIBLE_VAULT_PASSWORD
elif [[ -f $vault_file ]] ; then
  cat $vault_file
fi
