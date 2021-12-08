import docker
import os

archive_name = "/var/tmp/dumpdata.keycloak.tar"

client = docker.from_env()
api = client.containers.get("api")


def exec_run(container, cmd):
    exit_code, output = container.exec_run(cmd)
    if exit_code:
        raise Exception(output.decode("utf-8"))
    if len(output.decode("utf-8")) > 0:
        print(output.decode("utf-8"))

script_file = f"{os.path.abspath(os.path.split(__file__)[0])}/create_apps_in_django.py"

def copy_to(container, src, dst):
    os.chdir(os.path.dirname(src))
    srcname = os.path.basename(src)
    data = open(srcname).read()
    container.put_archive(os.path.dirname(dst), data)

# Copy from local
copy_to(api, archive_name, "/tmp/dumpdata.keycloak.json")


# Exec data migration
exec_run(api, f"python manage.py shell -c '{open(script_file).read()}'")
