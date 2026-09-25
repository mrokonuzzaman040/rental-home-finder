# Rental Home Finder 🏠

Rental Home Finder (HouseFinderBD) is a modern, AI-powered real estate application built with Django. It connects landlords, property owners, and hotel managers with tenants and buyers, offering rental listings, property sales, hotel booking, trust/verification scoring, smart matching, and gamified rewards to make renting and buying property smoother in Bangladesh.

## Core Features

### 👤 User Roles
Every account picks a role at registration, which gates what they can list:
*   **User** - browse, rent, buy, and book.
*   **Flat Owner** - list rental properties.
*   **Property Owner** - list properties for sale.
*   **Hotel Manager** - list hotels and rooms for booking.
*   Admins (`is_staff`) can do everything, regardless of role.

### 🏢 Rental Property Management
*   **Detailed Listings:** Flat owners can post listings with comprehensive details, including bedrooms, bathrooms, square footage, amenities (AC, heating, furnished status), contact phone, and tenant preferences (Bachelor, Family, Girl, Any) plus a free-text tenant-fit note (e.g. "Suitable for female students... Not allowed: bachelor male group").
*   **Media Gallery:** Support for a main image and multiple gallery images per listing.
*   **Listing Offers:** Built-in promotion engine to offer time-bound rent discounts and bonus inquiry reward points.

### ✅ Verified Listing Trust Score
Each listing has a rule-based, admin-verifiable trust score out of 100 (`listings/trust_score.py`), built from six weighted checks (phone, address, photos, rent, availability, private document) plus a bonus for having no unresolved complaints. Shown as a badge on cards and the detail page; recomputes automatically whenever the listing or a related complaint is saved.

### 🎯 Smart Match Score
A transparent, rule-based ranking engine (`listings/matching.py`) scores listings against a renter's budget, preferred location, tenant type, verification level, and feature priorities - each with a visible point breakdown so results are explainable, not a black box. Powers the home page "Smart Match" search and the "Best match" sort option on the search page.

### 📊 Rent Fairness Estimator
Compares a listing's rent against similar listings in the same area/bedroom count (`listings/fairness.py`), labeling it a great deal, fair price, or high rent - clearly flagged as a prototype estimate, not an official rent index.

### 🚩 Duplicate & Fake Listing Detection
Rule-based checks (`listings/duplicates.py`) flag suspicious listings for admin review: phone numbers reused across many listings, the same address posted at different rents, rent far below the area average, near-duplicate title/description text, and repeated images. Runs automatically when a listing is added/edited, and can be re-run anytime via the admin action or `python manage.py rescan_duplicates`.

### 🛡️ Admin Verification & Complaint Handling
Visitors can report a listing (fake, fraud, wrong info, offensive, other) via a report modal on the listing page - no login required. Admins review and resolve reports from the Django admin, which feeds directly back into the listing's trust score.

### 🏠 Property (Buy & Sell)
A separate module for property owners to list properties for sale (apartment, land, house, commercial) with their own gallery, status (available/under negotiation/sold), and buy-interest inquiries from prospective buyers.

### 🏨 Hotel (Rent/Booking)
Hotel managers list hotels and rooms; users book rooms for a date range with automatic overlap-based availability checking, and can cancel their own bookings from the dashboard.

### 👥 User Engagement
*   **Inquiries & Contact:** Prospective tenants can send inquiries directly to landlords regarding specific properties.
*   **Favorites:** Users can save their favorite listings for quick access later.
*   **Reviews & Ratings:** A transparent review system where tenants can rate and leave feedback on listings.

### 🎁 Gamified Rewards System
The platform features a unique loyalty system to encourage user engagement:
*   **Points Ledger:** Users earn points for actions such as signing up, sending inquiries, posting reviews, adding favorites, and publishing listings.
*   **Tier System:** Users progress through Bronze, Silver, and Gold tiers based on their lifetime earned points.
*   **Promotional Bonuses:** Landlords can attach bonus points to specific listings to incentivize inquiries.

