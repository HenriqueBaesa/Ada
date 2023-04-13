# Generated by Django 4.1.7 on 2023-04-11 15:38

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("attribution", "0001_initial"),
        ("admin", "0003_logentry_add_action_flag_choices"),
        ("courses", "0004_rename_instructor_course_teacher"),
        ("professors", "0003_alter_professors_is_staff"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Professors",
            new_name="Professor",
        ),
    ]
