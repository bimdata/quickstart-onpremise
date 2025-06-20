# Quickstart On-Premises Bimdata
This ansible project aims to help you deploy the Bimdata applications on your servers.

## Prerequisites
### Online
- Ansible server:
  - python >= 3.10
  - must be able to contect through ssh to all the applicative servers
- Applicative servers:
  - python >= 3.5

### Offline
- Ansible server:
  - python >= 3.10
  - python3-request
  - ansible >= 11.4.0
  - sshpass
  - must be able to contect through ssh to all the applicative servers

- Applicative servers:
  - python >= 3.5
  - python3-request
  - docker
  - docker-compose >= 2.0
  - bzip2

## Limitations
 - This project is given "as is", Bimdata.io can't be held accountable for data loss or
 other kind of disrupt services.

 - This project is an example on how to quickly install our applications. This is
not intended for production usage. You may need to do multiple modifications to
match your infrastructure and your security needs.

 - This project do not support high availability deployment.

## How to start
Install some system dependancies:
```
sudo apt update
sudo apt install git sshpass python3-venv
```

Clone the repository:
```
git clone https://github.com/bimdata/quickstart-onpremise.git
cd quickstart-onpremise
```

You will need to install some python dependencies, you may want to do it in a
virtualenv. If this is the case, you need to create it:

```
python3 -m venv venv
source venv/bin/activate
```

Now you need to install the dependencies:
```
pip install -r requirements.txt
```

This playbook come with and example inventory. The easiest way to start is to copy this inventory and modify the copy:
```
cp -rp inventories/sample inventories/main
```

First, you need to edit the inventory file `inventories/main/inventory.ini`.
There are three groups:
  - `app`: this is where all the web app will be deploy,
  - `db`: this is where all database will be deploy if you don't use an external Postgres cluster.
  - `workers`: this is where all the workers that process datas will be deploy.

Curently, `app` and `db` do not support multiples hosts. This project can't be
use for a fully redundant infrastructure. This means you can't put multiple servers
in the groups `app` or in the group `db`.

Then, you need to modify the variables to match your needs:
  - you need to edit `inventories/main/group_vars/all/vars.yml`, add the DNS domain that will be use.
    Multiples sub-domains are needed. You can find the list in `roles/prepare_vars/defaults/main/applications.yml`.
  - you can run the command :
    ```
    vault_path="inventories/main/group_vars/all/vault.yml" ;
    for line in $(grep -n "CHANGEME-BY-SOMETHING-SECURE" "${vault_path}" | cut -d ':' -f 1) ; do
      sed -i "${line}s/CHANGEME-BY-SOMETHING-SECURE/$(cat /dev/urandom | tr -dc '[:alnum:]' | fold -w 64 | head -n 1)/" "${vault_path}"
    done
    ```
    This will initiate most of the needed secure strings. You can then edit the file and add your password, for example if one is needed for the SMTP server.

They are a lot of variables that can be added to your `inventories/main/group_vars/all/vars.yml` to customize how BIMData will be installed.
You can find them in the multiple files in `roles/prepare_vars/defaults/main/` or at the end of this file.

When everything is configured, you can deploy:
```
ansible-playbook -i inventories/main/inventory.ini install-bimdata.yml
```

You may need to add options:

| Options          | Effect                    |
|------------------|---------------------------|
| -k               | Prompt for ssh password.  |
| -K               | Prompt for sudo password. |
| --ask-vault-pass | Prompt for vault password |

If you can't use `sudo`, you can check the [Ansible documentation](https://docs.ansible.com/ansible/latest/user_guide/become.html)
on how to configure other way to manage privilege escalation.

## Upgrade
- Download the last version of the quickstart: `git fetch && git checkout $(git describe --tags $(git rev-list --tags --max-count=1))`
- Upgrade dependencies: `source venv/bin/activate && pip install -r requirements.txt`
- Upgrade inventory: `./inventory-upgrade.py main`
  The script will tell you if you need to edit some files, follow the instructions.
- Deploy the new version: `ansible-playbook -i inventories/main/inventory.ini install-bimdata.yml`
  You may need other options, for sudo for example. Check the install instruction for more details.

### applications.yml
#### Version
| Variables                   | Default value                          | Description                                                     |
|-----------------------------|----------------------------------------|-----------------------------------------------------------------|
| bimdata_version             | 20250618                               | Bimdata version, should match the first part of the github tag. |

#### DNS configuration

