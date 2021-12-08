#! /bin/bash

# Fail early if any issue
set -euo pipefail

# Get project path
MAIN_DIR="$(readlink -f "$0" | rev | cut -d '/' -f 4- | rev)"

# You may want to customize this
APP_ENV_FILE_PATH=${MAIN_DIR}/files/old_env/app_env
WORKER_ENV_FILE_PATH=${MAIN_DIR}/files/old_env/worker_env
INVENTORY_NAME=main

# This should be ok
INVENTORY_PATH="$MAIN_DIR/inventories/$INVENTORY_NAME"

# Some functions
# get_old_var "path_to_env_file" "my_var"
# retrieve the value of 'my_var' in 'path_to_env_file' file
function get_old_var {
  local env_path="$1"
  local var_name="$2"
  local found_lines=$(grep -c "^${var_name}=" "${env_path}")
  local return_value=""
  if [[ $found_lines -eq 1 ]] ; then
    return_value=$(grep "^${var_name}=" "${env_path}" | cut -d '=' -f2)
  else
    echo "Can't determine the value of '${var_name}' in ${MAIN_DIR}/.env."
    echo "Maybe it's not declare or it's declare multiple times."
    exit 1
  fi
  echo $return_value
}

# write_new_var "var_name" "var_value"
# Update the variable 'var_name' with the value 'var_value' in the $INVENTORY_PATH
write_new_var(){
  local var_name="${1}"
  # Escape '/' in value to preserve sed syntax
  local var_value=${2//\//\\/}

  # We use a wildcard, can't put the path between ", so we need to escape space if there is some
  local path="${INVENTORY_PATH// /\\ }/group_vars/all/*.yml"

  sed -ri "s/^([[:space:]]*${var_name}: ).*/\1${var_value}/" ${path}
}

# General
write_new_var "app_dns_domain" "$(get_old_var "${APP_ENV_FILE_PATH}" "DNS_DOMAIN")"
write_new_var "vault_master_token" "$(get_old_var "${APP_ENV_FILE_PATH}" "MASTER_TOKEN")"
write_new_var "vault_mapbox_token" "$(get_old_var "${APP_ENV_FILE_PATH}" "MAPBOX_TOKEN")"

# Web configuration
write_new_var "external_port_http" "$(get_old_var "${APP_ENV_FILE_PATH}" "PORT_PUBLIC_HTTP")"
write_new_var "external_port_https" "$(get_old_var "${APP_ENV_FILE_PATH}" "PORT_PUBLIC_HTTPS")"

# Rabbitmq
write_new_var "rabbitmq_admin_dns_name" "\"$(get_old_var "${APP_ENV_FILE_PATH}" "RABBITMQ_SUBDOMAIN").{{ app_dns_domain }}\""
write_new_var "rabbitmq_user" "$(get_old_var "${APP_ENV_FILE_PATH}" "RABBITMQ_USER")"
write_new_var "vault_rabbitmq_password" "$(get_old_var "${APP_ENV_FILE_PATH}" "RABBITMQ_PASSWORD")"

# API
write_new_var "api_dns_name" "\"$(get_old_var "${APP_ENV_FILE_PATH}" "API_SUBDOMAIN").{{ app_dns_domain }}\""
write_new_var "vault_api_secret_key" "$(get_old_var "${APP_ENV_FILE_PATH}" "API_SECRET_KEY")"

# CONNECT
write_new_var "connect_dns_name" "\"$(get_old_var "${APP_ENV_FILE_PATH}" "CONNECT_SUBDOMAIN").{{ app_dns_domain }}\""
write_new_var "vault_connect_secret_key" "$(get_old_var "${APP_ENV_FILE_PATH}" "CONNECT_SECRET_KEY")"
write_new_var "vault_connect_invitation_secret" "$(get_old_var "${APP_ENV_FILE_PATH}" "CONNECT_INVITATION_SECRET")"
write_new_var "connect_invitation_client" "$(get_old_var "${APP_ENV_FILE_PATH}" "CONNECT_INVITATION_CLIENT")"
write_new_var "vault_connect_invitation_client_secret" "$(get_old_var "${APP_ENV_FILE_PATH}" "CONNECT_INVITATION_CLIENT_SECRET")"

# PLATFORM BACK
write_new_var "platform_back_dns_name" "\"$(get_old_var "${APP_ENV_FILE_PATH}" "PLATFORM_BACK_SUBDOMAIN").{{ app_dns_domain }}\""
write_new_var "vault_platform_back_secret_key" "$(get_old_var "${APP_ENV_FILE_PATH}" "PLATFORM_BACK_SECRET_KEY")"
write_new_var "vault_platform_back_webhook_secret" "$(get_old_var "${APP_ENV_FILE_PATH}" "PLATFORM_BACK_WEBHOOK_SECRET")"

# PLATFORM
write_new_var "platform_front_dns_name" "\"$(get_old_var "${APP_ENV_FILE_PATH}" "PLATFORM_SUBDOMAIN").{{ app_dns_domain }}\""
write_new_var "platform_front_client_id" "$(get_old_var "${APP_ENV_FILE_PATH}" "PLATFORM_CLIENT_ID")"

# IAM
write_new_var "iam_dns_name" "\"$(get_old_var "${APP_ENV_FILE_PATH}" "IAM_SUBDOMAIN").{{ app_dns_domain }}\""
write_new_var "iam_user" "$(get_old_var "${APP_ENV_FILE_PATH}" "IAM_USER")"
write_new_var "vault_iam_password" "$(get_old_var "${APP_ENV_FILE_PATH}" "IAM_PASSWORD")"

# SMTP SERVICE
write_new_var "smtp_host" "$(get_old_var "${APP_ENV_FILE_PATH}" "SMTP_HOST")"
write_new_var "smtp_port" "$(get_old_var "${APP_ENV_FILE_PATH}" "SMTP_PORT")"
write_new_var "smtp_user" "$(get_old_var "${APP_ENV_FILE_PATH}" "SMTP_USER")"
write_new_var "vault_smtp_pass" "$(get_old_var "${APP_ENV_FILE_PATH}" "SMTP_PASS")"
write_new_var "smtp_use_tls" "$(get_old_var "${APP_ENV_FILE_PATH}" "SMTP_USE_TLS")"
write_new_var "smtp_default_email" "$(get_old_var "${APP_ENV_FILE_PATH}" "SMTP_DEFAULT_EMAIL")"

# WORKERS
## WORKERS EXPORT
write_new_var "workers_export_instance" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_EXPORT_INSTANCE")"
write_new_var "workers_export_cpu" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_EXPORT_CPU")"

## WORKERS GLTF
write_new_var "workers_gltf_instance" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_GLTF_INSTANCE")"
write_new_var "workers_gltf_cpu" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_GLTF_CPU")"

## WORKERS EXTRACT
write_new_var "workers_extract_instance" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_EXTRACT_INSTANCE")"
write_new_var "workers_extract_cpu" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_EXTRACT_CPU")"

## WORKERS EXTRACT WITH QUANTITIES
write_new_var "workers_extract_quantities_instance" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_EXTRACT_QUANTITIES_INSTANCE")"
write_new_var "workers_extract_quantities_cpu" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_EXTRACT_QUANTITIES_CPU")"

## WORKERS SVG
write_new_var "workers_svg_instance" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_SVG_INSTANCE")"
write_new_var "workers_svg_cpu" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_SVG_CPU")"

## WORKERS MERGE
write_new_var "workers_merge_instance" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_MERGE_INSTANCE")"
write_new_var "workers_merge_cpu" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_MERGE_CPU")"

## WORKERS XKT
write_new_var "workers_xkt_instance" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_XKT_INSTANCE")"
write_new_var "workers_xkt_cpu" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_XKT_CPU")"

## WORKERS PREVIEW
write_new_var "workers_preview_instance" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_PREVIEW_INSTANCE")"
write_new_var "workers_preview_cpu" "$(get_old_var "${WORKER_ENV_FILE_PATH}" "WORKERS_PREVIEW_CPU")"
