from django.db import migrations, models

# Calibration usage type was already deactivated (0006) since it has no Activity
# Rules entry; the leftover "Under Calibration" equipment state is retired too.


def reassign_under_calibration(apps, schema_editor):
    Equipment = apps.get_model('masters', 'Equipment')
    Equipment.objects.filter(state='UNDER_CALIBRATION').update(state='NOT_IN_USE')


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0006_deactivate_calibration_usage_type'),
    ]

    operations = [
        migrations.RunPython(reassign_under_calibration, noop),
        migrations.AlterField(
            model_name='equipment',
            name='state',
            field=models.CharField(choices=[('AVAILABLE', 'Available'), ('IN_PROCESS', 'In-Process'), ('IN_USE', 'In Use'), ('TO_BE_PRESERVED', 'To Be Preserved'), ('UNDER_CLEANING', 'Under Cleaning'), ('TO_BE_CLEANED', 'To Be Cleaned'), ('CLEANED_TYPE_A', 'Cleaned Type A'), ('CLEANED_READY_FOR_QA', 'Cleaned and Ready for QA Certification'), ('UNDER_QA_CERTIFICATION', 'Under QA Certification'), ('CLEANED_AND_QA_CERTIFIED', 'Cleaned and QA Certified'), ('CLEANED_AFTER_MAINTENANCE', 'Cleaned After Maintenance'), ('UNDER_MAINTENANCE', 'Under Maintenance'), ('UNDER_QUALIFICATION', 'Under Qualification'), ('BREAKDOWN', 'Breakdown'), ('NOT_IN_USE', 'Not in Use')], default='AVAILABLE', max_length=30),
        ),
    ]