| Variables                   | Default value                          | Description                                            |
|-----------------------------|----------------------------------------|--------------------------------------------------------|
| app_dns_domain              | "domain.tld"                           | DNS (sub)domain use to build the app URLs.             |
| api_dns_name                | "api.{{ app_dns_domain }}"             | DNS name use for the API URL.                          |
| connect_dns_name            | "connect.{{ app_dns_domain }}"         | DNS name use for the Connect URL.                      |
| platform_back_dns_name      | "platform-back.{{ app_dns_domain }}"   | DNS name use for the Platform back URL.                |
| platform_front_dns_name     | "platform.{{ app_dns_domain }}"        | DNS name use for the Platform URL.                     |
| iam_dns_name                | "iam.{{ app_dns_domain }}"             | DNS name use for the Keycloak (identity provider) URL. |
| rabbitmq_admin_dns_name     | "rabbitmq.{{ app_dns_domain }}"        | RabbitMQ dns name.                                     |
| documentation_dns_name      | "doc.{{ app_dns_domain }}"             | DNS name use for the documentation URL.                |
| archive_dns_name            | "archive.{{ app_dns_domain }}"         | DNS name use for the archive URL.                      |
| marketplace_back_dns_name   | "marketplace-back.{{ app_dns_domain }}"| DNS name use for the marketplace back URL.             |
| marketplace_front_dns_name  | "marketplace.{{ app_dns_domain }}"     | DNS name use for fhe marketplace URL.                  |

For example if:
```
app_dns_domain: bimdata.company.tld
api_dns_name: "api.{{ app_dns_domain }}"
```

The DNS name for the API will be : `api.bimdata.company.tld`.
Each name need to be defined in the corresponding authoritative DNS server. This playbook do not manage this.

#### SMTP Configuration
| Variables          | Default value           | Description                                              |
|--------------------|-------------------------|----------------------------------------------------------|
| smtp_host          | ""                      | SMTP server address.                                     |
| smtp_port          | 587                     | SMTP server port.                                        |
| smtp_user          | ""                      | User used for the authentication on the SMTP server.     |
| smtp_pass          | "{{ vault_smtp_pass }}" | Password used for the authentication on the SMTP server. |
| smtp_use_tls       | true                    | If the SMTP connection should use TLS or not.            |
| smtp_default_email | ""                      | Email address use as default sender.                     |
| debug_mail_to      | ""                      | Email address use to send application exceptions.        |

#### Web configuration
| Variables           | Default value | Description                                       |
|---------------------|---------------|---------------------------------------------------|
| external_port_http  | 80            | TCP port for HTTP connections on the web server.  |
| external_port_https | 443           | TCP port for HTTPS connections on the web server. |
| max_upload_size     | "1g"          | Maximum upload file size (ifc… etc).              |

#### Data storage
| Variables                  | Default value                    | Description                                                 |
|----------------------------|----------------------------------|-------------------------------------------------------------|
| bimdata_path               | "/opt/bimdata"                   | Where we will install our needed files on the servers.      |
| bimdata_docker_volume_path | "{{ bimdata_path }}/data"        | Where will your data will be store on the servers.          |

Object storage (S3):

| Variables                      | Default value                          | Description                                         |
|--------------------------------|----------------------------------------|-----------------------------------------------------|
| s3_enabled                     | false                                  | Enable the S3 storage for the API.                  |
| s3_connect_enabled             | "{{ s3_enabled }}                      | Enable the S3 storage for connect.                  |
| s3_endpoint_url                | ""                                     | The s3 endpoint URL.                                |
| s3_region_name                 | ""                                     | The s3 region name.                                 |
| s3_access_key_id               | ""                                     | The s3 access key ID.                               |
| s3_secret_access_key           | "{{ vault_s3_secret_access_key }}"     | The s3 secret access key.                           |
| s3_multipart_threshold         | "{{ '5 GB' | human_to_bytes }}"        | The s3 threshold before using multipart upload.     |
| s3_storage_api_bucket_name     | ""                                     | The s3 bucket in which to store the API files.      |
| s3_storage_connect_bucket_name | ""                                     | The s3 bucket in which to store the Connect files.  |
| s3_other_options               | []                                     | List of other S3 options, need to be a list a dicts [{'name': option_name, 'value': option_value}] |
| csp_storage_url                | "https://{{ s3_storage_connect_bucket_name }}.{{ (s3_endpoint_url | urlsplit).hostname }}" | Connect needs to know the storage URL to add to its CSP. |
#### Applications configuration

