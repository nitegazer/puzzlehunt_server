# Generated by Django 2.2 on 2020-02-06 02:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('huntserver', '0042_auto_20200204_2304'),
    ]

    operations = [
        migrations.AddField(
            model_name='puzzle',
            name='doesnt_count',
            field=models.BooleanField(default=False, help_text='Should this puzzle not count towards scoring?'),
        ),
    ]