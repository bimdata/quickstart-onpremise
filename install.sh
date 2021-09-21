#!/usr/bin/env bash

set -e

trap clean_exit SIGINT SIGTERM ERR EXIT

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd -P)
VENV_PATH="${SCRIPT_DIR}/venv"
STORAGE_TYPES=("local" "swift")
DATABASES=("api" "connect" "platform" "iam" "share")
TLS_APPS=(
  "api"
  "connect"
  "platform_back"
  "platform_front"
  "iam"
  "rabbitmq_admin"
  "documentation"
  "share"
  "archive"
)

VAULT_SCRIPT="${SCRIPT_DIR}/.get-vault-pass.sh"

clean_exit(){
  trap - SIGINT SIGTERM ERR EXIT
  if [[ -n "$vault_password" ]] ; then
    if head -n1 "$vault_path" | grep -vq '^$ANSIBLE_VAULT;' ; then
      ANSIBLE_VAULT_PASSWORD=$vault_password ANSIBLE_VAULT_PASSWORD_FILE=$VAULT_SCRIPT ansible-vault encrypt $vault_path > /dev/null
    fi
  fi
  exit
}

usage() {
  cat <<EOF
Usage: $(basename "${BASH_SOURCE[0]}") [-h] [-v]

This script is intended to help you use the Bimdata.io on premise quickstart installation.

Available options:
  -h      Print this help and exit.
  -v      Enable verbose output
  -d      Enable debug output.
EOF
  exit
}

parse_params(){
  print_verb "Parse script arguments."
  while getopts "hvd" arguments ; do
    case $arguments in
      v)
      verbose=1
      ;;
      d)
      set -x
      ;;
      h)
      usage
      ;;
    esac
  done
}

print_err(){
  >&2 echo "$1"
}

print_verb(){
  output="${1:-$(</dev/stdin)}"
  if [[ $verbose -eq 1 ]] ; then
    echo "VERBOSE - $output"
  fi
}

get_value(){
  local var_name="$1"
  local path="${inventory_path// /\\ }/group_vars/all/*.yml"
  sed -rn "s/^[[:space:]]*${var_name}:[[:space:]]*(.*$)/\1/p" $path
}