| Variables                                    | Default value                                                            | Description                                                      |
|----------------------------------------------|--------------------------------------------------------------------------|------------------------------------------------------------------|
| api_secret_key                               | "{{ vault_api_secret_key }}"                                             | You should not change this.                                      |
| api_workers                                  | 8                                                                        | Number of web processes to handle requests.                      |
| api_custom_export_logo_bcf                   | false                                                                    | Configure usage of a custom logo for bcf export.                 |
||||
| connect_secret_key                           | "{{ vault_connect_secret_key }}"                                         | You should not change this.                                      |
| connect_client_id                            | "{{ 'connect_client_id' \| to_uuid(namespace=uuid_namespace) }}"         | You should not change this.                                      |
| connect_client_secret                        | "{{ 'connect_client_secret' \| to_uuid(namespace=uuid_namespace) }}"     | You should not change this.                                      |
| connect_invitation_secret                    | "{{ vault_connect_invitation_secret }}"                                  | You should not change this.                                      |
| connect_invitation_client                    | "{{ 'connect_invitation_client' \| to_uuid(namespace=uuid_namespace) }}" | You should not change this.                                      |
| connect_invitation_client_secret             | "{{ vault_connect_invitation_client_secret }}"                           | You should not change this.                                      |
| connect_use_custom_mail_templates            | false                                                                    | Configure usage of custom connect mail templates.                |
||||
| platform_back_secret_key                     | "{{ vault_platform_back_secret_key }}"                                   | You should not change this.                                      |
| platform_back_webhook_secret                 | "{{ vault_platform_back_webhook_secret }}"                               | You should not change this.                                      |
| platform_back_client_id                      | "{{ 'platform_back_client_id' \| to_uuid(namespace=uuid_namespace) }}"   | You should not change this.                                      |
| platform_back_client_secret                  | "{{ vault_platform_back_client_secret }}"                                | You should not change this.                                      |
| platform_back_use_custom_mail_templates      | false                                                                    | Configure usage of custom platform mail templates.               |
| platform_back_enable_cron                    | true                                                                     | Configure usage of cron to be able to send notifications.        |
||||
| platform_front_client_id                     | "{{ 'platform_front_client_id' | to_uuid(namespace=uuid_namespace) }}"   | You should not change this.                                      |
| platform_front_project_status_limit_new      | "5"                                                                      | Number of days during which the project is considered new.       |
| platform_front_project_status_limit_active   | "15"                                                                     | Number of days during before the project is considered inactive. |
| platform_front_authorized_identity_providers | "bimdataconnect"                                                         | Names of the authorized identity providers (comma separated).    |
||||
| iam_user                                     | "admin"                                                                  | Keycloak administrator user.                                     |
| iam_password                                 | "{{ vault_iam_password }}"                                               | Keycloak administrator password.                                 |
| iam_default_idp                              | "bimdataconnect"                                                         | Keycloak default identity provider.                              |
||||
| marketplace_enabled                          | false                                                                    | Enable / disable marketplace.                                    |
| marketplace_back_secret_key                  | "{{ vault_marketplace_back_secret_key }}"                                | You should not change this.                                      |
| marketplace_back_use_custom_mail_templates   | false                                                                    | Configure usage of custom marketplace mail templates.            |
||||
| marketplace_front_client_id                  | "{{ 'marketplace_front_client_id' | to_uuid(namespace=uuid_namespace) }}"| You should not change this.                                      |
| marketplace_front_workers                    | 2                                                                        | Number of node workers.                                          |
||||
| archive_prefix                               | "bimdata-"                                                               | Prefix use for the archive name when downloading multiple files. |
||||
| workers_export_instance                      | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_export_cpu                           | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_export_ram                           | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_export_task_timeout                  | "{{ '2h' | community.general.to_seconds | int }}"                        | Timeout for an export process.                                   |
| workers_gltf_instance                        | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_gltf_cpu                             | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_gltf_ram                             | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_gltf_task_timeout                    | "{{ '10h' | community.general.to_seconds | int }}"                       | Timeout for a GLTF process.                                      |
| workers_extract_instance                     | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_extract_cpu                          | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_extract_ram                          | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_extract_task_timeout                 | "{{ '2h' | community.general.to_seconds | int }}"                        | Timeout for an extract process.                                  |
| workers_svg_instance                         | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_svg_cpu                              | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_svg_ram                              | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_svg_task_timeout                     | "{{ '2h' | community.general.to_seconds | int }}"                        | Timeout for a SVG process.                                       |
| workers_merge_instance                       | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_merge_cpu                            | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_merge_ram                            | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_merge_task_timeout                   | "{{ '2h' | community.general.to_seconds | int }}"                        | Timeout for a merge process.                                     |
| workers_xkt_instance                         | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_xkt_cpu                              | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_xkt_ram                              | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_xkt_task_timeout                     | "{{ '3min' | community.general.to_seconds | int }}"                      | Timeout for an XKT process.                                      |
| workers_xkt_v10_instance                     | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_xkt_v10_cpu                          | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_xkt_v10_ram                          | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_xkt_v10_task_timeout                 | "{{ '3min' | community.general.to_seconds | int }}"                      | Timeout for an XKT v10 process.                                  |
| workers_preview_instance                     | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_preview_cpu                          | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_preview_ram                          | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_preview_task_timeout                 | "{{ '3min' | community.general.to_seconds | int }}"                      | Timeout for a 3D preview process.                                |
| workers_preview_2d_instance                  | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_preview_2d_cpu                       | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_preview_2d_ram                       | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_preview_2d_task_timeout              | "{{ '10min' | community.general.to_seconds | int }}"                     | Timeout for a 2D preview process.                                |
| workers_preview_pdf_instance                 | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_preview_pdf_cpu                      | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_preview_pdf_ram                      | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_preview_pdf_task_timeout             | "{{ '10min' | community.general.to_seconds | int }}"                     | Timeout for a PDF preview process.                               |
| workers_preview_office_instance              | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_preview_office_cpu                   | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_preview_office_ram                   | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_preview_office_task_timeout          | "{{ '10min' | community.general.to_seconds | int }}"                     | Timeout for a Office preview process.                            |
| workers_dwg_properties_instance              | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_dwg_properties_cpu                   | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_dwg_properties_ram                   | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_dwg_properties_task_timeout          | "{{ '1h' | community.general.to_seconds | int }}"                        | Timeout for a DWG properties process.                            |
| workers_dwg_geometries_instance              | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_dwg_geometries_cpu                   | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_dwg_geometries_ram                   | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_dwg_geometries_task_timeout          | "{{ '4h' | community.general.to_seconds | int }}"                        | Timeout for a DWG geometries process.                            |
| workers_pointcloud_instance                  | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_pointcloud_cpu                       | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_pointcloud_ram                       | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_pointcloud_task_timeout              | "{{ '10h' | community.general.to_seconds | int }}"                       | Timeout for a pointcloud process.                                |
| workers_b2d_instance                         | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_b2d_cpu                              | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_b2d_ram                              | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_b2d_task_timeout                     | "{{ '30m' | community.general.to_seconds | int }}"                       | Timeout for a B2D process.                                       |
| workers_elevation_instance                   | 1                                                                        | Number of replicas deployed on *each* worker server.             |
| workers_elevation_cpu                        | 1                                                                        | Number of CPUs allocated for each replicas.                      |
| workers_elevation_ram                        | "{{ ansible_memtotal_mb / 2 }}m"                                         | Quantity of RAM allocated for each replicas.                     |
| workers_elevation_task_timeout               | "{{ '15m' | community.general.to_seconds | int }}"                       | Timeout for a Elevation process.                                 |
||||
| run_app_initialization                       | true if first deployment else false                                      | Configure if initialization script are run.                      |
| uuid_namespace                               | "{{ app_dns_domain \| to_uuid }}"                                        | Use to generate needed UUIDs.                                    |
| master_token                                 | "{{ vault_master_token }}"                                               | Master token use for authentication between workers and API.     |
| app_env                                      | "staging"                                                                | Environnement definition for some app. Must not be changed.      |
| maptiler_token                               | Undefined                                                                | Token for authentication on the Maptiler API.                    |
| post_upgrade_version                        | Undefined                                                                | Use to force specific post upgrade tasks.                        |

