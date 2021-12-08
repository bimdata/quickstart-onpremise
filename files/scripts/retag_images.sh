#! /bin/bash

set -euo pipefail

src_repos=docker-registry.bimdata.io/on-premises
src_tag=20211208

dest_repos=
dest_tag=

img_list=(api connect platform platform_back iam documentation archive workers viewer_360 xkt_worker)

for img in ${img_list[@]} ; do
  sudo docker pull ${src_repos}/${img}:${src_tag}
  sudo docker tag ${src_repos}/${img}:${src_tag} ${dest_repos}/${img}:${dest_tag}
  sudo docker push ${dest_repos}/${img}:${dest_tag}
done

# Special image needed for migration
migration_img="api:apps_from_connect_to_api"
sudo docker pull ${src_repos}/${migration_img}
sudo docker tag ${src_repos}/${migration_img} ${dest_repos}/${migration_img}
sudo docker push ${dest_repos}/${migration_img}
