from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from press.services import report, mail
import datetime
class Command(BaseCommand):
    help = "Отправка отчёта о раздачах на REPORT_MONTH_EMAIL"

    def handle(self, *args, **options):
        recipient = settings.REPORT_MONTH_EMAIL
        if recipient is None:
            raise CommandError("Не указан REPORT_MONTH_EMAIL в settings.py")

        report_file = report.generate_report()
        mail.send_report(email=recipient, report_file=report_file, report_year=report._report_month().year)
        self.stdout.write(self.style.SUCCESS("Email с отчётом успешно отправлен"))