### SSO
If you want to use your own userbase and connect them to BIMData services, contact us.
We support OIDC and SAMLv2 (Microsoft AD) protocols.
We also provide a service to send emails to users when they are invited to spaces or projects.
You can find email templates examples in `files/sso_invitation/mails`. You can replace those files to customize emails with your logo, colors and wording.

| Variables                  | Default value                       | Description                                                 |
|----------------------------|-------------------------------------|-------------------------------------------------------------|
| sso_invitation_enabled     | false                               | Send email to users on invitation                           |
| sso_invitation_secret      | "{{ vault_sso_invitation_secret }}" | You should not change this.                                 |

### connectivity.yml
#### Ansible connectivity
| Variables                  | Default value      | Description                   |
|----------------------------|--------------------|-------------------------------|
| ansible_python_interpreter | "/usr/bin/python3" | Force the use of python3.     |
| ansible_ssh_pipelining     | true               | Improve ansible performances. |

#### SSH Bastion
If you can't use SSH directly from this computer to the servers where you want to install
our applications, you can use a *bastion* that will proxy the ssh connections.

| Variables                 | Default value                 | Description                                    |
|---------------------------|-------------------------------|------------------------------------------------|
| use_bastion               | false                         | Configure if you want to use a bastion or not. |
| bastion_ssh_addr          | ""                            | Bastion adresse use for the ssh connection.    |
| bastion_ssh_port          | 22                            | Bastion TCP port use for the ssh connection.   |
| bastion_ssh_user          | "{{ lookup('env', 'USER') }}" | SSH user for authentication on the Bastion.    |
| bastion_ssh_extra_options | *undefined*                   | String to add other SSH options.               |

#### Proxy
If your servers can't access the web directly, you may need to configure a proxy
to access our docker registry for example.

| Variables   | Default value | Description                                            |
|-------------|---------------|--------------------------------------------------------|
| http_proxy  | ""            | HTTP proxy address.                                    |
| https_proxy | ""            | HTTPS proxy address.                                   |
| no_proxy    | []            | List of domains / IP where the proxy must not be used. |

### databases.yml
#### External postgres cluster
| Variables        | Default value | Description                                                                      |
|------------------|---------------|----------------------------------------------------------------------------------|
| use_external_db  | false         | Configure if you want to use a postgres instance manage by this playbook or not. |
| external_db_host | ""            | Postgres cluster address use for connection if use_external_db: true.            |
| external_db_port | 5432          | Postgres cluster TCP port use for connection if use_external_db: true.           |

