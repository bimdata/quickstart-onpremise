from django.core.management.color import no_style
from django.db import connection
from django.db.models.signals import m2m_changed
from django.db.models.signals import pre_save
from app.models import App
from app.models import Scope
from app.models import AppCloudAuthorization
from app.signals import sync_scopes
from app.signals import create_scope
from app.signals import create_keycloak_client
from django.core import management
from client.models import ClientUser
from client.models import ClientCloudAuthorization
import json


def first_available_id(apps):
    apps.sort(key=lambda app: int(app.pk))
    for i, app in enumerate(apps[:-1]):
        if app.pk + 1 != apps[i + 1].pk:
            return app.pk + 1
    return apps[-1].pk + 1


tmp_file = "/tmp/dumpdata.keycloak.json"

m2m_changed.disconnect(receiver=sync_scopes, sender=App.scopes.through)
pre_save.disconnect(receiver=create_scope, sender=Scope)
pre_save.disconnect(receiver=create_keycloak_client, sender=App)

management.call_command("migrate", app_label="app", migration_name="0002_auto_20200902_1339")
management.call_command(
    "migrate", app_label="ifc", migration_name="0064_auto_20200902_1339"
)
management.call_command(
    "migrate", app_label="client", migration_name="0013_auto_20200819_0707"
)
management.call_command(
    "migrate", app_label="organization", migration_name="0064_cloud_organization"
)

app_table = []
no_client_id_apps = []
scope_table = []
app_scope_m2m = []

with open(tmp_file) as f:
    datas = json.load(f)
    for data in datas:
        if data.get("model") == "keycloak.client":
            fields = data.get("fields")
            fields["redirect_uris"] = json.loads(fields["redirect_uris"])
            try:
                client_id = fields.get("client_id")
                client_user = ClientUser.objects.get(client_id=client_id)
                fields["pk"] = client_user.pk
                fields["provider_id"] = client_user.provider_id
                for scope in fields.pop("scopes"):
                    app_scope_m2m.append({"app": fields["pk"], "scope": scope})
                app_table.append(App(**fields))
            except ClientUser.DoesNotExist:
                no_client_id_apps.append(fields)
                print(f"ClientUser with id = {client_id} does not exists")

        elif data.get("model") == "keycloak.scope":
            fields = data.get("fields")
            fields["pk"] = data.get("pk")
            scope_table.append(Scope(**fields))
    for fields in no_client_id_apps:
        fields["pk"] = first_available_id(app_table)
        for scope in fields.pop("scopes"):
            app_scope_m2m.append({"app": fields["pk"], "scope": scope})
        app_table.append(App(**fields))


App.objects.bulk_create(app_table)
Scope.objects.bulk_create(scope_table)

for data in app_scope_m2m:
    scope = Scope.objects.get(pk=data.get("scope"))
    scope.app_set.add(data.get("app"))


app_cloud_table = []
for auth in ClientCloudAuthorization.objects.prefetch_related("client").all():
    client_id = auth.client.client_id
    try:
        new_app = App.objects.get(client_id=client_id)
        app_cloud_table.append(
            AppCloudAuthorization(client=new_app, cloud=auth.cloud, scopes=auth.scopes)
        )
    except App.DoesNotExist:
        print(f"App with client_id = {client_id} does not exists")

AppCloudAuthorization.objects.bulk_create(app_cloud_table)

sequence_sql = connection.ops.sequence_reset_sql(
    no_style(),
    [App, Scope, AppCloudAuthorization],
)

with connection.cursor() as cursor:
    for sql in sequence_sql:
        cursor.execute(sql)
