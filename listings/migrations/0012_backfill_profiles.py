from django.db import migrations


def backfill_profiles(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("listings", "Profile")
    missing = User.objects.filter(profile__isnull=True)
    Profile.objects.bulk_create(
        [Profile(user=user, role="user") for user in missing]
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0011_listing_address_verified_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_profiles, noop_reverse),
    ]
