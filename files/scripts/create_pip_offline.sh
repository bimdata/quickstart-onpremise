#! /usr/bin/sh

set -euo pipefail

WORKING_DIR="/tmp/bimdata"

REQUIREMENTS=$(cat <<EOF
pip
docker-compose==1.29.2
EOF
)

echo -n "Creating needed virtualenv…"
mkdir -p "${WORKING_DIR}/pip-archives"
echo "${REQUIREMENTS}" > "${WORKING_DIR}/requirements.txt"
python3 -m venv "${WORKING_DIR}/venv"
echo "Ok."

echo -n "Updating pip if needed…"
"${WORKING_DIR}/venv/bin/pip" install --disable-pip-version-check --upgrade pip > /dev/null
echo "Ok."

echo -n "Downloading prerequisites…"
"${WORKING_DIR}/venv/bin/pip" download -d "${WORKING_DIR}/pip-archives" -r "${WORKING_DIR}/requirements.txt" > /dev/null
echo "Ok."

echo -n "Compressing the archive…"
tar -cjf "$WORKING_DIR/pip-archives.tar.bz2" -C "${WORKING_DIR}" pip-archives
echo -e "Ok.\n"

echo "You can now retrieve the '$WORKING_DIR/pip-archives.tar.bz2' file and put it in your ansible inventory."