#### Databases
| Variables               | Default value                         | Description                            |
|-------------------------|---------------------------------------|----------------------------------------|
| db_api_name             | "api"                                 | Database name for the API.             |
| db_api_user             | "api"                                 | Postgres user for the API.             |
| db_api_password         | "{{ vault_db_api_password }}"         | Postgres password for the API.         |
||||
| db_connect_name         | "connect"                             | Database name for Connect.             |
| db_connect_user         | "connect"                             | Postgres user for Connect.             |
| db_connect_password     | "{{ vault_db_connect_password }}"     | Postgres password for Connect.         |
||||
| db_platform_name        | "platform"                            | Database name for the Platform.        |
| db_platform_user        | "platform"                            | Postgres user for the Platform.        |
| db_platform_password    | "{{ vault_db_platform_password }}"    | Postgres password for the Platform.    |
||||
| db_iam_name             | "iam"                                 | Database name for Keycloak.            |
| db_iam_user             | "iam"                                 | Postgres user for Keycloak.            |
| db_iam_password         | "{{ vault_db_iam_password }}"         | Postgres password for Keycloak.        |
||||
| db_marketplace_name     | "marketplace"                         | Database name for the Marketplace.     |
| db_marketplace_user     | "marketplace"                         | Postgres user for the Marketplace.     |
| db_marketplace_password | "{{ vault_db_marketplace_password }}" | Postgres password for the Marketplace. |

If `use_external_db: false` AND if the [db] server is different from the [app] server (in the inventory)
each postgres instance will need to use its own TCP port. There are defined with these variables.
You will need to configure your firewall: the [app] server will need to be able to communication
with the [db] server on these ports.

| Variables                    | Default value                                                        | Description                                                                              |
|------------------------------|----------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| db_pg_version                | 13                                                                   | Postgres version.                                                                        |
| db_api_external_port         | 5432                                                                 | Postgres external port for the API.                                                      |
| db_connect_external_port     | 5433                                                                 | Postgres external port for Connect.                                                      |
| db_platform_external_port    | 5434                                                                 | Postgres external port for the Platform.                                                 |
| db_iam_external_port         | 5435                                                                 | Postgres external port for Keycloak.                                                     |
| db_marketplace_external_port | 5436                                                                 | Postgres external port for Keycloak.                                                     |
| db_server_addr               | "{{ hostvars[groups['db'][0]]['ansible_default_ipv4']['address'] }}" | Use to determine the IP that will be use for Postgres connection between [app] and [db]. |

