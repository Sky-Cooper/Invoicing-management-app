# TODO: for production use the commented one
# from django.core.management.base import BaseCommand
# from django_celery_beat.models import PeriodicTask, CrontabSchedule

# class Command(BaseCommand):
#     help = "Create default Celery Beat periodic tasks for Invoice Management"

#     def handle(self, *args, **kwargs):
#         # 1. Define a Daily Schedule (e.g., 09:00 AM every day)
#         # It is better to send reminders in the morning.
#         daily_morning_schedule, _ = CrontabSchedule.objects.get_or_create(
#             minute="0",
#             hour="9",
#             day_of_week="*",
#             day_of_month="*",
#             month_of_year="*",
#         )

#         # 2. Task: Standard / Pre-Due Reminders
#         # This covers your send_invoice_reminders task
#         task1, created1 = PeriodicTask.objects.get_or_create(
#             crontab=daily_morning_schedule,
#             name="Invoice Daily Reminders",
#             task="api.tasks.send_invoice_reminders",
#         )

#         # 3. Task: Post-Due (Overdue) Reminders
#         # This covers the 1, 3, 7, 14 days late logic
#         task2, created2 = PeriodicTask.objects.get_or_create(
#             crontab=daily_morning_schedule,
#             name="Invoice Overdue Reminders",
#             task="api.tasks.send_invoice_reminders_pre_due",
#         )

#         # Output results to console
#         if created1 or created2:
#             self.stdout.write(self.style.SUCCESS("Successfully created/verified periodic tasks."))
#         else:
#             self.stdout.write(self.style.WARNING("Periodic tasks already exist."))

#         self.stdout.write(f"Tasks scheduled for 09:00 daily.")


from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule


class Command(BaseCommand):
    help = "Create default Celery Beat periodic tasks for TESTING (Runs every 5 mins)"

    def handle(self, *args, **kwargs):

        testing_schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="*/5",
            hour="*",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )

        PeriodicTask.objects.update_or_create(
            name="Invoice General Reminders - TEST",
            defaults={
                "crontab": testing_schedule,
                "task": "api.tasks.send_invoice_reminders",
            },
        )

        PeriodicTask.objects.update_or_create(
            name="Invoice Pre-Due Milestones - TEST",
            defaults={
                "crontab": testing_schedule,
                "task": "api.tasks.send_invoice_reminders_pre_due",
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Testing tasks (General & Pre-Due) are active every 5 minutes."
            )
        )
