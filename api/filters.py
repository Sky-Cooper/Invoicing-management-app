import django_filters
from .models import Expense

class ExpenseFilter(django_filters.FilterSet):
    chantier = django_filters.NumberFilter(field_name="chantier_id")
    created_by = django_filters.NumberFilter(field_name="created_by_id")

    class Meta:
        model = Expense
        fields = ["chantier", "created_by"]
