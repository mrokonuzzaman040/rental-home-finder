"""Views for the Hotel (Rent/Booking) module."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import role_required
from .forms import BookingForm, HotelForm, RoomForm
from .models import Booking, Hotel, Profile, Room


def has_availability(room, check_in, check_out) -> bool:
    overlapping = Booking.objects.filter(
        room=room, check_in__lt=check_out, check_out__gt=check_in
    ).exclude(status=Booking.Status.CANCELLED)
    return overlapping.count() < room.total_rooms


def hotel_list(request):
    queryset = Hotel.objects.filter(is_published=True).order_by("-list_date")
    city = request.GET.get("city")
    if city:
        queryset = queryset.filter(city__iexact=city)

    paginator = Paginator(queryset, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "listings/hotels.html", {"hotels": page_obj, "page_obj": page_obj})


def hotel_detail(request, hotel_id):
    hotel = get_object_or_404(Hotel, pk=hotel_id)
    rooms = hotel.rooms.filter(is_published=True)
    context = {"hotel": hotel, "rooms": rooms, "booking_form": BookingForm()}
    return render(request, "listings/hotel_detail.html", context)


@role_required(Profile.Role.HOTEL_MANAGER)
def add_hotel(request):
    if request.method == "POST":
        form = HotelForm(request.POST, request.FILES)
        if form.is_valid():
            hotel = form.save(commit=False)
            hotel.manager = request.user
            hotel.save()
            messages.success(request, "Hotel added. Now add some rooms.")
            return redirect("add_room", hotel_id=hotel.id)
    else:
        form = HotelForm()
    return render(request, "auth/add_hotel.html", {"form": form})


@login_required
def edit_hotel(request, hotel_id):
    hotel = get_object_or_404(Hotel, pk=hotel_id, manager=request.user)
    if request.method == "POST":
        form = HotelForm(request.POST, request.FILES, instance=hotel)
        if form.is_valid():
            form.save()
            messages.success(request, "Hotel updated.")
            return redirect("dashboard")
    else:
        form = HotelForm(instance=hotel)
    return render(request, "auth/edit_hotel.html", {"form": form, "hotel": hotel})


@login_required
def delete_hotel(request, hotel_id):
    hotel = get_object_or_404(Hotel, pk=hotel_id, manager=request.user)
    if request.method == "POST":
        hotel.delete()
        messages.success(request, "Hotel removed.")
        return redirect("dashboard")
    return render(request, "auth/delete_hotel_confirm.html", {"hotel": hotel})


@login_required
def add_room(request, hotel_id):
    hotel = get_object_or_404(Hotel, pk=hotel_id, manager=request.user)
    if request.method == "POST":
        form = RoomForm(request.POST, request.FILES)
        if form.is_valid():
            room = form.save(commit=False)
            room.hotel = hotel
            room.save()
            messages.success(request, "Room added.")
            return redirect("dashboard")
    else:
        form = RoomForm()
    return render(request, "auth/add_room.html", {"form": form, "hotel": hotel})


@login_required
def book_room(request, room_id):
    room = get_object_or_404(Room, pk=room_id, is_published=True)
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            check_in = form.cleaned_data["check_in"]
            check_out = form.cleaned_data["check_out"]
            if not has_availability(room, check_in, check_out):
                messages.error(request, "This room isn't available for those dates.")
            else:
                booking = form.save(commit=False)
                booking.room = room
                booking.user = request.user
                booking.save()
                messages.success(request, "Booking requested. Awaiting confirmation.")
                return redirect("hotel_detail", hotel_id=room.hotel_id)
        messages.error(request, "Please correct the errors below.")
    return redirect("hotel_detail", hotel_id=room.hotel_id)


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)
    if request.method == "POST":
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=["status"])
        messages.success(request, "Booking cancelled.")
    return redirect("dashboard")
