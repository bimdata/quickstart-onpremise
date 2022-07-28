import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bimdata.settings.api")
django.setup()

from django.conf import settings
from user.models import IdentityProvider
from app.models import App, Scope
from externals.keycloak import request

secret = sys.argv[1]
invitation_client_id = sys.argv[2]
invitation_client_secret = sys.argv[3]
platform_client_id = sys.argv[4]
client_id = sys.argv[5]
client_secret = sys.argv[6]
platform_url = sys.argv[7]
marketplace_url = sys.argv[8]
marketplace_client_id = sys.argv[9]
connect_url = sys.argv[10]

changed = False

# create provider
idp = IdentityProvider.objects.get(
    slug="bimdataconnect",
)

if idp.secret != secret or idp.invitation_url != f"{connect_url}/api/invitation":
    idp.secret = secret
    idp.invitation_url = f"{connect_url}/api/invitation"
    idp.save()
    changed = True

# create invitation app
try:
    invitation_app = App.objects.get(client_id=invitation_client_id)
except App.DoesNotExist:
    invitation_app = App.objects.create(
        name="BIMData Connect IDP",
        redirect_uris=[connect_url],
        creator=None,
        access_type=App.TYPE_CONFIDENTIAL,
        implicit_flow_enabled=False,
        client_id=invitation_client_id,
        client_secret=invitation_client_secret,
        base_url=connect_url,
        provider=idp,
    )
    invitation_app.scopes.add(Scope.objects.get(name="org:manage"))
    changed = True

# create plarform app
try:
    platform_app = App.objects.get(client_id=platform_client_id)
except App.DoesNotExist:
    platform_app = App.objects.create(
        name="BIMData Platform",
        redirect_uris=[platform_url + "/*"],
        creator=None,
        access_type=App.TYPE_PUBLIC,
        implicit_flow_enabled=False,
        client_id=platform_client_id,
        base_url=platform_url,
    )
    platform_app.scopes.set(Scope.objects.all())
    changed = True

# create marketplace app
try:
    marketplace_app = App.objects.get(client_id=marketplace_client_id)
except App.DoesNotExist:
    marketplace_app = App.objects.create(
        name="BIMData Marketplace",
        redirect_uris=[marketplace_url + "/*"],
        creator=None,
        access_type=App.TYPE_PUBLIC,
        implicit_flow_enabled=False,
        client_id=marketplace_client_id,
        base_url=marketplace_url,
    )
    marketplace_app.scopes.set(Scope.objects.all())
    changed = True

for app in [invitation_app, platform_app, marketplace_app]:
    request(verb="put", endpoint=f"/clients/{app.keycloak_id}", json={"consentRequired": False})

# Keycloak config
data = {
    "config": {
        "useJwksUrl": "true",
        "hideOnLoginPage": "",
        "loginHint": "",
        "uiLocales": "",
        "backchannelSupported": "",
        "disableUserInfo": "",
        "acceptsPromptNoneForwardFromClient": "",
        "validateSignature": "true",
        "authorizationUrl": f"{connect_url}/authorize",
        "tokenUrl": f"{connect_url}/token",
        "logoutUrl": f"{connect_url}/end-session",
        "userInfoUrl": f"{connect_url}/userinfo",
        "clientAuthMethod": "client_secret_post",
        "clientId": client_id,
        "clientSecret": client_secret,
        "issuer": f"{connect_url}",
        "defaultScope": "openid profile email",
        "jwksUrl": f"{connect_url}/jwks",
    },
    "alias": "bimdataconnect",
    "providerId": "oidc",
    "enabled": True,
    "authenticateByDefault": False,
    "firstBrokerLoginFlowAlias": "first broker login",
    "postBrokerLoginFlowAlias": "",
    "storeToken": "",
    "addReadTokenRoleOnCreate": "",
    "trustEmail": "",
    "linkOnly": "",
    "displayName": "BIMData Connect",
}

if request("get", "/identity-provider/instances/bimdataconnect", raise_for_status=False).status_code != 200:
    request("post", "/identity-provider/instances", json=data)
    changed = True

keycloak_mappers = (
    {
        "identityProviderAlias": "bimdataconnect",
        "config": {"user.attribute": "lastName", "claim": "family_name"},
        "name": "lastName",
        "identityProviderMapper": "oidc-user-attribute-idp-mapper",
    },
    {
        "identityProviderAlias": "bimdataconnect",
        "config": {"user.attribute": "firstName", "claim": "given_name"},
        "name": "firstName",
        "identityProviderMapper": "oidc-user-attribute-idp-mapper",
    },
    {
        "identityProviderAlias": "bimdataconnect",
        "config": {"user.attribute": "picture", "claim": "picture"},
        "name": "profilePicture",
        "identityProviderMapper": "oidc-user-attribute-idp-mapper",
    },
    {
        "identityProviderAlias": "bimdataconnect",
        "config": {"user.attribute": "language", "claim": "language"},
        "name": "language",
        "identityProviderMapper": "oidc-user-attribute-idp-mapper",
    },
    {
        "identityProviderAlias": "bimdataconnect",
        "config": {"user.attribute": "provider_sub", "claim": "sub"},
        "name": "provider_sub",
        "identityProviderMapper": "oidc-user-attribute-idp-mapper",
    },
    {
        "identityProviderAlias": "bimdataconnect",
        "config": {"template": "${ALIAS}.${CLAIM.email}"},
        "name": "username",
        "identityProviderMapper": "oidc-username-idp-mapper",
    },
)

existing_mappers = []

response = request(
    "get", "/identity-provider/instances/bimdataconnect/mappers", raise_for_status=False
)
if response.status_code == 200:
    existing_mappers = response.json()

for mapper in keycloak_mappers:
    if not next((x for x in existing_mappers if x["name"] == mapper["name"]), None):
        request(
            "post", "/identity-provider/instances/bimdataconnect/mappers", json=mapper
        )
        changed = True


for app, role_name in zip(
    [platform_app, marketplace_app], ["bimdata_platform", "bimdata_marketplace"]
):
    bimdata_mapper = {
        "name": role_name,
        "protocol": "openid-connect",
        "protocolMapper": "oidc-hardcoded-role-mapper",
        "config": {"role": role_name},
    }

    response = request(
        "get",
        f"/clients/{app.keycloak_id}/protocol-mappers/models",
        raise_for_status=True,
    ).json()

    if not next((x for x in response if x["name"] == role_name), None):
        request(
            "post",
            f"/clients/{app.keycloak_id}/protocol-mappers/models",
            json=bimdata_mapper,
        )
        changed = True

print({"changed": changed})
