from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django_celery_beat.models import ClockedSchedule, CrontabSchedule, PeriodicTask, SolarSchedule, IntervalSchedule
from django.contrib.sites.models import Site

admin.site.unregister(ClockedSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(PeriodicTask)
admin.site.unregister(SolarSchedule)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(Site)

admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    readonly_fields = ['last_login', 'date_joined']

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        elif obj == request.user:
            return (
                (None, {'fields': ('username', 'password')}),
                ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
                ('Important dates', {'fields': ('last_login', 'date_joined')}),
            )
        else:
            return (
                (None, {'fields': ('username', 'password')}),
                ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
                ('Permissions', {'fields': ('is_staff', 'groups',)}),
                ('Important dates', {'fields': ('last_login', 'date_joined')}),
            )

    def has_change_permission(self, request, obj=None):
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return super(UserAdmin, self).has_change_permission(request, obj)

    def get_queryset(self, request):
        qs = super(UserAdmin, self).get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(is_superuser=False)
        return qs