### docker_images.yml
| Variables                               | Default value                                                    | Description                                                               |
|-----------------------------------------|------------------------------------------------------------------|---------------------------------------------------------------------------|
| docker_private_registry                 | "docker-registry.bimdata.io"                                     | Define the registry address from which most of the images will come from. |
| docker_registries                       |                                                                  | List of registries informations use to configure docker authentication.   |
| docker_nginx_image                      | nginxproxy/nginx-proxy                                           | Nginx docker image (use Dockerhub by default).                            |
| docker_nginx_tag                        | alpine                                                           | Nginx docker tag.                                                         |
| docker_acme_companion_image             | nginxproxy/acme-companion                                        | ACME companion (Needed only for Letsencrypt, use Dockerhub by default).   |
| docker_acme_companion_tag               | 2.2                                                              | ACME companion tag.                                                       |
| docker_rabbitmq_image                   | "rabbitmq"                                                       | RabbitMQ docker image (use Dockerhub by default).                         |
| docker_rabbitmq_tag                     | "3.8-management-alpine"                                          | RabbitMQ docker tag.                                                      |
| docker_postgres_image                   | "postgres"                                                       | Postgres docker image (use Dockerhub by default).                         |
| docker_postgres_tag                     | "{{ db_pg_version }}-alpine"                                     | Postgres docker tag.                                                      |
| docker_bimdata_tag                      | "{{ bimdata_version }}                                           | Docker tag use by all bimdata images.                                     |
| docker_api_image                        | "{{ docker_private_registry }}/on-premises/api"                  | API docker image.                                                         |
| docker_api_tag                          | "{{ docker_bimdata_tag }}"                                       | API docker tag.                                                           |
| docker_connect_image                    | "{{ docker_private_registry }}/on-premises/connect"              | Connect docker image.                                                     |
| docker_connect_tag                      | "{{ docker_bimdata_tag }}"                                       | Connect docker tag.                                                       |
| docker_platform_back_image              | "{{ docker_private_registry }}/on-premises/platform_back"        | Platform back docker image.                                               |
| docker_platform_back_tag                | "{{ docker_bimdata_tag }}"                                       | Platform back docker tag.                                                 |
| docker_platform_front_image             | "{{ docker_private_registry }}/on-premises/platform"             | Platform front docker image.                                              |
| docker_platform_front_tag               | "{{ docker_bimdata_tag }}"                                       | Platform front docker tag.                                                |
| docker_iam_image                        | "{{ docker_private_registry }}/on-premises/iam"                  | Keycloak docker image.                                                    |
| docker_iam_tag                          | "{{ docker_bimdata_tag }}"                                       | Keycloak docker tag.                                                      |
| docker_documentation_image              | "{{ docker_private_registry }}/on-premises/documentation"        | Documentation docker image.                                               |
| docker_documentation_tag                | "{{ docker_bimdata_tag }}"                                       | Documentation docker tag.                                                 |
| docker_archive_image                    | "{{ docker_private_registry }}/on-premises/archive"              | Archive docker image.                                                     |
| docker_archive_tag                      | "{{ docker_bimdata_tag }}"                                       | Archive docker tag.                                                       |
| docker_marketplace_back_image           | "{{ docker_private_registry }}/on-premise/marketplace_back"      | Marketplace back images.                                                  |
| docker_marketplace_back_tag             | "{{ docker_bimdata_tag }}"                                       | Marketplace back docker tag.                                              |
| docker_marketplace_front_image          | "{{ docker_private_registry }}/on-premise/marketplace"           | Marketplace front docker image.                                           |
| docker_marketplace_front_tag            | "{{ docker_bimdata_tag }}"                                       | Marketplace front docker tag.                                             |
| docker_workers_export_image             | "{{ docker_private_registry }}/on-premises/workers"              | Worker export docker image.                                               |
| docker_workers_export_tag               | "{{ docker_bimdata_tag }}"                                       | Worker export docker tag.                                                 |
| docker_workers_gltf_image               | "{{ docker_private_registry }}/on-premises/workers"              | Worker GLTF docker image.                                                 |
| docker_workers_gltf_tag                 | "{{ docker_bimdata_tag }}"                                       | Worker GLTF docker tag.                                                   |
| docker_workers_extract_image            | "{{ docker_private_registry }}/on-premises/workers"              | Worker extract docker image.                                              |
| docker_workers_extract_tag              | "{{ docker_bimdata_tag }}"                                       | Worker extract docker tag.                                                |
| docker_workers_svg_image                | "{{ docker_private_registry }}/on-premises/workers"              | Worker SVG docker image.                                                  |
| docker_workers_svg_tag                  | "{{ docker_bimdata_tag }}"                                       | Worker SVG docker tag.                                                    |
| docker_workers_merge_image              | "{{ docker_private_registry }}/on-premises/workers"              | Worker merge docker image.                                                |
| docker_workers_merge_tag                | "{{ docker_bimdata_tag }}"                                       | Worker merge docker tag.                                                  |
| docker_workers_xkt_image                | "{{ docker_private_registry }}/on-premises/xkt_worker"           | Worker XKT docker image.                                                  |
| docker_workers_xkt_tag                  | "{{ docker_bimdata_tag }}"                                       | Worker XKT docker tag.                                                    |
| docker_workers_xkt_v10_image            | "{{ docker_private_registry }}/on-premises/xkt_v10_worker"       | Worker XKT v10 er image.                                                  |
| docker_workers_xkt_v10_tag              | "{{ docker_bimdata_tag }}"                                       | Worker XKT v10 er tag.                                                    |
| docker_workers_preview_image            | "{{ docker_private_registry }}/on-premises/viewer_360"           | Worker preview docker image.                                              |
| docker_workers_preview_tag              | "{{ docker_bimdata_tag }}"                                       | Worker preview docker tag.                                                |
| docker_workers_preview_2d_image         | "{{ docker_private_registry }}/on-premises/image_preview_worker" | Worker preview 2D image.                                                  |
| docker_workers_preview_2d_tag           | "{{ docker_bimdata_tag }}"                                       | Worker preview 2D tag.                                                    |
| docker_workers_preview_pdf_image        | "{{ docker_private_registry }}/on-premises/pdf_preview_worker"   | Worker preview PDF image.                                                 |
| docker_workers_preview_pdf_tag          | "{{ docker_bimdata_tag }}"                                       | Worker preview PDF tag.                                                   |
| docker_workers_preview_office_image     | "{{ docker_private_registry }}/on-premises/office_preview_worker"| Worker preview Office image.                                              |
| docker_workers_preview_office_tag       | "{{ docker_bimdata_tag }}"                                       | Worker preview Office tag.                                                |
| docker_workers_dwg_image                | "{{ docker_private_registry }}/on-premises/dwg_worker"           | Worker DWG image.                                                         |
| docker_workers_dwg_tag                  | "{{ docker_bimdata_tag }}"                                       | Worker DWG tag.                                                           |
| docker_workers_b2d_image                | "{{ docker_private_registry }}/on-premises/worker_b2d"           | Worker B2D image.                                                         |
| docker_workers_b2d_tag                  | "{{ docker_bimdata_tag }}"                                       | Worker B2D tag.                                                           |
| docker_workers_elevation_image          | "{{ docker_private_registry }}/on-premises/elevation_worker"     | Worker Elevation image.                                                   |
| docker_workers_elevation_tag            | "{{ docker_bimdata_tag }}"                                       | Worker Elevation tag.                                                     |

