import os
from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML
from num2words import num2words
from decimal import Decimal
from .models import Invoice, InvoiceStatus
from .services import InvoiceCalculator
from django.utils import timezone
from .services import EmailSending
from django.core.cache import cache
from datetime import timedelta


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
)
def generate_invoice_pdf_task(self, invoice_id):
    try:

        invoice = Invoice.objects.select_related("client", "created_by__company").get(
            id=invoice_id
        )

        totals = InvoiceCalculator.get_totals(invoice)
        invoice.subtotal = totals["subtotal"]
        invoice.discount_percentage = totals["discount_percentage"]
        invoice.discount_amount = totals["discount_amount"]
        invoice.total_ht = totals["total_ht"]
        invoice.tax_rate = totals["tax_rate"]
        invoice.tax_amount = totals["tax_amount"]
        invoice.total_ttc = totals["total_ttc"]

        ttc_value = invoice.total_ttc
        dirhams = int(ttc_value)
        centimes = int(round((ttc_value - dirhams) * 100))
        dirhams_words = num2words(dirhams, lang="fr")

        if centimes > 0:
            legal_text = f"{dirhams_words} Dirhams Et {centimes} Cts TTC"
        else:
            legal_text = f"{dirhams_words} Dirhams TTC"

        invoice.amount_in_words = legal_text.upper()
        invoice.save()

        logo_path = os.path.join(
            settings.BASE_DIR, "static", "assets", "companyLogo.jpg"
        )

        context = {
            "invoice": invoice,
            "company": invoice.created_by.company,
            "logo_path": logo_path,
        }

        html_string = render_to_string("pdf/invoice_pdf.html", context)

        pdf_filename = f"facture_{invoice.invoice_number.replace('/', '_')}.pdf"
        pdf_directory = os.path.join(settings.MEDIA_ROOT, "invoices")

        if not os.path.exists(pdf_directory):
            os.makedirs(pdf_directory, exist_ok=True)

        pdf_path = os.path.join(pdf_directory, pdf_filename)

        HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf(pdf_path)

   

        return f"Invoice {invoice.invoice_number} successfully generated."

    except Invoice.DoesNotExist:
        return f"Error: Invoice ID {invoice_id} not found."
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(
    blank=True,
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_kwargs={"max_retries": 3},
)
def send_invoice_reminders():

    today = timezone.now().date()

    print("checking for unpaid invoices ...")
    unpaid_invoices = Invoice.objects.filter(
        due_date__lte=today, status=InvoiceStatus.COMPLETED
    )

    print(f"unpaid invoices found {unpaid_invoices}")

    for invoice in unpaid_invoices:

        cache_key = f"reminder_sent_{invoice.id}_{timezone.now().date()}"

        if not cache.get(cache_key):
            email_sending = EmailSending(invoice)
            email_sending.send_email_reminder()

            cache.set(cache_key, True, 86400)
        else:
            print(f"Skipping invoice {invoice.id}: Reminder already sent today.")

    return f"{unpaid_invoices.count()} reminders sent"


@shared_task(autoretry_for=(Exception,), retry_backoff=60)
def send_invoice_reminders_pre_due():

    today = timezone.now().date()

    milestones = [7, 5, 3, 1]
    target_dates = [today + timedelta(days=m) for m in milestones]

    invoices = Invoice.objects.filter(
        due_date__in=target_dates, status=InvoiceStatus.COMPLETED
    )

    for invoice in invoices:
        days_left = (invoice.due_date - today).days
        email_sending = EmailSending(invoice)
        email_sending.send_pre_due_reminder(days_left)

    return f"Sent {invoices.count()} pre-due reminders."


@shared_task
def send_thanking_invoice_task(invoice_id):
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        email_sending = EmailSending(invoice)
        email_sending.send_thanking_email()
    except Invoice.DoesNotExist:
        print(f"Invoice {invoice_id} not found for thanking email.")
