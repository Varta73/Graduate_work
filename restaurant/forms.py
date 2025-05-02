from django import forms
from django.forms import ModelForm

from restaurant.models import Reservation, Restaurant, Table


class StyleFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"


class RestaurantForm(StyleFormMixin, ModelForm):
    """Форма создания ресторана."""

    class Meta:
        model = Restaurant
        fields = "__all__"


class ReservationForm(ModelForm):
    """Форма бронирования столика."""

    class Meta:
        model = Reservation
        fields = ["owner", "table", "reserved_at", "customer_name", "customer_contact"]
        widgets = {
            "reserved_at": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Выберите дату и время",
                    "type": "datetime-local",  # для выбора даты и времени
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super(ReservationForm, self).__init__(*args, **kwargs)
        self.fields["table"].queryset = Table.objects.filter(is_available=True)
        self.fields["table"].widget.attrs.update({"class": "form-control"})
        self.fields["customer_name"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "На кого бронируем столик?",
            }
        )
        self.fields["customer_contact"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Укажите контактный номер телефона для связи",
            }
        )
        self.fields["owner"].widget.attrs.update({"class": "form-control"})
