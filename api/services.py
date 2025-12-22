import os

from django.conf import settings

from django.template.loader import render_to_string

from weasyprint import HTML

from decimal import Decimal

from django.core.mail import send_mail

import os
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from email.mime.image import MIMEImage
from django.utils import timezone


class InvoiceGenerator:

    @staticmethod
    def generate_pdf(invoice):

        logo_path = os.path.join(
            settings.BASE_DIR, "static", "assets", "companyLogo.jpg"
        )

        items = invoice.invoice_items.all()

        subtotal = sum(i.subtotal for i in items)

        retention_rate = Decimal("10.0")

        discount_amount = subtotal * (retention_rate / Decimal("100"))

        total_ht = subtotal - discount_amount

        tax_rate = Decimal("20.0")

        tax_amount = total_ht * (tax_rate / Decimal("100"))

        total_ttc = total_ht + tax_amount

        invoice.subtotal = subtotal

        invoice.discount_percentage = retention_rate

        invoice.discount_amount = discount_amount

        invoice.total_ht = total_ht

        invoice.tax_rate = tax_rate

        invoice.tax_amount = tax_amount

        invoice.total_ttc = total_ttc

        invoice.save()

        context = {
            "invoice": invoice,
            "company": invoice.created_by.company,
            "logo_path": logo_path,
        }

        html_string = render_to_string("pdf/invoice_template.html", context)

        pdf_name = f"invoice_{invoice.invoice_number.replace('/', '-')}.pdf"

        pdf_dir = os.path.join(settings.MEDIA_ROOT, "invoices")

        if not os.path.exists(pdf_dir):

            os.makedirs(pdf_dir)

        pdf_path = os.path.join(pdf_dir, pdf_name)

        HTML(string=html_string).write_pdf(pdf_path)

        return f"{settings.MEDIA_URL}invoices/{pdf_name}"


class InvoiceCalculator:
    @staticmethod
    def recalculate(invoice):
        items = invoice.invoice_items.all()

        subtotal = sum(i.subtotal for i in items)
        tax = sum(i.tax_amount for i in items)

        discount = subtotal * (invoice.discount_percentage / 100)
        total = subtotal - discount + tax

        invoice.subtotal = subtotal
        invoice.discount_amount = discount
        invoice.tax_amount = tax
        invoice.total_ttc = total

        invoice.save(
            update_fields=["subtotal", "discount_amount", "tax_amount", "total_ttc"]
        )

    @staticmethod
    def get_totals(invoice):

        items = invoice.invoice_items.all()
        subtotal = sum(i.quantity * i.unit_price for i in items)

        retention_rate = Decimal("10.0")
        discount_amount = subtotal * (retention_rate / Decimal("100"))

        total_ht = subtotal - discount_amount

        tax_rate = Decimal("20.0")
        tax_amount = total_ht * (tax_rate / Decimal("100"))

        total_ttc = total_ht + tax_amount

        return {
            "subtotal": subtotal,
            "discount_percentage": retention_rate,
            "discount_amount": discount_amount,
            "total_ht": total_ht,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "total_ttc": total_ttc,
        }


class EmailSending:
    def __init__(self, invoice):
        self.invoice = invoice
        self.common_context = {
            "contact_name": self.invoice.client.contact_name,
            "client_company": self.invoice.client.company_name,
            "invoice_number": self.invoice.invoice_number,
            "total_ttc": "{:,.2f}".format(self.invoice.total_ttc),
            "due_date": (
                self.invoice.due_date.strftime("%d/%m/%Y")
                if self.invoice.due_date
                else "N/A"
            ),
            "current_year": timezone.now().year,
            "payment_url": f"https://tourtra-app.com/invoices/{self.invoice.id}/",
        }

    def _prepare_email(self, subject, template_name, context_update):
        context = {**self.common_context, **context_update}
        from_email = settings.EMAIL_HOST_USER
        to_email = self.invoice.client.email

        if not to_email:
            return None

        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)
        email = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        email.attach_alternative(html_content, "text/html")
        email.mixed_subtype = "related"

        logo_path = os.path.join(
            settings.BASE_DIR, "static", "assets", "companyLogo.jpg"
        )
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                logo = MIMEImage(f.read())
                logo.add_header("Content-ID", "<logo>")
                logo.add_header(
                    "Content-Disposition", "inline", filename="companyLogo.jpg"
                )
                email.attach(logo)

        return email

    def send_email_reminder(self, days_left=None):
        subject = f"Reminder: Invoice #{self.invoice.invoice_number} is due soon"
        if days_left:
            subject = f"Action Required: {days_left} days until Invoice #{self.invoice.invoice_number} is due"

        email = self._prepare_email(
            subject, "invoice_reminder.html", {"days_left": days_left}
        )
        if email:
            email.send()

    def send_thanking_email(self):
        subject = f"Receipt & Thank You: Invoice #{self.invoice.invoice_number} Paid"
        email = self._prepare_email(subject, "thanking_invoice.html", {})
        if email:
            email.send()

    def send_pre_due_reminder(self, days_left):

        subject = f"Friendly Reminder: Invoice #{self.invoice.invoice_number} is due in {days_left} days"

        context_update = {
            "is_overdue": False,
            "days_left": days_left,
            "message_title": "Upcoming Payment Reminder",
        }

        email = self._prepare_email(subject, "invoice_reminder.html", context_update)
        if email:
            email.send()
            print(
                f"Pre-due reminder sent for invoice {self.invoice.invoice_number} ({days_left} days remaining)"
            )
