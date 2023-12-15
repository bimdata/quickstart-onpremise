#! /usr/bin/bash

set -euo pipefail

WORKING_DIR="/tmp/bimdata"

# Request is pined to this version as a workaround to https://github.com/docker/docker-py/issues/3113
REQUIREMENTS=$(cat <<EOF
pip
selinux
docker-compose==1.29.2
requests<=2.29.0
docker~=6.0
EOF
)

echo -n "Creating needed virtualenv…"
# Delete existing venv, existing cache can cause issues
if [[ -d "${WORKING_DIR}/venv" ]] ; then
  rm -r "${WORKING_DIR}/venv"
fi
mkdir -p "${WORKING_DIR}/pip-archives"

echo "${REQUIREMENTS}" > "${WORKING_DIR}/requirements.txt"
virtualenv -p python3 "${WORKING_DIR}/venv"
echo "Ok."

echo -n "Updating pip if needed…"
"${WORKING_DIR}/venv/bin/pip" install --disable-pip-version-check --upgrade pip > /dev/null
echo "Ok."

echo -n "Downloading prerequisites…"
"${WORKING_DIR}/venv/bin/pip" download -d "${WORKING_DIR}/pip-archives" -r "${WORKING_DIR}/requirements.txt" > /dev/null
echo "Ok."

echo -n "Creating the archive…"
tar -cjf "$WORKING_DIR/pip-archives.tar.bz2" -C "${WORKING_DIR}" pip-archives
echo -e "Ok.\n"

echo "You can now retrieve the '$WORKING_DIR/pip-archives.tar.bz2' file and put it in your ansible inventory."
