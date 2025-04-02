#! /bin/bash

set -euo pipefail

src_repos=docker-registry.bimdata.io/bimdata
src_tag=prod

dest_repos=docker-registry.bimdata.io/on-premises
dest_tag=20250402

img_list=(
  api
  connect
  platform
  platform_back
  marketplace
  marketplace_back
  iam
  documentation
  archive
  sso_invitation_email_sender
  workers
  viewer_360
  xkt_worker
  xkt_v10_worker
  dwg_worker
  image_preview_worker
  pdf_preview_worker
  pointcloud_worker
  worker_b2d
  elevation_worker
)

for img in ${img_list[@]} ; do
  sudo docker pull ${src_repos}/${img}:${src_tag}
  sudo docker tag ${src_repos}/${img}:${src_tag} ${dest_repos}/${img}:${dest_tag}
  sudo docker push ${dest_repos}/${img}:${dest_tag}
done