config_var_value(){
  local prompt="$1"
  local var_name="$2"

  if [[ $3 == "lookup" ]] ; then
    local lookup=1
  fi

  # ${inventory_path// /\\ }: string substitution, replace all ' ' by '\ '
  local path="${inventory_path// /\\ }/group_vars/all/*.yml"
  local current_value=""
  local value=""

  # Get current value
  if [[ $lookup -eq 1 ]] ; then
    current_value=$(sed -rn "s/^[[:space:]]*${var_name}: \"\{\{ lookup\('file', '(.*)'\) \}\}\"$/\1/p" $path)
  else
    current_value=$(get_value "$var_name")
  fi

  if [[ $var_name =~ "vault_" ]] && [[ $lookup -eq 0 ]] ; then
    read -p "$prompt (sensible datas, hidden current value and prompt): " -s value
    echo -en "\n"
  else
    read -p "$prompt [$current_value]: " value
  fi

  if [[ -n "$value" ]] ; then
    # ${value//\//\\/}: string substitution, replace all '/' by '\/'
    # Needed because if there is a '/' in a variables, this broke sed syntax
    value=${value//\//\\/}
    if [[ $lookup -eq 1 ]] ; then
      sed -ri "s/^([[:space:]]*${var_name}: ).*/\1\"\{\{ lookup('file', '${value}') \}\}\"/g" $path
    else
      sed -ri "s/^([[:space:]]*${var_name}: ).*/\1${value}/" $path
    fi
  fi
}

config_ini_value(){
  local ini_path="${inventory_path}/inventory.ini"
  local group="$1"
  value=""

  # Get current value
  local current_value=$(sed -n "/\[${group}\]/{n;p;}" "$ini_path")
  read -p "${group^} server name/address[$current_value]: " value

  # If non empty input, replace the value in the inventory
  if [[ -n "$value" ]] ; then
    sed -i "/^\[${group}\]$/{n;s/.*/${value}/}" "$ini_path"
  fi
}

parse_params "$@"

cat <<EOF

#################################################
#### Bimdata On-Premise Installation Wizzard ####
#################################################

This script allow you for a quick install, not intended for production usage.
This doesn't configure HTTPS for example.

Some informations :
  - each time the script ask you to enter a value, if there is a default value \
(specified like [default_value]), you can leave the input empty to keep this value.
  - this script is really basic, this does not configure a lot of variables, for
custom installation, you should modify ansible inventory yourself.
  - None of the Ansible syntax are escaped from read inputs (stuff like {{ or {%)
    It can result in playbook error. You should escape them or use something like:
    "{% raw %} my_str {% end_raw %}" when needed.
    That also means you can use ansible syntax if you want conditional values or
    lookup a value from a file, for example.

EOF

# Create virtualenv
if [[ ! -d "$VENV_PATH" ]] ; then
  print_verb "Create virtuelenv: python3 -m venv $VENV_PATH"
  python3 -m venv $VENV_PATH
fi

# Enable it and install prerequisistes
print_verb "Enable virtualenv: source \"${VENV_PATH}/bin/activate\""
source "${VENV_PATH}/bin/activate"
pip install --upgrade pip > /dev/null

print_verb "Install python requirements: pip install -r ${SCRIPT_DIR}/requirements.txt"
pip install -r ${SCRIPT_DIR}/requirements.txt | print_verb

cat <<EOF

#################################################
####         Inventory configuration         ####
#################################################

EOF

# Choose the wanted inventory
# Get existing inventories
mapfile -t inventories < <(find ${SCRIPT_DIR}/inventories/ -mindepth 1 -maxdepth 1 -type d -not -path ${SCRIPT_DIR}/inventories/sample)

if [[ ${#inventories[@]} -ne 0 ]] ; then
  echo "You have ${#inventories[@]} existing inventory:"
  inventory_index=0
  for inventory in "${inventories[@]}" ; do
    echo "  - $inventory_index: $(basename $inventory)"
    inventory_index=$(( inventory_index + 1 ))
  done
  echo -e "\nIf you want to create a new one, enter 'create', else enter the number corresponding to the wanted inventory."
  read -p "Reading: " wanted_inventory

  number_regex="^[0-9]+$"
  if [[ $wanted_inventory =~ $number_regex ]] ; then
    if [[ $wanted_inventory -le ${#inventories[@]} ]] ; then
      inventory_path="${inventories[$wanted_inventory]}"
      vault_path="${inventory_path}/group_vars/all/vault.yml"

      if head -n1 "$vault_path" | grep -q '^$ANSIBLE_VAULT;' ; then
        read -p "This inventory have an encrypted vault. Please enter the password (hidden prompt): " -s vault_password
        if [[ -n "$vault_password" ]] ; then
          ANSIBLE_VAULT_PASSWORD=$vault_password ANSIBLE_VAULT_PASSWORD_FILE=$VAULT_SCRIPT ansible-vault decrypt $vault_path
        fi
      fi

    else
      print_err "Unknown input. Invalid ID, must be between 0 and ${#inventories[@]}."
      exit 1
    fi
  elif [[ "$wanted_inventory" =~ ^([cC][rR][eE][aA][tT][eE]|[cC])$ ]] ; then
    inventory_path=""
  else
    print_err "Unknown input. You must 'create' a new inventory or enter the ID of an existing one."
    exit 1
  fi
fi

# Create a new inventory if needed
if [[ ${#inventories[@]} -eq 0 ]] || [[ -z "$inventory_path" ]] ; then
  echo -en "\n"
  read -p "We will create a new inventory for you, please enter its name: " inventory_name
  inventory_path="${SCRIPT_DIR}/inventories/${inventory_name}"

  if [[ -d "$inventory_path" ]] ; then
    print_err "Inventory '$inventory_name' already exist. If you want to re-create it from scratch, please rename or delete ir first."
    exit 1
  fi

  print_verb "Copying the sample inventory to the wanted name: cp -r \"${SCRIPT_DIR}/inventories/sample\" \"$inventory_path\""
  cp -r "${SCRIPT_DIR}/inventories/sample" "$inventory_path"
fi

# Configure the inventory
echo -e "\nWe'll now ask you some questions to configure the deployment.\n"

# Host configuration
config_ini_value 'app'
config_ini_value 'db'
config_ini_value 'workers'

# Docker configuration
cat <<EOF

#################################################
####          Docker  configuration          ####
#################################################

EOF

config_var_value "Private docker registry name" "docker_private_registry"

config_var_value "Install and configure docker & docker-compose (true/false)" "install_docker"
docker_install=$(get_value "install_docker")
if [[ "$docker_install" =~ ^([yY][eE][sS]|[tT][rR][uU][eE])$ ]] ; then

  # This one is kind of tricky, this is in a list of yaml dicts
  # So our sed command need to match the previous line (URL of the registry) to modify the right entry
  # Then it match username line and retrieve / modify the value

  path="${inventory_path}/group_vars/all/docker_images.yml"

  # Get the current value
  current_docker_user=$(sed -rzn 's|.*[[:space:]]*- url: "https://\{\{ docker_private_registry \}\}"\n[[:space:]]*username: ([^\n]*)\n.*|\1|p' "$path")

  # If there is no value, we assume the inventory has been modify, and we don't attemp to re-modify it and let the user manage this
  if [[ -z "$current_docker_user" ]] ; then
    echo "${inventory_path}/group_vars/all/docker_images.yml seems to have been modify. The script could not modify it safely."
    echo "The deployment will only work if your modifications are right."
  else
    read -p "Private docker registry username[$current_docker_user]: " docker_user
    if [[ -n "$docker_user" ]] ; then
      sed -zri "s|([[:space:]]*- url: \"https://\{\{ docker_private_registry \}\}\"\n[[:space:]]*username: )[^\n]*\n|\1\"$docker_user\"\n|g" "$path"
    fi
  fi

  config_var_value "Private docker registry password" "vault_docker_private_registry_password"

else
  echo "WARNING! You chose to not install and configure Docker and docker-compose."
  echo "Docker and compose are needed for this script to work."
  echo "You need to install docker and docker-compose on the serveurs."
  echo "You also need to configure it to be able to download the images from the registry."

  sed -i "s/^\(install_docker: \).*/\1false/" "${inventory_path}/group_vars/all/docker.yml"
fi

# App configuration
cat <<EOF

#################################################
####        Application configuration        ####
#################################################

EOF

config_var_value "Application DNS domain" "app_dns_domain"

# Data configuration
read -p "Personalize data storage (Yes/No)[No]: " conf_storage
if [[ "$conf_storage" =~ ^([yY][eE][sS]|[Yy])$ ]] ; then
  config_var_value "Bimdata install path" "bimdata_path"
  echo "Storage type:"
  for type in ${STORAGE_TYPES[@]} ; do
    echo "  - $type"
  done

  read -p "Enter the the wanted storage type [${STORAGE_TYPES[0]}]: " storage_type

  # Set default value
  if [[ -z $storage_type ]] ; then
    storage_type=${STORAGE_TYPES[0]} ;
  fi

  if [[ "$storage_type" == "local" ]] ; then
    config_var_value "Local storage path" "bimdata_docker_volume_path"
  elif [[ "$storage_type" == "swift" ]] ; then
    sed -i "s/^\(swift_enabled: \).*/\1true/" "${inventory_path}/group_vars/all/applications.yml"
    config_var_value "Swift auth URL" "swift_auth_url"
    config_var_value "Swift tenant ID" "swift_tenant_id"
    config_var_value "Swift tenant name" "swift_tenant_name"
    config_var_value "Swift username" "swift_username"
    config_var_value "Swift password" "vault_swift_password"
    config_var_value "Swift temporary URL key" "vault_swift_temp_url_key"
    config_var_value "Swift container name" "swift_container_name"
  else
    print_err "Unknown storage type ${storage_type}, must be: ${STORAGE_TYPES[@]}."
    exit 1
  fi
fi

# SMTP configuration
echo -en "\n"
read -p "Personalize SMTP informations (Yes/No)[No]: " conf_smtp
if [[ "$conf_smtp" =~ ^([yY][eE][sS]|[Yy])$ ]] ; then
  config_var_value "SMTP Host" "smtp_host"
  config_var_value "SMTP Port" "smtp_port"
  config_var_value "SMTP User" "smtp_user"
  config_var_value "SMTP Password" "vault_smtp_password"
  config_var_value "SMTP TLS enabled" "smtp_use_tls"
  config_var_value "SMTP default email" "smtp_default_email"
fi

config_var_value "Mapbox token (https://docs.mapbox.com/help/tutorials/get-started-tokens-api/#creating-temporary-tokens)" "vault_mapbox_token"
config_var_value "Maximum upload size" "max_upload_size"

# Database configuration
cat <<EOF

#################################################
####         Database  configuration         ####
#################################################

EOF

config_var_value "Use external postgresl cluster (unmanaged by this script) (true/false)" "use_external_db"
use_external_db=$(get_value "use_external_db")
if [[ "$use_external_db" =~ ^([yY][eE][sS]|[tT][rR][uU][eE])$ ]] ; then
  config_var_value "Postgres host address" "external_db_host"
  config_var_value "Postgres port" "external_db_port"
  for db in ${DATABASES[@]} ; do
    config_var_value "${db^} database name" "db_${db}_name"
    config_var_value "${db^} database username" "db_${db}_user"
    config_var_value "${db^} database password" "vault_db_${db}_password"
  done
fi

# RabbitMQ configuration
cat <<EOF

#################################################
####         RabbitMQ  configuration         ####
#################################################

EOF

config_var_value "Use external rabbitmq cluster (unmanaged by this script) (true/false)" "use_external_rabbitmq"
use_external_rabbitmq=$(get_value "use_external_rabbitmq")
if [[ "$use_external_rabbitmq" =~ ^([yY][eE][sS]|[tT][rR][uU][eE])$ ]] ; then
  config_var_value "RabbitMQ host address" "external_rabbitmq_host"
  config_var_value "RabbitMQ port" "external_rabbitmq_port"
  config_var_value "RabbitMQ username" "rabbitmq_user"
  config_var_value "RabbitMQ password" "vault_rabbitmq_password"
fi

# TLS configuration
cat <<EOF

#################################################
####            TLS configuration            ####
#################################################

EOF

config_var_value "Use TLS (true/false)" "tls_enabled"
tls_enabled=$(get_value "tls_enabled")
if [[ "$tls_enabled" =~ ^([yY][eE][sS]|[tT][rR][uU][eE])$ ]] ; then
  echo "We will now ask you for the path of certificates and keys on *this* server."
  echo "Ansible will read the content of the file and use that in variables."

  config_var_value "CA certificate path (PEM format)" "tls_ca_certificate" "lookup"

  echo -e "SubCA need to contains all the needed sub CA. You can leave it empty."
  config_var_value "Sub CA certificate path (PEM format)" "tls_subca_certificates" "lookup"

  for app in ${TLS_APPS[@]} ; do
    config_var_value "${app^} TLS Certificate path (PEM format)" "tls_${app}_cert" "lookup"
    config_var_value "${app^} TLS Key path (PEM format)" "vault_tls_${app}_key" "lookup"
  done
fi

# Connectivity configuration
cat <<EOF

#################################################
####       Connectivity  configuration       ####
#################################################

EOF
config_var_value "Use SSH bastion (true/false)" "use_bastion"
use_bastion=$(get_value "use_bastion")
if [[ "$use_bastion" =~ ^([yY][eE][sS]|[tT][rR][uU][eE])$ ]] ; then
  config_var_value "Bastion address" "bastion_ssh_addr"
  config_var_value "Bastion port" "bastion_ssh_port"
  config_var_value "Bastion user" "bastion_ssh_user"
  config_var_value "Bastion ssh extra options" "bastion_ssh_extra_options"
fi

read -p "Servers need a proxy to access the web (Yes/No)[No]: " proxy_needed
if [[ "$proxy_needed" =~ ^([yY][eE][sS]|[Yy])$ ]] ; then
  config_var_value "HTTP Proxy (format: http://username:password@proxy.company.tld:PORT/)" "http_proxy"
  config_var_value "HTTPS Proxy (format: http://username:password@proxy.company.tld:PORT/)" "https_proxy"
  config_var_value "Proxy exclusions, must be a list (['item1', 'item2'])" "no_proxy"
fi

cat <<EOF

#################################################
####           Vault configuration           ####
#################################################

EOF

# Replace default password by random strings of [:alnum:]
# [:punct:] add too much complexe cases where escaping is needed, for now
vault_path="${inventory_path}/group_vars/all/vault.yml"

for line in $(grep -n "CHANGEME-BY-SOMETHING-SECURE" "$vault_path" | cut -d ':' -f 1) ; do
    sed -i "${line}s/CHANGEME-BY-SOMETHING-SECURE/$(cat /dev/urandom | tr -dc '[:alnum:]' | fold -w 64 | head -n 1)/" "$vault_path"
done

if [[ -z "$vault_password" ]] ; then
  echo "The vault contains sensible information but is unencrypted."
  echo "Enter a password if you want to encrypt it."
  echo "You need to remember this password or store it securly."
  echo "Leave it empty if you don't want to encrypt the vault."
  read -p "Vault password (hidden prompt): " -s vault_password
fi

if [[ -n "$vault_password" ]] ; then
  ANSIBLE_VAULT_PASSWORD=$vault_password ANSIBLE_VAULT_PASSWORD_FILE=$VAULT_SCRIPT ansible-vault encrypt $vault_path
fi

ANSIBLE_VAULT_PASSWORD=$vault_password ANSIBLE_VAULT_PASSWORD_FILE=$VAULT_SCRIPT ansible-playbook -i $inventory_path/inventory.ini install-bimdata.yml