### 🤖 AI-Powered Insights (Gemini API)
Rental Home Finder leverages Google's Gemini 2.5 Flash model to provide intelligent features for both landlords and tenants:
*   **Rental Assistant Chat:** A conversational AI assistant that provides neutral, practical advice on renting, leases, and neighborhoods.
*   **Neighborhood Insider Reports:** Generates a "Creative Insider Report" detailing the vibe, commute truths, and local secrets of a specific address.
*   **Living Cost Estimator:** Analyzes the city and rent price to estimate monthly living costs (utilities, internet, groceries, transport).
*   **Automated Property Descriptions:** Helps landlords generate professional, luxury-toned property descriptions based on listing details.

## Technology Stack

*   **Backend Framework:** Django (Python)
*   **Database:** SQLite (default for development)
*   **AI Integration:** `google-generativeai` (Gemini API)
*   **Styling & UI:** Django Crispy Forms with Bootstrap 5
*   **Admin Panel:** Django Jazzmin for a modern, responsive admin dashboard

## Project Structure

The project is structured around standard Django conventions:
*   **`config/`**: Core Django project configuration (`settings.py`, `urls.py`).
*   **`listings/`**: The main application containing the models, views, forms, and business logic.
    *   `models.py`: Defines the database schema (Listing, Profile, Complaint, ListingFlag, PropertyListing, Hotel, Room, Booking, Inquiry, Favorite, Review, RewardWallet, etc.).
    *   `roles.py` / `decorators.py`: User role helpers and the `@role_required` view decorator.
    *   `trust_score.py`: Verified Listing Trust Score calculation.
    *   `matching.py`: Smart Match Score ranking engine.
    *   `fairness.py`: Rent Fairness Estimator.
    *   `duplicates.py`: Rule-based duplicate/fake listing detection.
    *   `property_views.py` / `hotel_views.py`: Views for the Buy & Sell and Hotel booking modules.
    *   `admin.py`, `admin_moderation.py`, `admin_property.py`, `admin_hotel.py`: Django admin configuration, including the moderation queue and the admin dashboard.
    *   `ai_utils.py`: Contains the logic for interacting with the Gemini API.
    *   `rewards.py`: Logic for granting points and managing user tiers.
    *   `management/commands/`: `rescan_duplicates` and `backfill_image_hashes` management commands.
*   **`seed.py`**: A utility script to quickly populate the database with realistic demo listings (including sample data to exercise duplicate detection).

---
## Setup Instructions

Follow these instructions to set up and run the application on your local machine.

## Prerequisites
- Python 3.8+ installed on your system.
- Basic knowledge of using the terminal/command prompt.

## Setup Steps

### 1. Create a Virtual Environment
It's highly recommended to use a virtual environment to manage your project's dependencies.

Open your terminal, navigate to the project directory, and run:
```bash
python -m venv venv
```

### 2. Activate the Virtual Environment
Activate the virtual environment you just created.

- **On macOS/Linux:**
  ```bash
  source venv/bin/activate
  ```
- **On Windows:**
  ```bash
  venv\Scripts\activate
  ```

### 3. Install Dependencies
Install the required Python packages from the `requirements.txt` file:
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
The application uses environment variables for configuration.

1. Copy the `.env.example` file to a new file named `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open the `.env` file and set the required variables. For a local development setup, the defaults are usually fine, but ensure `DEBUG=True`. If you plan to use AI features, add your Gemini API key to `GEMINI_API_KEY`.

### 5. Apply Database Migrations
Set up the database structure by running Django migrations. The application uses SQLite by default (`db.sqlite3`).
```bash
python manage.py migrate
```

### 6. Populate Demo Data (Optional)
You can populate the database with dummy listings to test the application. A script is provided to do this automatically.

To add 100 demo listings, run:
```bash
python seed.py
```
*Note: This script will replace existing listings. If you want to append to existing listings instead, use `python seed.py --append`. The script also creates a default admin user with username: `admin` and password: `admin123`.*

After seeding, run the duplicate scan so the admin moderation queue has demo data to review:
```bash
python manage.py rescan_duplicates
```

### 7. Create a Superuser (Optional)
If you didn't run the `seed.py` script, or if you want to create a specific admin user, you can create one manually:
```bash
python manage.py createsuperuser
```
Follow the prompts to set a username, email, and password.

### 8. Run the Development Server
Start the Django development server:
```bash
python manage.py runserver
```

The application will now be running. You can access it in your web browser at:
`http://127.0.0.1:8000/`

You can access the admin panel at:
`http://127.0.0.1:8000/admin/` (or whatever `ADMIN_URL_PATH` you set in `.env`)
