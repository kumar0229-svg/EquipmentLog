from django.apps import AppConfig


class ActivitylogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'activitylog'
    verbose_name = 'Activity Log'

    def ready(self):
        from django.core.cache import cache
        from django.db.models.signals import post_delete, post_save

        from .models import ActivityRuleConfig
        from .rules import CACHE_KEY

        def _clear_activity_rules_cache(**kwargs):
            cache.delete(CACHE_KEY)

        post_save.connect(
            _clear_activity_rules_cache, sender=ActivityRuleConfig,
            dispatch_uid='activitylog_clear_rules_cache_on_save',
        )
        post_delete.connect(
            _clear_activity_rules_cache, sender=ActivityRuleConfig,
            dispatch_uid='activitylog_clear_rules_cache_on_delete',
        )
