import os

from django.conf import settings

from django.template.loader import render_to_string

from weasyprint import HTML

from decimal import Decimal


class InvoiceGenerator:

    @staticmethod
    def generate_pdf(invoice):

        # 1. Prepare Paths

        logo_path = os.path.join(
            settings.BASE_DIR, "static", "assets", "companyLogo.jpg"
        )

        # 2. Re-calculate totals based on Moroccan Template Logic

        items = invoice.invoice_items.all()

        subtotal = sum(i.subtotal for i in items)

        # Deduction of 10% (Retention) as per template

        retention_rate = Decimal("10.0")

        discount_amount = subtotal * (retention_rate / Decimal("100"))

        # HT After Deduction [cite: 18, 27]

        total_ht = subtotal - discount_amount

        # TVA 20% on the remaining HT [cite: 19, 28]

        tax_rate = Decimal("20.0")

        tax_amount = total_ht * (tax_rate / Decimal("100"))

        # Final TTC [cite: 20, 29]

        total_ttc = total_ht + tax_amount

        # Update Invoice Instance

        invoice.subtotal = subtotal

        invoice.discount_percentage = retention_rate

        invoice.discount_amount = discount_amount

        invoice.total_ht = total_ht

        invoice.tax_rate = tax_rate

        invoice.tax_amount = tax_amount

        invoice.total_ttc = total_ttc

        invoice.save()

        # 3. Render HTML

        context = {
            "invoice": invoice,
            "company": invoice.created_by.company,
            "logo_path": logo_path,
        }

        html_string = render_to_string("pdf/invoice_template.html", context)

        # 4. Generate PDF

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
        """
        Calculates totals based on the Moroccan template logic.
        Used by the Celery task to ensure data integrity before PDF generation.
        """
        items = invoice.invoice_items.all()
        subtotal = sum(i.quantity * i.unit_price for i in items)  # [cite: 8, 14, 25]

        # Moroccan 10% Retention (Réception provisoire)
        retention_rate = Decimal("10.0")
        discount_amount = subtotal * (retention_rate / Decimal("100"))

        # HT After Deduction [cite: 18, 27]
        total_ht = subtotal - discount_amount

        # TVA 20% on the remaining HT [cite: 19, 28]
        tax_rate = Decimal("20.0")
        tax_amount = total_ht * (tax_rate / Decimal("100"))

        # Final TTC [cite: 20, 29]
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
