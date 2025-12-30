from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Invoice, Payment, Expense, Client, Attendance, InvoiceStatus
from django.db.models import Sum

def clear_company_analytics(company_id):
 
    if not company_id:
        return

    keys_to_clear = [
        f"analytics:kpi:{company_id}",    
        f"analytics:rg:{company_id}",   
        f"analytics:eb:{company_id}",     
        f"analytics:cp:{company_id}",    
        f"analytics:cc:{company_id}",    
        f"analytics:ts:{company_id}",     
        f"analytics:ab:{company_id}",     
        f"analytics:cd:{company_id}",    
        f"analytics:li:{company_id}",     
        f"analytics:pe:{company_id}",     
        f"analytics:tf:{company_id}",     
    ]
    
    cache.delete_many(keys_to_clear)
    print(f"--- [CACHE INVALIDATED] All Analytics for Company {company_id} ---")

@receiver([post_save, post_delete], sender=Invoice)
def invalidate_invoice_cache(sender, instance, **kwargs):
    if instance.created_by and instance.created_by.company:
        clear_company_analytics(instance.created_by.company.id)

@receiver([post_save, post_delete], sender=Payment)
def invalidate_payment_cache(sender, instance, **kwargs):
    if instance.invoice.created_by and instance.invoice.created_by.company:
        clear_company_analytics(instance.invoice.created_by.company.id)

@receiver([post_save, post_delete], sender=Expense)
def invalidate_expense_cache(sender, instance, **kwargs):
    if instance.chantier.department and instance.chantier.department.company:
        clear_company_analytics(instance.chantier.department.company.id)

@receiver([post_save, post_delete], sender=Client)
def invalidate_client_cache(sender, instance, **kwargs):
    if instance.company:
        clear_company_analytics(instance.company.id)

@receiver([post_save, post_delete], sender=Attendance)
def invalidate_attendance_cache(sender, instance, **kwargs):
   
    if instance.chantier.department and instance.chantier.department.company:
        clear_company_analytics(instance.chantier.department.company.id)



@receiver([post_save, post_delete], sender=Payment)
def update_invoice_balance(sender, instance, **kwargs):

    invoice = instance.invoice
    
    total_paid = invoice.payments.aggregate(total=Sum('amount'))['total'] or 0
    
    invoice.remaining_balance = max(invoice.total_ttc - total_paid, 0)
    
   
    if invoice.remaining_balance == 0:
        invoice.status = InvoiceStatus.PAID
    elif invoice.remaining_balance < invoice.total_ttc:
        invoice.status = InvoiceStatus.PARTIALLY_PAID
    elif invoice.remaining_balance == invoice.total_ttc:

        if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.PARTIALLY_PAID]:
            invoice.status = InvoiceStatus.COMPLETED 


    invoice.save(update_fields=['remaining_balance', 'status'])