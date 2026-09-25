"""Views for the Property (Buy & Sell) module."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import role_required
from .forms import PropertyListingForm
from .models import Profile, PropertyImage, PropertyInterest, PropertyListing


def property_list(request):
    queryset = PropertyListing.objects.filter(is_published=True).order_by("-list_date")

    city = request.GET.get("city")
    if city:
        queryset = queryset.filter(city__iexact=city)

    property_kind = request.GET.get("property_kind")
    if property_kind:
        queryset = queryset.filter(property_kind=property_kind)

    paginator = Paginator(queryset, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "listings": page_obj,
        "page_obj": page_obj,
        "property_kinds": PropertyListing.PropertyKind.choices,
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "listings/_property_items.html", context)
    return render(request, "listings/properties.html", context)


def property_detail(request, property_id):
    property_listing = get_object_or_404(PropertyListing, pk=property_id)
    property_listing.views_count += 1
    property_listing.save(update_fields=["views_count"])

    context = {"property_listing": property_listing}
    return render(request, "listings/property_detail.html", context)


@login_required
def property_interest(request, property_id):
    property_listing = get_object_or_404(PropertyListing, pk=property_id)
    if request.method == "POST":
        PropertyInterest.objects.create(
            property_listing=property_listing,
            user=request.user,
            name=request.POST.get("name", "").strip() or request.user.username,
            email=request.POST.get("email", "").strip() or request.user.email,
            phone=request.POST.get("phone", "").strip(),
            message=request.POST.get("message", "").strip(),
            offered_price=request.POST.get("offered_price") or None,
        )
        messages.success(request, "Your interest has been sent to the owner.")
    return redirect("property_detail", property_id=property_id)


@role_required(Profile.Role.PROPERTY_OWNER)
def add_property(request):
    if request.method == "POST":
        form = PropertyListingForm(request.POST, request.FILES)
        files = request.FILES.getlist("images")
        if form.is_valid():
            property_listing = form.save(commit=False)
            property_listing.owner = request.user
            property_listing.save()
            for f in files:
                PropertyImage.objects.create(property_listing=property_listing, image=f)
            messages.success(request, "Property listed for sale.")
            return redirect("dashboard")
    else:
        form = PropertyListingForm()
    return render(request, "auth/add_property.html", {"form": form})


@login_required
def edit_property(request, property_id):
    property_listing = get_object_or_404(
        PropertyListing, pk=property_id, owner=request.user
    )
    if request.method == "POST":
        form = PropertyListingForm(
            request.POST, request.FILES, instance=property_listing
        )
        files = request.FILES.getlist("images")
        if form.is_valid():
            property_listing = form.save()
            for f in files:
                PropertyImage.objects.create(property_listing=property_listing, image=f)
            messages.success(request, "Listing updated.")
            return redirect("dashboard")
    else:
        form = PropertyListingForm(instance=property_listing)
    return render(
        request,
        "auth/edit_property.html",
        {"form": form, "property_listing": property_listing},
    )


@login_required
def delete_property(request, property_id):
    property_listing = get_object_or_404(
        PropertyListing, pk=property_id, owner=request.user
    )
    if request.method == "POST":
        property_listing.delete()
        messages.success(request, "Listing removed.")
        return redirect("dashboard")
    return render(
        request, "auth/delete_confirm.html", {"listing": property_listing}
    )
