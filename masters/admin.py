from django.contrib import admin

from .models import (
    Area,
    Equipment,
    EquipmentType,
    EquipmentUsageType,
    Product,
    ProductEquipment,
)


class AdminOnlyMixin:
    """Master data is Admin-managed; other roles get read-only access at most."""

    def _is_admin(self, request):
        return request.user.is_authenticated and request.user.is_admin_role

    def has_add_permission(self, request):
        return self._is_admin(request)

    def has_change_permission(self, request, obj=None):
        return self._is_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self._is_admin(request)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    """Area hierarchy is QA-owned per PROJECT.md; Admin retains access too."""

    list_display = ['full_path', 'area_type', 'parent', 'active']
    list_filter = ['area_type', 'active']
    search_fields = ['name']

    def _can_edit(self, request):
        return request.user.is_authenticated and (
            request.user.is_qa or request.user.is_admin_role
        )

    def has_add_permission(self, request):
        return self._can_edit(request)

    def has_change_permission(self, request, obj=None):
        return self._can_edit(request)

    def has_delete_permission(self, request, obj=None):
        return self._can_edit(request)


@admin.register(EquipmentType)
class EquipmentTypeAdmin(AdminOnlyMixin, admin.ModelAdmin):
    list_display = ['name', 'active']
    list_filter = ['active']
    search_fields = ['name']


@admin.register(EquipmentUsageType)
class EquipmentUsageTypeAdmin(AdminOnlyMixin, admin.ModelAdmin):
    list_display = ['name', 'active']
    list_filter = ['active']
    search_fields = ['name']


@admin.register(Equipment)
class EquipmentAdmin(AdminOnlyMixin, admin.ModelAdmin):
    list_display = ['code', 'name', 'equipment_type', 'area', 'state', 'is_movable', 'active']
    list_filter = ['equipment_type', 'area', 'state', 'is_movable', 'active']
    search_fields = ['code', 'name']


class ProductEquipmentInline(admin.TabularInline):
    model = ProductEquipment
    extra = 1


@admin.register(Product)
class ProductAdmin(AdminOnlyMixin, admin.ModelAdmin):
    list_display = ['name', 'active']
    list_filter = ['active', 'streams']
    search_fields = ['name']
    filter_horizontal = ['streams']
    inlines = [ProductEquipmentInline]
