from django.apps import AppConfig
from django.db.models.signals import post_migrate
import os


def create_superadmin(sender, **kwargs):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    username = os.getenv("DJANGO_SUPERUSER_USERNAME", "superadmin")
    email = os.getenv("DJANGO_SUPERUSER_EMAIL", "superadmin@gmail.com")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "superadmin")

    if not User.objects.filter(email=email).exists():
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            role="superadmin",
            isEmailVerified=True,  
            is_superuser=True,
        )
        print(" Default superadmin created.")


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"

    def ready(self):
        if os.getenv("CREATE_SUPERADMIN") == "True":
            post_migrate.connect(create_superadmin, sender=self)
