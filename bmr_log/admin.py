from django.contrib import admin

from .models import BMRIssuanceEntry


@admin.register(BMRIssuanceEntry)
class BMRIssuanceEntryAdmin(admin.ModelAdmin):
    list_display = ['batch_no', 'batch_type', 'product', 'process_order_no', 'production_block', 'issued_to', 'status']
    list_filter = ['status', 'batch_type', 'production_block']
    search_fields = ['batch_no', 'process_order_no', 'master_document_no', 'product__name']
