from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView
from restaurant.forms import ReservationForm
from restaurant.models import Reservation, Restaurant


def home(request):
   return render(request, "home.html")


class Contacts(TemplateView):
    """Контакты"""

    template_name = "restaurant/contacts.html"

    def post(self, request, *args, **kwargs):
        """Обработка POST-запроса ответа на обратную связь."""
        if request.method == "POST":
            name = request.POST.get("name")  # получаем имя
            # message = request.POST.get("message")  # получаем сообщение
            # Отправляем сообщение об успешной отправке
            messages.success(request, f"Спасибо, {name}! Ваше сообщение успешно отправлено.")
            return redirect("restaurant:contacts")
        return render(request, self.template_name)


class Feedback(TemplateView):
    """Обратная связь"""

    template_name = "restaurant/feedback.html"


class MainView(ListView):
    """Главная страница."""

    model = Restaurant
    template_name = "restaurant/main.html"


class AboutView(ListView):
    """О ресторане"""

    model = Restaurant
    template_name = "restaurant/about.html"


class ReservationListView(ListView):
    """Бронирование"""

    model = Reservation
    template_name = "restaurant/reservation_list.html"
    context_object_name = "restaurant"
    success_url = reverse_lazy("restaurant:reservation_list")
    form_class = ReservationForm

    def get_object(self, queryset=None):
        self.object = super().get_object(queryset)
        self.object.save()
        if self.request.user == self.object.owner:
            self.object.save()
            return self.object
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = ReservationForm()
        context["reservations"] = self.get_queryset()
        context["now"] = timezone.now()
        return context

    def post(self, request, *args, **kwargs):
        """POST-запрос"""
        form = self.form_class(request.POST)

        if form.is_valid():
            reservation = form.save(commit=False)

            # Проверка, на корректность даты
            if reservation.reserved_at and reservation.reserved_at < timezone.now():
                messages.error(
                    request,
                    "Дата бронирования не может быть в прошлом. Пожалуйста, выберите другое время.",
                )
                return self.get(request, *args, **kwargs)

            # Проверка интервала бронирования (60 минут после)
            reserved_at = reservation.reserved_at
            start_time = reserved_at
            end_time = start_time + timedelta(minutes=60)

            # Проверка, есть ли уже бронирования в этом интервале
            interval_restaurant = Reservation.objects.filter(reserved_at__range=(start_time, end_time)).exclude(
                id=reservation.id
            )

            if interval_restaurant.exists():
                messages.error(
                    request,
                    "К сожалению, на это время уже занято. Выберите другой стол или дату.",
                )
                return self.get(request, *args, **kwargs)  # Возврат на ту же страницу

            reservation.save()
            messages.success(request, "Ваше бронирование успешно зарегистрировано!")
            return redirect(self.success_url)  # Перенаправление на страницу с успешным бронированием

        # Сообщение об ошибке
        messages.error(
            request,
            "К сожалению, на это время уже занято. Выберите другой стол или дату",
        )
        return self.get(request, *args, **kwargs)  # Возврат на ту же страницу

    def get_queryset(self):
        now = timezone.now()

        # Время, до которого бронирования считаются "в процессе"
        in_progress_time = now - timedelta(minutes=60)

        return Reservation.objects.filter(
            reserved_at__gte=in_progress_time  # Бронирования, которые в процессе или будут
        ).order_by("table", "reserved_at")


class ReservationCreateView(CreateView):
    """Создание бронирования"""

    model = Reservation
    form_class = ReservationForm
    template_name = "restaurant/reservation_list.html"
    success_url = reverse_lazy("restaurant:reservation_list")


class ReservationUpdateView(UpdateView, LoginRequiredMixin):
    """Редактирование бронирования"""

    model = Reservation
    form_class = ReservationForm
    template_name = "restaurant/reservation_list.html"
    context_object_name = "restaurant"
    success_url = reverse_lazy("restaurant:personal_account")

    def get_object(self, queryset=None):
        reservation = super().get_object(queryset)
        if self.request.user != reservation.owner:
            raise PermissionDenied("Вы не можете редактировать это бронирование.")
        return reservation

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["from_personal_account"] = True
        return context

    def form_valid(self, form):
        reservation = form.save(commit=False)

        if reservation.reserved_at and reservation.reserved_at < timezone.now():
            messages.error(self.request, "Дата бронирования не может быть в прошлом.")
            return self.form_invalid(form)

        # Проверка интервала бронирования (60 минут после)
        reserved_at = reservation.reserved_at
        start_time = reserved_at
        end_time = start_time + timedelta(minutes=60)

        # Проверка, есть ли уже бронирования в этом интервале
        interval_reservations = Reservation.objects.filter(reserved_at__range=(start_time, end_time)).exclude(
            id=reservation.id
        )

        if interval_reservations.exists():
            messages.error(self.request, "К сожалению, на это время уже занято.")
            return self.form_invalid(form)

        reservation.save()
        messages.success(self.request, "Бронирование успешно обновлено!")
        return super().form_valid(form)


class ReservationDeleteView(DeleteView):
    """Удаление бронирования"""

    model = Reservation
    success_url = reverse_lazy("restaurant:personal_account")

    def get_object(self, queryset=None):
        self.object = super().get_object(queryset)
        if self.request.user == self.object.owner:
            self.object.save()
            return self.object
        raise PermissionDenied


class PersonalAccountListView(ListView):
    """Личный кабинет"""

    model = Reservation
    template_name = "restaurant/personal_account.html"

    def get_queryset(self):

        # Фильтруем по владельцу и сортируем по дате и столику
        queryset = Reservation.objects.filter(owner=self.request.user).order_by("reserved_at", "table")
        return queryset


class Services(TemplateView):
    """Услуги"""

    template_name = "restaurant/services.html"


class Mission(TemplateView):
    """Миссия и ценности"""

    template_name = "restaurant/mission.html"


class Team(TemplateView):
    """Команда"""

    template_name = "restaurant/team.html"


class History(TemplateView):
    """История"""

    template_name = "restaurant/history.html"
