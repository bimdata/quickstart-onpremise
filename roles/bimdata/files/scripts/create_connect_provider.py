import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth.settings")
django.setup()

from django.conf import settings
from oidc_provider.models import Client as OidcClient
from oidc_provider.models import ResponseType

CONNECT_URL = settings.SITE_URL

client_id = sys.argv[1]
client_secret = sys.argv[2]
iam_url = sys.argv[3]
invitation_client_id = sys.argv[4]
invitation_client_secret = sys.argv[5]
platform_client_id = sys.argv[6]

print(sys.argv)
# create provider
app = OidcClient.objects.create(
    name="keycloak",
    client_id=client_id,
    client_secret=client_secret,
    require_consent=False,
    _redirect_uris=f"{iam_url}/auth/realms/bimdata/broker/bimdataconnect/endpoint",
    _post_logout_redirect_uris=f"{iam_url}/auth/realms/bimdata/broker/bimdataconnect/endpoint/logout_response",
)
app.response_types.add(ResponseType.objects.get(value="code"))

from keycloak.models import Client, Scope

# create invitation app
invitation_app = Client.create(
    name="BIMData Connect IDP",
    redirect_uris=[settings.SITE_URL],
    creator=None,
    access_type=Client.TYPE_CONFIDENTIAL,
    implicit_flow_enabled=False,
    client_id=invitation_client_id,
    secret=invitation_client_secret,
    base_url=settings.SITE_URL
)
invitation_app.scopes.add(Scope.objects.get(name="org:manage"))

# create plarform app
platform_app = Client.create(
    name="BIMData Platform",
    redirect_uris=[settings.PLATFORM_URL + "/*"],
    creator=None,
    access_type=Client.TYPE_PUBLIC,
    implicit_flow_enabled=False,
    client_id=platform_client_id,
    base_url=settings.PLATFORM_URL
)
platform_app.scopes.set(Scope.objects.all())

from externals.keycloak import request

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
        "authorizationUrl": f"{CONNECT_URL}/authorize",
        "tokenUrl": f"{CONNECT_URL}/token",
        "logoutUrl": f"{CONNECT_URL}/end-session",
        "userInfoUrl": f"{CONNECT_URL}/userinfo",
        "clientAuthMethod": "client_secret_post",
        "clientId": client_id,
        "clientSecret": client_secret,
        "issuer": f"{CONNECT_URL}",
        "defaultScope": "openid profile email",
        "jwksUrl": f"{CONNECT_URL}/jwks",
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

request("post", "/identity-provider/instances", json=data)

last_name_body = {
    "identityProviderAlias": "bimdataconnect",
    "config": {"user.attribute": "lastName", "claim": "family_name"},
    "name": "lastName",
    "identityProviderMapper": "oidc-user-attribute-idp-mapper",
}

response = request(
    "post", "/identity-provider/instances/bimdataconnect/mappers", json=last_name_body
)

first_name_body = {
    "identityProviderAlias": "bimdataconnect",
    "config": {"user.attribute": "firstName", "claim": "given_name"},
    "name": "firstName",
    "identityProviderMapper": "oidc-user-attribute-idp-mapper",
}
response = request(
    "post", "/identity-provider/instances/bimdataconnect/mappers", json=first_name_body
)

provider_sub_body = {
    "identityProviderAlias": "bimdataconnect",
    "config": {"user.attribute": "provider_sub", "claim": "sub"},
    "name": "provider_sub",
    "identityProviderMapper": "oidc-user-attribute-idp-mapper",
}
response = request(
    "post",
    "/identity-provider/instances/bimdataconnect/mappers",
    json=provider_sub_body,
)

username_body = {
    "identityProviderAlias": "bimdataconnect",
    "config": {"template": "${ALIAS}.${CLAIM.email}"},
    "name": "username",
    "identityProviderMapper": "oidc-username-idp-mapper",
}
response = request(
    "post", "/identity-provider/instances/bimdataconnect/mappers", json=username_body
)
