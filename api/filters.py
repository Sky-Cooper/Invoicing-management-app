import django_filters
from .models import Expense

class ExpenseFilter(django_filters.FilterSet):

    chantier = django_filters.NumberFilter(field_name="chantier_id")
    created_by = django_filters.NumberFilter(field_name="created_by_id")

 
    expense_date = django_filters.DateFilter(field_name="expense_date")
    expense_date_after = django_filters.DateFilter(
        field_name="expense_date", lookup_expr="gte"
    )
    expense_date_before = django_filters.DateFilter(
        field_name="expense_date", lookup_expr="lte"
    )

    class Meta:
        model = Expense
        fields = [
            "chantier",
            "created_by",
            "expense_date",
            "expense_date_after",
            "expense_date_before",
        ]
