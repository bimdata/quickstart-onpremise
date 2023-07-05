#! /bin/bash

set -euo pipefail

src_repos=docker-registry.bimdata.io/on-premises
src_tag=20230608

dest_repos=
dest_tag=

img_list=(api connect platform platform_back iam documentation archive workers viewer_360 xkt_worker xkt_v10_worker dwg_worker image_preview_worker pdf_preview_worker pointcloud_worker)

for img in ${img_list[@]} ; do
  sudo docker pull ${src_repos}/${img}:${src_tag}
  sudo docker tag ${src_repos}/${img}:${src_tag} ${dest_repos}/${img}:${dest_tag}
  sudo docker push ${dest_repos}/${img}:${dest_tag}
done
