#! /bin/bash

set -euo pipefail

archive_path="./files/offline/docker"

src_private_repos=docker-registry.bimdata.io/on-premises
src_private_tag=20251114

app_images=(
  rabbitmq:3.12-management-alpine
  nginxproxy/nginx-proxy:alpine
  nginxproxy/acme-companion:2.2
  ${src_private_repos}/api:${src_private_tag}
  ${src_private_repos}/iam:${src_private_tag}
  ${src_private_repos}/connect:${src_private_tag}
  ${src_private_repos}/platform:${src_private_tag}
  ${src_private_repos}/platform_back:${src_private_tag}
  ${src_private_repos}/documentation:${src_private_tag}
  ${src_private_repos}/archive:${src_private_tag}
  ${src_private_repos}/marketplace_back:${src_private_tag}
  ${src_private_repos}/marketplace:${src_private_tag}
  ${src_private_repos}/sso_invitation_email_sender:${src_private_tag}
)

db_images=(
  postgres:13
  postgres:17
  tianon/postgres-upgrade:13-to-17
)

worker_images=(
  ${src_private_repos}/workers:${src_private_tag}
  ${src_private_repos}/viewer_360:${src_private_tag}
  ${src_private_repos}/xkt_worker:${src_private_tag}
  ${src_private_repos}/xkt_v10_worker:${src_private_tag}
  ${src_private_repos}/dwg_worker:${src_private_tag}
  ${src_private_repos}/image_preview_worker:${src_private_tag}
  ${src_private_repos}/pdf_preview_worker:${src_private_tag}
  ${src_private_repos}/office_preview_worker:${src_private_tag}
  ${src_private_repos}/pointcloud_worker:${src_private_tag}
  ${src_private_repos}/worker_b2d:${src_private_tag}
  ${src_private_repos}/elevation_worker:${src_private_tag}
)

app_archive_path="${archive_path}/docker-app-images-${src_private_tag}.tar.bz2"
db_archive_path="${archive_path}/docker-bdd-images-${src_private_tag}.tar.bz2"
worker_archive_path="${archive_path}/docker-worker-images-${src_private_tag}.tar.bz2"

echo "Pulling the images..."
for img in ${app_images[@]} ${db_images[@]} ${worker_images[@]} ; do
    sudo docker pull ${img}
done

echo "Creating archive directory if it does not exist..."
mkdir -p ${archive_path}

echo "Creating app archive in ${app_archive_path}..."
sudo docker save ${app_images[@]} | bzip2 > ${app_archive_path}

echo "Creating db archive in ${db_archive_path}..."
sudo docker save ${db_images[@]} | bzip2 > ${db_archive_path}

echo "Creating worker archive in ${worker_archive_path}..."
sudo docker save ${worker_images[@]} | bzip2 > ${worker_archive_path}
