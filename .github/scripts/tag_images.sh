#! /bin/bash

set -euo pipefail

src_repos=docker-registry.bimdata.io/bimdata
src_tag=prod

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
  pointcloud_worker
)

for img in ${img_list[@]} ; do
  docker pull --quiet ${src_repos}/${img}:${src_tag}
  docker tag ${src_repos}/${img}:${src_tag} ${dest_repos}/${img}:${dest_tag}
  docker push --quiet ${dest_repos}/${img}:${dest_tag}
done
