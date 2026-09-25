from django.urls import path, re_path

from . import hotel_views, property_views, views

urlpatterns = [
    path("", views.index, name="listings"),
    path("search", views.search, name="search"),
    path("contact", views.contact, name="contact"),
    path(
        "listing/<int:listing_id>/report/",
        views.submit_complaint,
        name="submit_complaint",
    ),
    # Property (Buy & Sell)
    path("for-sale/", property_views.property_list, name="property_list"),
    path(
        "for-sale/<int:property_id>/",
        property_views.property_detail,
        name="property_detail",
    ),
    path(
        "for-sale/<int:property_id>/interest/",
        property_views.property_interest,
        name="property_interest",
    ),
    path("for-sale/add/", property_views.add_property, name="add_property"),
    path(
        "for-sale/edit/<int:property_id>/",
        property_views.edit_property,
        name="edit_property",
    ),
    path(
        "for-sale/delete/<int:property_id>/",
        property_views.delete_property,
        name="delete_property",
    ),
    # Hotel (Rent/Booking)
    path("hotels/", hotel_views.hotel_list, name="hotel_list"),
    path("hotel/<int:hotel_id>/", hotel_views.hotel_detail, name="hotel_detail"),
    path("hotel/add/", hotel_views.add_hotel, name="add_hotel"),
    path("hotel/edit/<int:hotel_id>/", hotel_views.edit_hotel, name="edit_hotel"),
    path("hotel/delete/<int:hotel_id>/", hotel_views.delete_hotel, name="delete_hotel"),
    path("hotel/<int:hotel_id>/room/add/", hotel_views.add_room, name="add_room"),
    path("room/<int:room_id>/book/", hotel_views.book_room, name="book_room"),
    path(
        "booking/<int:booking_id>/cancel/",
        hotel_views.cancel_booking,
        name="cancel_booking",
    ),
    # Listing detail - readable URL (must come before legacy numeric redirect)
    path("property/<int:listing_id>/", views.listing, name="listing"),
    # Management
    path("dashboard/", views.dashboard, name="dashboard"),
    path("rewards/", views.rewards_view, name="rewards"),
    path("listing/add/", views.add_listing, name="add_listing"),
    path("listing/edit/<int:listing_id>/", views.edit_listing, name="edit_listing"),
    path(
        "listing/delete/<int:listing_id>/", views.delete_listing, name="delete_listing"
    ),
    path("messages/", views.messages_view, name="messages"),
    path("profile/", views.profile_view, name="profile"),
    path("favorites/", views.favorites_view, name="favorites"),
    path("listing/<int:listing_id>/review/", views.add_review, name="add_review"),
    path(
        "listing/<int:listing_id>/favorite/",
        views.toggle_favorite,
        name="toggle_favorite",
    ),
    path(
        "listing/<int:listing_id>/compare/", views.add_to_compare, name="add_to_compare"
    ),
    path("compare/", views.compare_properties, name="compare_properties"),
    path("compare/clear/", views.clear_compare, name="clear_compare"),
    path(
        "api/generate-description/",
        views.generate_ai_description_api,
        name="api_generate_description",
    ),
    path("api/ai-chat/", views.ai_assistant_chat, name="api_ai_chat"),
    path(
        "api/preferences/",
        views.api_set_visitor_preferences,
        name="api_visitor_preferences",
    ),
    path(
        "api/resolve-location/", views.api_resolve_location, name="api_resolve_location"
    ),
    # Auth
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
]

# Old bare URLs like /104 → 301 redirect to /property/104/
urlpatterns += [
    re_path(r"^(?P<listing_id>[0-9]+)/?$", views.listing_legacy_redirect),
]