### docker.yml
| Variables                       | Default value                                                         | Description                                                                                                  |
|---------------------------------|-----------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| install_docker                  | true                                                                  | Install Docker or not (if not, docker need to be already installed).                                         |
| docker_apt_dependencies         | ["python3-docker", "gnupg", "apt-transport-https", "ca-certificates"] | List of APT packages to install before Docker.                                                               |
| docker_apt_release_channel      | "stable"                                                              | Docker version that will be installed.                                                                       |
| docker_repo_base_url            | "https://download.docker.com/linux"                                   | Docker APT repository.                                                                                       |
| docker_apt_key_url              | "{{ docker_repo_base_url }}/{{ ansible_distribution | lower }}/gpg"   | URL of APT GPG key needed for Docker installation.                                                           |
| docker_apt_repo_url             | "{{ docker_repo_base_url }}/{{ ansible_distribution | lower }}"       | URL of APT repository for Docker installation.                                                               |
||||
| docker_edition                  | ce                                                                    | Docker edition that will be installed ('ee' for 'Enterprise Edition' or 'ce' for 'Community Edition')        |
| docker_pkg_name                 | "docker-{{ docker_edition }}"                                         | Docker APT package name that will be installed.                                                              |
| docker_pkg_version              | "5:27.*"                                                              | Docker APT package version that will be installed. (Only works for APT system currently)                     |
| docker_pkg_version_hold         | "{{ docker_pkg_version | default(false) | ternary(true, false) }}"    | Should APT be configure to hold the Docker version (false by default, true if docker_pkg_version is defined) |
||||
| docker_compose_pkg_name         | "docker-compose-plugin"                                               | Name of the docker-compose apt package.                                                                      |
| docker_compose_pkg_version      | "2.*"                                                                 | Version of the docker-compose apt package. (Only works for APT system currently)                             |
| docker_compose_pkg_version_hold | "{{ docker_compose_pkg_version | default(false) | ternary(true, false) }}"| Should APT be configure to hold the Docker compose version (false by default, true if docker_compose_pkg_version is defined) |
||||
| docker_use_extra_hosts          | false                                                                 | Add /etc/hosts value in containers if needed.                                                                |
| docker_extra_hosts              | []                                                                    | list of hosts that will be added to /etc/hosts of containers.                                                |

### nginx.yml
You should not have to modified these variables in most cases.

| Variables            | Default value | Description                 |
|----------------------|---------------|-----------------------------|
| nginx_custom_conf    |               | Nginx custom configuration. |

### rabbitmq.yml
| Variables               | Default value                   | Description                                                |
|-------------------------|---------------------------------|------------------------------------------------------------|
| use_external_rabbitmq   | false                           | Set to true if you want to use your own RabbitMQ instance. |
| external_rabbitmq_host  | ""                              | RabbitMQ cluster address if use_external_rabbitmq: true.   |
| external_rabbitmq_port  | 5672                            | RabbitMQ cluster TCP port if use_external_rabbitmq: true.  |
| rabbitmq_user           | "bimdata"                       | RabbitMQ user use for authentication.                      |
| rabbitmq_password       | "{{ vault_rabbitmq_password }}" | RabbitMQ password use for authentication.                  |
| rabbitmq_external_port  | 5672                            | RabbitMQ external port.                                    |
| rabbitmq_server_addr    | "{{ rabbitmq_admin_dns_name }}" | RabbitMQ server address.                                   |

### tls.yml
We currently support 3 ways to manage TLS configuration:
  - our reverse proxy use your tls custom ca / keys / certs: you need to set `tls_enabled` to `true` and define all the certs/keys variables.
  - you set your own custom reverse proxy for TLS manage in front of what we deploy: you need to set `tls_external` to `true`.
  - our reverse proxy manage letsencrypt certificate: you need to set `tls_acme` to `true`. Note that the server need to be accessible on internet for Letsencrypt verification.
`tls_enabled`, `tls_external` and `tls_acme` are mutualy exclusive, only one can be `true`.

