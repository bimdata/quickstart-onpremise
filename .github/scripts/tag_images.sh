#! /bin/bash

set -euo pipefail

src_repos=docker-registry.bimdata.io/bimdata
src_tag=prod
api_src_tag=on-premises

dest_repos=docker-registry.bimdata.io/on-premises
# Remove the last ".x" of the tag
dest_tag=${GITHUB_REF_NAME%.*}

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
  office_preview_worker
  pointcloud_worker
  worker_b2d
  elevation_worker
)

for img in ${img_list[@]} ; do
  if [[ "$img" == "api" ]]; then
    _src_tag=${api_src_tag}
  else
    _src_tag=${src_tag}
  fi

  docker pull --quiet ${src_repos}/${img}:${_src_tag}
  docker tag ${src_repos}/${img}:${_src_tag} ${dest_repos}/${img}:${dest_tag}
  docker push --quiet ${dest_repos}/${img}:${dest_tag}
done
