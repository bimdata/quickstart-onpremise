import docker
import json
import tarfile

archive_name = "/var/tmp/dumpdata.keycloak.tar"

client = docker.from_env()
auth = client.containers.get("connect")
api = client.containers.get("api")

tmp_loc = "/tmp/"
tmp_dumpdata = "dumpdata"
tmp_dir = tmp_loc + tmp_dumpdata
tmp_keycloak_file = "keycloak.json"
tmp_user_file = "user.json"
tmp_fosuser_file = "fosuser.json"


def exec_run(container, cmd):
    exit_code, output = container.exec_run(cmd)
    if exit_code:
        raise Exception(output.decode("utf-8"))
    if len(output.decode("utf-8")) > 0:
        print(output.decode("utf-8"))


def copy_from(container, src, dst):
    f = open(dst, "wb")
    bits, stat = container.get_archive(src)
    for chunk in bits:
        f.write(chunk)
    f.close()


# Dump data in file inside container
exec_run(auth, f"bash -c 'mkdir -p {tmp_dir}'")
exec_run(api, f"bash -c 'mkdir -p {tmp_dir}'")
exec_run(
    auth,
    f"bash -c 'python manage.py dumpdata keycloak --output {tmp_dir}/{tmp_keycloak_file}'",
)
exec_run(
    auth,
    f"bash -c 'python manage.py dumpdata user.user --output {tmp_dir}/{tmp_user_file}'",
)

exec_run(
    api,
    f"bash -c 'python manage.py dumpdata user.fosuser --output {tmp_dir}/{tmp_fosuser_file}'",
)

# Copy file to local
copy_from(auth, tmp_dir, tmp_dir)
copy_from(api, tmp_dir, tmp_loc + "dump_api_fosuser")

tar = tarfile.open(tmp_loc + "dump_api_fosuser")
file_api_fosuser = tar.extractfile(tmp_dumpdata + "/" + tmp_fosuser_file)

with tarfile.open(tmp_dir, "r") as archive:
    file_auth_keycloak = archive.extractfile(tmp_dumpdata + "/" + tmp_keycloak_file)
    file_auth_user = archive.extractfile(tmp_dumpdata + "/" + tmp_user_file)
    data_auth_keycloak = json.load(file_auth_keycloak)
    data_auth_user = json.load(file_auth_user)
    data_api_fosuser = json.load(file_api_fosuser)

    for obj in data_auth_keycloak:
        if obj["model"] == "keycloak.client":
            creator_id = obj["fields"].pop("creator")
            if creator_id:
                email = next(
                    x["fields"]["email"]
                    for x in data_auth_user
                    if x["pk"] == creator_id
                )
                fosuser_id = next(
                    (
                        x["pk"]
                        for x in data_api_fosuser
                        if x["fields"]["email"] == email
                        and x["fields"]["provider"] == 1
                    ),
                    None,
                )
                if fosuser_id is None:
                    print(f"{email} not found in api db : fosuser")
                obj["fields"]["creator_id"] = fosuser_id

    with open("/tmp/dumpdata.keycloak.json", "w") as f:
        json.dump(data_auth_keycloak, f)
    with tarfile.open(archive_name, mode="w") as tar:
        tar.add("/tmp/dumpdata.keycloak.json", arcname="dumpdata.keycloak.json")