| Variables                  | Default value                           | Description                                                                                                                    |
|----------------------------|-----------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| tls_enabled                | false                                   | Enable TLS with provided certs or not.                                                                                         |
| tls_external               | false                                   | Set it to true if the TLS is manage by another web server, like a reverse proxy.                                               |
| nginx_use_pregen_dh        | true                                    | Use pre-defined diffie hellman parameters. If false it'll generate new one. This take a lot of time.                           |
| tls_ca_certificate         | ""                                      | CA certificate of the CA used to sign the certificates for the applications. (PEM format.)                                     |
| tls_subca_certificates     | []                                      | If a complexe CA architecture is used, tls_ca_certificate should contain the main CA, and this list all the intermediate ones. |
| tls_key                    | "{{ vault_tls_key }}"                   | Empty by default, use by all the other tls_*_key variables. (PEM format)                                                       |
| tls_cert                   | ""                                      | Empty by default, use to define all the other tls_*_cert variables. (PEM format)                                               |
| tls_api_key                | "{{ vault_tls_key }}"                   | API TLS key (PEM format).                                                                                                      |
| tls_api_cert               | "{{ tls_cert }}"                        | API TLS Certificate (PEM format).                                                                                              |
| tls_connect_key            | "{{ vault_tls_key }}"                   | Connect TLS key (PEM format).                                                                                                  |
| tls_connect_cert           | "{{ tls_cert }}"                        | Connect TLS Certificate (PEM format).                                                                                          |
| tls_platform_back_key      | "{{ vault_tls_key }}"                   | Platform back TLS key (PEM format).                                                                                            |
| tls_platform_back_cert     | "{{ tls_cert }}"                        | Platform back TLS Certificate (PEM format).                                                                                    |
| tls_platform_front_key     | "{{ vault_tls_key }}"                   | Platform front TLS key (PEM format).                                                                                           |
| tls_platform_front_cert    | "{{ tls_cert }}"                        | Platform front TLS Certificate (PEM format).                                                                                   |
| tls_iam_key                | "{{ vault_tls_key }}"                   | Keycloak TLS key (PEM format).                                                                                                 |
| tls_iam_cert               | "{{ tls_cert }}"                        | Keycloak TLS Certificate (PEM format).                                                                                         |
| tls_rabbitmq_admin_key     | "{{ vault_tls_key }}"                   | RabbitMQ TLS key (PEM format). (Only needed if use_external_rabbitmq: false.)                                                  |
| tls_rabbitmq_admin_cert    | "{{ tls_cert }}"                        | RabbitMQ TLS Certificate (PEM format). (Only needed if use_external_rabbitmq: false.)                                          |
| tls_documentation_key      | "{{ vault_tls_key }}"                   | Documentation TLS key (PEM format).                                                                                            |
| tls_documentation_cert     | "{{ tls_cert }}"                        | Documentation TLS Certificate (PEM format).                                                                                    |
| tls_archive_key            | "{{ vault_tls_key }}"                   | Archive TLS key (PEM format).                                                                                                  |
| tls_archive_cert           | "{{ tls_cert }}"                        | Archive TLS Certificate (PEM format).                                                                                          |
| tls_marketplace_back_key   | "{{ vault_tls_key }}"                   | Marketplace back TLS key (PEM format).                                                                                         |
| tls_marketplace_back_cert  | "{{ tls_cert }}"                        | Marketplace back TLS Certificate (PEM format).                                                                                 |
| tls_marketplace_front_key  | "{{ vault_tls_key }}"                   | Marketplace front TLS key (PEM format).                                                                                        |
| tls_marketplace_front_cert | "{{ tls_cert }}"                        | Marketplace front TLS Certificate (PEM format).                                                                                |
| tls_acme                   | false                                   | Use ACME (Letsencrypt) to generate TLS certificarte.                                                                           |
| tls_acme_email             | "{{ debug_mail_to }}"                   | Email for Letsencrypt notification.                                                                                            |

### vault.yml
In this file, all private informations are defined. Like password, TLS keys or other security stuff.
You should replace all the values and encrypt the file with `ansible-vault`.

## Offline installation
On each server you need to have:
* Docker
* Docker compose v2
* python3 >= 3.5
* bzip2

You will need to do these steps before each installation or upgrade.:
* Retrieve the docker image archives and put them in `files/offline/docker`

### offline.yml
You also need to enable offline installation in the ansible inventory in
`inventories/your_inventory_name/group_vars/all/vars.yml`.

| Variables                   | Default value                      | Description                                                                                |
|-----------------------------|------------------------------------|--------------------------------------------------------------------------------------------|
| install_offline             | false                              | Enable the offline installation.                                                           |
| install_offline_cache_path  | "{{ bimdata_path }}/offline-cache" | Cache directory where archives with docker images will be stored on the servers            |
| install_offline_clear_cache | false                              | Delete the cache directory after loading the docker image (will re-upload playbook re-run) |

## Customization
### BCF Excel logo
You can customize the BCF export logo. To Do so, you need to:
  - set `api_custom_export_logo_bcf` to `true` in your `vars.yml` inventory file,
  - create the folder `files/api` in the quickstart directory,
  - create the file `bcf-xls-export-logo.png` which contains your logo in this newly created folder `files/api`,
  - re-deploy the application.

### Email templates
You can use custom emails templates for different part of our application. To do so, you need to set the variables:
  - `connect_use_custom_mail_templates`: to use custom templates for connect,
  - `platform_back_use_custom_mail_templates`: to use custom templates for the platform,
  - `marketplace_back_use_custom_mail_templates`: to use custom templates for the marketplace.

#### Connect
If you set `connect_use_custom_mail_templates` to `true`, before deploying, you need to put all the need templates into `files/connect/templates` in the quickstart folder. The files will be automatically copy into the right places on the applicative servers.

#### Platform
If you set `platform_back_use_custom_mail_templates` to `true`, before deploying, you need to put all the need templates into `files/platform-back/templates` in the quickstart folder. The files will be automatically copy into the right places on the applicative servers.

#### Marketplace
If you set `marketplace_back_use_custom_mail_templates` to `true`, before deploying, you need to put all the need templates into `files/marketplace-back/templates` in the quickstart folder. The files will be automatically copy into the right places on the applicative servers.
