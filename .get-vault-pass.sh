#! /bin/bash

vault_file="./.vault-pass.txt"

if [[ -f $vault_file ]] ; then
  cat $vault_file
elif [[ -n ${ANSIBLE_VAULT_PASSWD+x} ]] ; then
  echo $ANSIBLE_VAULT_PASSWD
fi
