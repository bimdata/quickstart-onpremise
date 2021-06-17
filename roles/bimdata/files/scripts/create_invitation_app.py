import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bimdata.settings")
django.setup()

from django.conf import settings
from user.models import IdentityProvider
from client.models import ClientUser

secret = sys.argv[1]
invitation_client_id = sys.argv[2]

idp = IdentityProvider.objects.get(
    slug="bimdataconnect",
)
idp.secret = secret
idp.invitation_url = f"{settings.CONNECT_URL}/api/invitation"

idp.save()

bimdata_connect_invitation = ClientUser.objects.get(client_id=invitation_client_id)
bimdata_connect_invitation.provider = idp
bimdata_connect_invitation.save()
