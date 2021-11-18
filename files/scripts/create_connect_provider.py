import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth.settings.connect")
django.setup()

from django.conf import settings
from oidc_provider.models import Client as OidcClient
from oidc_provider.models import ResponseType

CONNECT_URL = settings.SITE_URL

client_id = sys.argv[1]
client_secret = sys.argv[2]
iam_url = sys.argv[3]

print(sys.argv)
# create provider

if not OidcClient.objects.filter(client_id=client_id).exists():
    app = OidcClient.objects.create(
        name="keycloak",
        client_id=client_id,
        client_secret=client_secret,
        require_consent=False,
        _redirect_uris=f"{iam_url}/auth/realms/bimdata/broker/bimdataconnect/endpoint",
        _post_logout_redirect_uris=f"{iam_url}/auth/realms/bimdata/broker/bimdataconnect/endpoint/logout_response",
    )
    app.response_types.add(ResponseType.objects.get(value="code"))
