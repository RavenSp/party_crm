from django.core.mail import EmailMultiAlternatives
# from django.template.loader import get_template


def send_report(email: str, report_year: int, report_file) -> None:
    subject = f"Отчёт о раздачах газет за {report_year} год"
    message = f"Добрый день!\n Вы запросили отчёт о раздаче газет за { report_year } год.\n\nРабочая партия России. Москвоское отделение."
    recipient_list = [email]
    mail = EmailMultiAlternatives(
        subject=subject,
        body=message,
        to=recipient_list
    )

    mail.attach(filename=f"Отчёт о раздачах за {report_year} год.xlsx", content=report_file.read(),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    # mail.attach_alternative(content=get_template('press/report_email.html').render({
    #     'year': report_year
    # }), mimetype='text/html')
    mail.send()


