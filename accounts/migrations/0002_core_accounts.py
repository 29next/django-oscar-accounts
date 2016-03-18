# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from accounts import names


def create_core_accounts(apps, schema_editor):
    # Please use `manage.py oscar_accounts_init`
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_core_accounts)
    ]
