import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import bmr_log.models


def delete_legacy_entries(apps, schema_editor):
    # Entries created under the old single-step "Issue BMR" flow have no
    # prepare/receive/return history to backfill into the new state machine —
    # confirmed with the user to drop them rather than fabricate a history.
    BMRIssuanceEntry = apps.get_model('bmr_log', 'BMRIssuanceEntry')
    BMRIssuanceEntry.objects.all().delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bmr_log', '0003_alter_bmrissuanceentry_process_order_no'),
    ]

    operations = [
        migrations.RunPython(delete_legacy_entries, noop),
        migrations.AddField(
            model_name='bmrissuanceentry',
            name='status',
            field=models.CharField(
                choices=[
                    ('PREPARED', 'Prepared'),
                    ('RECEIVED', 'Received by Production'),
                    ('ISSUED', 'Issued'),
                    ('RETURNED', 'Returned by Production'),
                    ('VERIFIED', 'Verified'),
                    ('CLOSED', 'Received by QA'),
                ],
                default='PREPARED', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='bmrissuanceentry',
            name='prepared_by',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='bmr_entries_prepared', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='bmrissuanceentry',
            name='receive_token',
            field=models.CharField(default=bmr_log.models.generate_token, max_length=6),
        ),
        migrations.AddField(
            model_name='bmrissuanceentry',
            name='received_by',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='bmr_entries_receive_confirmed', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='bmrissuanceentry',
            name='received_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='bmrissuanceentry',
            name='returned_by',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='bmr_entries_returned', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='bmrissuanceentry',
            name='returned_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='bmrissuanceentry',
            name='return_token',
            field=models.CharField(blank=True, default='', max_length=6),
        ),
        migrations.AddField(
            model_name='bmrissuanceentry',
            name='verified_by',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='bmr_entries_verified', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='bmrissuanceentry',
            name='verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='bmrissuanceentry',
            name='received_back_by',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='bmr_entries_received_back', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='bmrissuanceentry',
            name='received_back_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='bmrissuanceentry',
            name='issued_by',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='bmr_entries_issued', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='bmrissuanceentry',
            name='issued_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='bmrissuanceentry',
            name='issued_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterModelOptions(
            name='bmrissuanceentry',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'BMR Issuance Entry',
                'verbose_name_plural': 'BMR Issuance Entries',
            },
        ),
    ]
