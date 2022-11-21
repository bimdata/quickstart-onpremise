#! /bin/bash

set -euo pipefail

src_repos=docker-registry.bimdata.io/on-premises
src_tag=20221118

dest_repos=
dest_tag=

img_list=(api connect platform platform_back iam documentation archive marketplace_back marketplace workers viewer_360 xkt_worker dwg_worker image_preview_worker)

for img in ${img_list[@]} ; do
  sudo docker pull ${src_repos}/${img}:${src_tag}
  sudo docker tag ${src_repos}/${img}:${src_tag} ${dest_repos}/${img}:${dest_tag}
  sudo docker push ${dest_repos}/${img}:${dest_tag}
done
