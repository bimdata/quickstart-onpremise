import docker
import os
import sys

archive_name = sys.argv[1] if len(sys.argv) == 2 else "/tmp/dumpdata.keycloak.tar"


client = docker.from_env()
api = client.containers.get("api")


def exec_run(container, cmd):
    exit_code, output = container.exec_run(cmd)
    if exit_code:
        raise Exception(output.decode("utf-8"))
    if len(output.decode("utf-8")) > 0:
        print(output.decode("utf-8"))

script_file = f"{os.path.abspath(os.path.split(__file__)[0])}/loaddata.py"

def copy_to(container, src, dst):
    os.chdir(os.path.dirname(src))
    srcname = os.path.basename(src)
    data = open(srcname).read()
    container.put_archive(os.path.dirname(dst), data)

# Copy from local
copy_to(api, "/tmp/dumpdata.keycloak.tar", "/tmp/dumpdata.keycloak.json")


# Exec data migration
exec_run(api, f"python manage.py shell -c '{open(script_file).read()}'")
