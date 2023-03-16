#!/usr/bin/bash

# Object storage
s3_endpoint_url=""
s3_region_name=""
s3_access_key_id=""
s3_secret_access_key=""
s3_bucket_name=""

# Storage path
local_storage_path="/opt/bimdata/data/web/api_storage"

# Other configs
gzip_content_types="
  text/plain
  application/json
  application/octet-stream
  image/svg+xml
  text/xml
  model/gltf+json
  application/p21
  application/pdf
  application/msword
  application/vnd.ms-excel
  text/csv
"

force_default_content_types="
  application/p21
"
export AWS_ACCESS_KEY_ID=${s3_access_key_id}
export AWS_SECRET_ACCESS_KEY=${s3_secret_access_key}

find ${local_storage_path} -type f | while read line ; do
  file=${line}
  s3_key=${line#"$local_storage_path"}
  file_mime_type=$(file --brief --mime-type $file)

  # Some content types need to be change, because of firefox behavior when downloaded
  if [[ "$(echo $force_default_content_types)" =~ ( |^)$file_mime_type( |$) ]] ; then
    file_mime_type="application/octet-stream"
  fi

  if [[ "$(echo $gzip_content_types)" =~ ( |^)$file_mime_type( |$) ]] ; then
    gzip -c ${file} | aws --endpoint-url ${s3_endpoint_url} --region ${s3_region_name} s3 cp - s3://${s3_bucket_name}${s3_key} --content-type ${file_mime_type} --content-encoding 'gzip'
  else
    aws --endpoint-url ${s3_endpoint_url} --region ${s3_region_name} s3 cp ${file} s3://${s3_bucket_name}${s3_key} --content-type ${file_mime_type}
  fi
done
