#!/usr/bin/bash

# This is a really naive script without any optimization

# Object storage config
s3_endpoint_url=""
s3_region_name=""
s3_access_key_id=""
s3_secret_access_key=""
s3_bucket_name=""

# Storage path
local_storage_path="/opt/bimdata/data/web/api_storage"

export AWS_ACCESS_KEY_ID=${s3_access_key_id}
export AWS_SECRET_ACCESS_KEY=${s3_secret_access_key}

# For all file in the local storage folder, we compute retrieve the full path
# The we compute the corresponding s3 key by removing the useless part
# Then we copy it with the AWS cli to the configured bucket
find ${local_storage_path} -type f | while read line ; do
  file=${line}
  s3_key=${line#"$local_storage_path"}
  aws --endpoint-url ${s3_endpoint_url} --region ${s3_region_name} s3 cp ${file} s3://${s3_bucket_name}${s3_key}
done
