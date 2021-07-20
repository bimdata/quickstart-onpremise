import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bimdata.settings")
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

# create provider
idp = IdentityProvider.objects.get(
    slug="bimdataconnect",
)
idp.secret = secret
idp.invitation_url = f"{settings.CONNECT_URL}/api/invitation"

idp.save()

# create invitation app
invitation_app, created = App.objects.get_or_create(
    name="BIMData Connect IDP",
    redirect_uris=[settings.CONNECT_URL],
    creator=None,
    access_type=App.TYPE_CONFIDENTIAL,
    implicit_flow_enabled=False,
    client_id=invitation_client_id,
    client_secret=invitation_client_secret,
    base_url=settings.CONNECT_URL,
    provider=idp
)
if created:
    invitation_app.scopes.add(Scope.objects.get(name="org:manage"))

# create plarform app
platform_app, created = App.objects.get_or_create(
    name="BIMData Platform",
    redirect_uris=[platform_url + "/*"],
    creator=None,
    access_type=App.TYPE_PUBLIC,
    implicit_flow_enabled=False,
    client_id=platform_client_id,
    base_url=platform_url
)
if created:
    platform_app.scopes.set(Scope.objects.all())

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
        "authorizationUrl": f"{settings.CONNECT_URL}/authorize",
        "tokenUrl": f"{settings.CONNECT_URL}/token",
        "logoutUrl": f"{settings.CONNECT_URL}/end-session",
        "userInfoUrl": f"{settings.CONNECT_URL}/userinfo",
        "clientAuthMethod": "client_secret_post",
        "clientId": client_id,
        "clientSecret": client_secret,
        "issuer": f"{settings.CONNECT_URL}",
        "defaultScope": "openid profile email",
        "jwksUrl": f"{settings.CONNECT_URL}/jwks",
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

keycloak_mappers=(
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
        "config": {"user.attribute": "provider_sub", "claim": "sub"},
        "name": "provider_sub",
        "identityProviderMapper": "oidc-user-attribute-idp-mapper",
    },
    {
        "identityProviderAlias": "bimdataconnect",
        "config": {"template": "${ALIAS}.${CLAIM.email}"},
        "name": "username",
        "identityProviderMapper": "oidc-username-idp-mapper",
    }
)

existing_mappers = []

response = request("get", "/identity-provider/instances/bimdataconnect/mappers", raise_for_status=False)
if response.status_code == 200:
    existing_mappers = response.json()

for mapper in keycloak_mappers:
    if not next((x for x in existing_mappers if x['name'] == mapper['name']), None):
        request("post", "/identity-provider/instances/bimdataconnect/mappers", json=mapper)
