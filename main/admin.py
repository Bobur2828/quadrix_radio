from django.apps import apps
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

# Apps that own their admin classes — leave their models alone here.
APPS_WITH_OWN_ADMIN = {'radio', 'analytics', 'notifications', 'ads'}
EXCLUDED_MODELS = {'Session', 'ContentType', 'Permission', 'Site', 'LogEntry'}


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


for model in apps.get_models():
    if model.__name__ in EXCLUDED_MODELS:
        continue
    if model._meta.app_label in APPS_WITH_OWN_ADMIN:
        continue
    try:
        admin.site.register(model, ModelAdmin)
    except AlreadyRegistered:
        pass
