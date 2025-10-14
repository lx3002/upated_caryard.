from django.apps import AppConfig

class CaryardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'caryard'

    def ready(self):
        import caryard.signals  # noqa
