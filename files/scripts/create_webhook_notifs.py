import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "platform_back.settings.platform_back")
django.setup()

def run():
    try:
        from admin.views import register_webhooks
    except ModuleNotFoundError:
        return False
    count = register_webhooks()
    return count > 0

print({"changed": run()})
