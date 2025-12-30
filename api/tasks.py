import os
from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML
from num2words import num2words
from decimal import Decimal
from .models import Invoice, InvoiceStatus, Quote, QuoteItem, POItem,  PurchaseOrder , QuoteStatus, POStatus
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
        # Fetch invoice (Data is already calculated by the View)
        invoice = Invoice.objects.select_related("client", "created_by__company").get(
            id=invoice_id
        )

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

        return f"Invoice {invoice.invoice_number} PDF successfully generated."

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


@shared_task
def generate_po_pdf_task(po_id):
    try:
        po = PurchaseOrder.objects.select_related("client", "created_by__company").get(id=po_id)
        logo_path = os.path.join(settings.BASE_DIR, "static", "assets", "companyLogo.jpg")
        
        context = {
            "invoice": po, 
            "company": po.created_by.company,
            "logo_path": logo_path,
        }
        
        html_string = render_to_string("pdf/purchase_order_pdf.html", context)
        
        filename = f"bc_{po.po_number.replace('/', '_')}.pdf"
        directory = os.path.join(settings.MEDIA_ROOT, "purchase_orders")
        if not os.path.exists(directory): os.makedirs(directory, exist_ok=True)
        
        HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf(os.path.join(directory, filename))
        return f"PO {po.po_number} PDF Generated"
    except Exception as e:
        return f"Error: {str(e)}"





@shared_task
def generate_quote_pdf_task(quote_id):
    try:
        quote = Quote.objects.select_related("client", "created_by__company").get(id=quote_id)
        logo_path = os.path.join(settings.BASE_DIR, "static", "assets", "companyLogo.jpg")
        
        # Note: We pass 'invoice' key to reuse the same variables in template easier
        context = {
            "invoice": quote, 
            "company": quote.created_by.company,
            "logo_path": logo_path,
        }
        
        html_string = render_to_string("pdf/quote_pdf.html", context)
        
        filename = f"devis_{quote.quote_number.replace('/', '_')}.pdf"
        directory = os.path.join(settings.MEDIA_ROOT, "quotes")
        if not os.path.exists(directory): os.makedirs(directory, exist_ok=True)
        
        HTML(string=html_string, base_url=settings.BASE_DIR).write_pdf(os.path.join(directory, filename))
        return f"Quote {quote.quote_number} PDF Generated"
    except Exception as e:
        return f"Error: {str(e)}"