from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Listing, Profile


class RegistrationTests(TestCase):
    def test_register_requires_email_and_saves_it(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password1": "Secure!",
                "password2": "Secure!",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        user = User.objects.get(username="newuser")
        self.assertEqual(user.email, "newuser@example.com")

    def test_register_rejects_password_without_required_mix(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "weakuser",
                "email": "weakuser@example.com",
                "password1": "abcdef",
                "password2": "abcdef",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="weakuser").exists())
        self.assertContains(response, "uppercase")
        self.assertContains(response, "symbol")


class ListingFilterTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="Owner!1")
        Profile.objects.create(user=self.owner, role=Profile.Role.FLAT_OWNER)

    def _listing(self, title, tenant_type):
        return Listing.objects.create(
            title=title,
            description=f"{title} description",
            address="Road 1",
            city="Dhaka",
            price=12000,
            bedrooms=2,
            bathrooms=1,
            square_feet=700,
            garage=0,
            status="available",
            tenant_type=tenant_type,
            owner=self.owner,
            is_published=True,
        )

    def test_girl_tenant_filter_includes_girl_and_any(self):
        girl_listing = self._listing("Girl-ready flat", "girl")
        any_listing = self._listing("Open tenant flat", "any")
        family_listing = self._listing("Family flat", "family")

        response = self.client.get(reverse("search"), {"tenant": "girl"})

        listings = list(response.context["listings"].object_list)
        self.assertIn(girl_listing, listings)
        self.assertIn(any_listing, listings)
        self.assertNotIn(family_listing, listings)

    def test_add_listing_publishes_to_public_search(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("add_listing"),
            {
                "title": "New public flat",
                "description": "A clean listing for public browsing.",
                "city": "Dhaka",
                "address": "Road 2",
                "tenant_type": "girl",
                "price": "15000",
                "bedrooms": "2",
                "bathrooms": "1",
                "square_feet": "850",
                "garage": "0",
                "status": "available",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        listing = Listing.objects.get(title="New public flat")
        self.assertTrue(listing.is_published)

        search = self.client.get(reverse("search"), {"city": "Dhaka"})
        self.assertContains(search, "New public flat")


class AdminListingTests(TestCase):
    def test_listing_changelist_renders_when_listing_has_no_image(self):
        staff = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="Admin!1",
        )
        Listing.objects.create(
            title="No image flat",
            description="Admin should render this row.",
            address="Road 3",
            city="Dhaka",
            price=10000,
            bedrooms=1,
            bathrooms=1,
            square_feet=500,
            garage=0,
            status="available",
            tenant_type="any",
            owner=staff,
            is_published=True,
        )

        self.client.force_login(staff)
        response = self.client.get(reverse("admin:listings_listing_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No image flat")
