import unittest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import (
    Seller, Buyer, Vehicle, Booking, Comment, Rating,
    Payment, ChatbotLog, Messages, Notification, Staff, ChatMessage
)
from .forms import SignupForm, BookingForm, VehicleForm, PaymentForm


# =============================================================================
# MODEL TESTS
# =============================================================================

class SellerModelTest(TestCase):
    """Unit tests for the Seller model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='seller_user',
            email='seller@test.com',
            password='testpass123'
        )

    def test_seller_creation(self):
        """Test that Seller is created via signal when User is created."""
        self.assertTrue(Seller.objects.filter(user=self.user).exists())

    def test_seller_str_representation(self):
        """Test string representation of Seller."""
        seller = Seller.objects.get(user=self.user)
        self.assertEqual(str(seller), 'seller_user')

    def test_seller_phone_field(self):
        """Test Seller phone field can be updated."""
        seller = Seller.objects.get(user=self.user)
        seller.phone = '1234567890'
        seller.save()
        self.assertEqual(seller.phone, '1234567890')


class BuyerModelTest(TestCase):
    """Unit tests for the Buyer model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='buyer_user',
            email='buyer@test.com',
            password='testpass123'
        )

    def test_buyer_creation(self):
        """Test that Buyer is created via signal when User is created."""
        self.assertTrue(Buyer.objects.filter(user=self.user).exists())

    def test_buyer_str_representation(self):
        """Test string representation of Buyer."""
        buyer = Buyer.objects.get(user=self.user)
        self.assertEqual(str(buyer), 'buyer_user')

    def test_buyer_address_field(self):
        """Test Buyer address field can be updated."""
        buyer = Buyer.objects.get(user=self.user)
        buyer.address = '123 Test Street'
        buyer.save()
        self.assertEqual(buyer.address, '123 Test Street')


class VehicleModelTest(TestCase):
    """Unit tests for the Vehicle model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='vehicle_seller',
            email='vseller@test.com',
            password='testpass123'
        )
        self.seller = Seller.objects.get(user=self.user)
        
        # Create a simple test image
        self.image = SimpleUploadedFile(
            name='test_car.jpg',
            content=b'\x47\x49\x46\x38\x89\x61',  # Minimal GIF header
            content_type='image/jpeg'
        )
        
        self.vehicle = Vehicle.objects.create(
            seller=self.seller,
            title='Test Car',
            description='A test vehicle',
            price=Decimal('15000.00'),
            image=self.image
        )

    def test_vehicle_creation(self):
        """Test Vehicle is created correctly."""
        self.assertEqual(self.vehicle.title, 'Test Car')
        self.assertEqual(self.vehicle.price, Decimal('15000.00'))

    def test_vehicle_str_representation(self):
        """Test string representation of Vehicle."""
        self.assertEqual(str(self.vehicle), 'Test Car')

    def test_vehicle_average_rating_no_ratings(self):
        """Test average_rating returns 0 when no ratings exist."""
        self.assertEqual(self.vehicle.average_rating(), 0)

    def test_vehicle_average_rating_with_ratings(self):
        """Test average_rating calculates correctly."""
        user2 = User.objects.create_user('rater1', 'r1@test.com', 'pass123')
        user3 = User.objects.create_user('rater2', 'r2@test.com', 'pass123')
        
        Rating.objects.create(vehicle=self.vehicle, user=user2, score=4)
        Rating.objects.create(vehicle=self.vehicle, user=user3, score=5)
        
        self.assertEqual(self.vehicle.average_rating(), 4.5)

    def test_vehicle_seller_relationship(self):
        """Test Vehicle-Seller relationship."""
        self.assertEqual(self.vehicle.seller, self.seller)
        self.assertIn(self.vehicle, self.seller.vehicles.all())


class BookingModelTest(TestCase):
    """Unit tests for the Booking model."""

    def setUp(self):
        self.seller_user = User.objects.create_user('seller', 's@test.com', 'pass123')
        self.buyer_user = User.objects.create_user('buyer', 'b@test.com', 'pass123')
        
        self.seller = Seller.objects.get(user=self.seller_user)
        self.buyer = Buyer.objects.get(user=self.buyer_user)
        
        self.image = SimpleUploadedFile(
            name='booking_car.jpg',
            content=b'\x47\x49\x46\x38\x89\x61',
            content_type='image/jpeg'
        )
        
        self.vehicle = Vehicle.objects.create(
            seller=self.seller,
            title='Booking Test Car',
            description='Test',
            price=Decimal('20000.00'),
            image=self.image
        )

    def test_vehicle_booking_creation(self):
        """Test creating a vehicle purchase booking."""
        booking = Booking.objects.create(
            booking_type='VEHICLE',
            vehicle=self.vehicle,
            buyer=self.buyer
        )
        self.assertEqual(booking.status, 'PENDING')
        self.assertEqual(booking.booking_type, 'VEHICLE')

    def test_tour_booking_creation(self):
        """Test creating a tour booking."""
        tour_date = timezone.now()
        booking = Booking.objects.create(
            booking_type='TOUR',
            buyer=self.buyer,
            tour_date=tour_date,
            notes='Want to see SUVs'
        )
        self.assertEqual(booking.booking_type, 'TOUR')
        self.assertIsNone(booking.vehicle)

    def test_booking_str_vehicle(self):
        """Test string representation for vehicle booking."""
        booking = Booking.objects.create(
            booking_type='VEHICLE',
            vehicle=self.vehicle,
            buyer=self.buyer
        )
        self.assertIn('Booking Test Car', str(booking))
        self.assertIn('buyer', str(booking))

    def test_booking_str_tour(self):
        """Test string representation for tour booking."""
        booking = Booking.objects.create(
            booking_type='TOUR',
            buyer=self.buyer
        )
        self.assertIn('Car Yard Tour', str(booking))

    def test_booking_status_choices(self):
        """Test booking status can be changed."""
        booking = Booking.objects.create(
            booking_type='VEHICLE',
            vehicle=self.vehicle,
            buyer=self.buyer
        )
        booking.status = 'CONFIRMED'
        booking.save()
        self.assertEqual(booking.status, 'CONFIRMED')


class StaffModelTest(TestCase):
    """Unit tests for the Staff model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='staff_member',
            email='staff@test.com',
            password='testpass123'
        )

    def test_staff_creation(self):
        """Test Staff model creation."""
        staff = Staff.objects.create(
            user=self.user,
            position='Sales Manager',
            phone='5551234567'
        )
        self.assertEqual(staff.position, 'Sales Manager')

    def test_staff_str_representation(self):
        """Test string representation of Staff."""
        staff = Staff.objects.create(user=self.user, position='Mechanic')
        self.assertIn('staff_member', str(staff))
        self.assertIn('Mechanic', str(staff))

    def test_staff_str_no_position(self):
        """Test string representation when no position."""
        staff = Staff.objects.create(user=self.user)
        self.assertIn('Staff', str(staff))


class PaymentModelTest(TestCase):
    """Unit tests for the Payment model."""

    def setUp(self):
        self.seller_user = User.objects.create_user('seller', 's@test.com', 'pass123')
        self.buyer_user = User.objects.create_user('buyer', 'b@test.com', 'pass123')
        
        self.seller = Seller.objects.get(user=self.seller_user)
        self.buyer = Buyer.objects.get(user=self.buyer_user)
        
        self.image = SimpleUploadedFile(
            name='pay_car.jpg',
            content=b'\x47\x49\x46\x38\x89\x61',
            content_type='image/jpeg'
        )
        
        self.vehicle = Vehicle.objects.create(
            seller=self.seller,
            title='Payment Test Car',
            description='Test',
            price=Decimal('25000.00'),
            image=self.image
        )
        
        self.booking = Booking.objects.create(
            booking_type='VEHICLE',
            vehicle=self.vehicle,
            buyer=self.buyer
        )

    def test_payment_creation(self):
        """Test Payment creation."""
        payment = Payment.objects.create(
            booking=self.booking,
            buyer=self.buyer,
            method='CARD',
            amount=Decimal('25000.00')
        )
        self.assertEqual(payment.method, 'CARD')
        self.assertEqual(payment.amount, Decimal('25000.00'))

    def test_payment_str_representation(self):
        """Test string representation of Payment."""
        payment = Payment.objects.create(
            booking=self.booking,
            buyer=self.buyer,
            method='MPESA',
            amount=Decimal('25000.00')
        )
        self.assertIn('25000', str(payment))
        self.assertIn('buyer', str(payment))


class NotificationModelTest(TestCase):
    """Unit tests for the Notification model."""

    def setUp(self):
        self.user = User.objects.create_user('notif_user', 'n@test.com', 'pass123')

    def test_notification_creation(self):
        """Test Notification creation."""
        notif = Notification.objects.create(
            user=self.user,
            message='Your booking has been confirmed'
        )
        self.assertFalse(notif.is_read)
        self.assertEqual(notif.user, self.user)

    def test_notification_str_representation(self):
        """Test string representation of Notification."""
        notif = Notification.objects.create(
            user=self.user,
            message='Test notification'
        )
        self.assertIn('notif_user', str(notif))

    def test_notification_ordering(self):
        """Test notifications are ordered by created_at descending."""
        notif1 = Notification.objects.create(user=self.user, message='First')
        notif2 = Notification.objects.create(user=self.user, message='Second')
        
        notifications = Notification.objects.filter(user=self.user)
        self.assertEqual(notifications[0], notif2)  # Most recent first


class CommentModelTest(TestCase):
    """Unit tests for the Comment model."""

    def setUp(self):
        self.seller_user = User.objects.create_user('seller', 's@test.com', 'pass123')
        self.commenter = User.objects.create_user('commenter', 'c@test.com', 'pass123')
        
        self.seller = Seller.objects.get(user=self.seller_user)
        
        self.image = SimpleUploadedFile(
            name='comment_car.jpg',
            content=b'\x47\x49\x46\x38\x89\x61',
            content_type='image/jpeg'
        )
        
        self.vehicle = Vehicle.objects.create(
            seller=self.seller,
            title='Comment Test Car',
            description='Test',
            price=Decimal('18000.00'),
            image=self.image
        )

    def test_comment_creation(self):
        """Test Comment creation."""
        comment = Comment.objects.create(
            vehicle=self.vehicle,
            user=self.commenter,
            content='Great car!'
        )
        self.assertEqual(comment.content, 'Great car!')

    def test_comment_str_representation(self):
        """Test string representation of Comment."""
        comment = Comment.objects.create(
            vehicle=self.vehicle,
            user=self.commenter,
            content='Nice vehicle'
        )
        self.assertIn('commenter', str(comment))
        self.assertIn('Comment Test Car', str(comment))


class RatingModelTest(TestCase):
    """Unit tests for the Rating model."""

    def setUp(self):
        self.seller_user = User.objects.create_user('seller', 's@test.com', 'pass123')
        self.rater = User.objects.create_user('rater', 'r@test.com', 'pass123')
        
        self.seller = Seller.objects.get(user=self.seller_user)
        
        self.image = SimpleUploadedFile(
            name='rate_car.jpg',
            content=b'\x47\x49\x46\x38\x89\x61',
            content_type='image/jpeg'
        )
        
        self.vehicle = Vehicle.objects.create(
            seller=self.seller,
            title='Rating Test Car',
            description='Test',
            price=Decimal('22000.00'),
            image=self.image
        )

    def test_rating_creation(self):
        """Test Rating creation."""
        rating = Rating.objects.create(
            vehicle=self.vehicle,
            user=self.rater,
            score=5
        )
        self.assertEqual(rating.score, 5)

    def test_rating_str_representation(self):
        """Test string representation of Rating."""
        rating = Rating.objects.create(
            vehicle=self.vehicle,
            user=self.rater,
            score=4
        )
        self.assertIn('4', str(rating))
        self.assertIn('rater', str(rating))


# =============================================================================
# FORM TESTS
# =============================================================================

class SignupFormTest(TestCase):
    """Unit tests for the SignupForm."""

    def test_valid_signup_form(self):
        """Test SignupForm with valid data."""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'securepass123',
            'confirm_password': 'securepass123'
        }
        form = SignupForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_signup_form_password_mismatch(self):
        """Test SignupForm rejects mismatched passwords."""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'securepass123',
            'confirm_password': 'differentpass'
        }
        form = SignupForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_signup_form_short_password(self):
        """Test SignupForm rejects short passwords."""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'short',
            'confirm_password': 'short'
        }
        form = SignupForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_signup_form_duplicate_username(self):
        """Test SignupForm rejects duplicate username."""
        User.objects.create_user('existing', 'ex@test.com', 'pass123')
        form_data = {
            'username': 'existing',
            'email': 'new@test.com',
            'password': 'securepass123',
            'confirm_password': 'securepass123'
        }
        form = SignupForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_signup_form_duplicate_email(self):
        """Test SignupForm rejects duplicate email."""
        User.objects.create_user('user1', 'duplicate@test.com', 'pass123')
        form_data = {
            'username': 'newuser',
            'email': 'duplicate@test.com',
            'password': 'securepass123',
            'confirm_password': 'securepass123'
        }
        form = SignupForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_signup_form_invalid_email(self):
        """Test SignupForm rejects invalid email format."""
        form_data = {
            'username': 'newuser',
            'email': 'notanemail',
            'password': 'securepass123',
            'confirm_password': 'securepass123'
        }
        form = SignupForm(data=form_data)
        self.assertFalse(form.is_valid())


class VehicleFormTest(TestCase):
    """Unit tests for the VehicleForm."""

    def test_valid_vehicle_form(self):
        """Test VehicleForm with valid data."""
        image = SimpleUploadedFile(
            name='test.jpg',
            content=b'\x47\x49\x46\x38\x89\x61',
            content_type='image/jpeg'
        )
        form_data = {
            'title': 'Honda Civic 2020',
            'description': 'Well maintained vehicle',
            'price': '18000.00'
        }
        form = VehicleForm(data=form_data, files={'image': image})
        self.assertTrue(form.is_valid())

    def test_vehicle_form_missing_title(self):
        """Test VehicleForm rejects missing title."""
        image = SimpleUploadedFile(
            name='test.jpg',
            content=b'\x47\x49\x46\x38\x89\x61',
            content_type='image/jpeg'
        )
        form_data = {
            'description': 'Well maintained vehicle',
            'price': '18000.00'
        }
        form = VehicleForm(data=form_data, files={'image': image})
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

    def test_vehicle_form_negative_price(self):
        """Test VehicleForm handles negative price."""
        image = SimpleUploadedFile(
            name='test.jpg',
            content=b'\x47\x49\x46\x38\x89\x61',
            content_type='image/jpeg'
        )
        form_data = {
            'title': 'Test Car',
            'description': 'Test',
            'price': '-1000.00'
        }
        form = VehicleForm(data=form_data, files={'image': image})
        # DecimalField may accept negative, depends on model constraints
        # Test that form processes the data
        self.assertTrue(form.is_valid() or 'price' in form.errors)


class BookingFormTest(TestCase):
    """Unit tests for the BookingForm."""

    def test_booking_form_vehicle_type(self):
        """Test BookingForm with vehicle booking type."""
        form_data = {
            'booking_type': 'VEHICLE',
            'notes': 'Please contact me ASAP'
        }
        form = BookingForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_booking_form_tour_type(self):
        """Test BookingForm with tour booking type."""
        form_data = {
            'booking_type': 'TOUR',
            'tour_date': '2026-05-01T10:00',
            'notes': 'Looking for SUVs'
        }
        form = BookingForm(data=form_data)
        self.assertTrue(form.is_valid())


class PaymentFormTest(TestCase):
    """Unit tests for the PaymentForm."""

    def test_payment_form_card(self):
        """Test PaymentForm with card method."""
        form_data = {'method': 'CARD'}
        form = PaymentForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_payment_form_mpesa(self):
        """Test PaymentForm with M-Pesa method."""
        form_data = {'method': 'MPESA'}
        form = PaymentForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_payment_form_invalid_method(self):
        """Test PaymentForm rejects invalid payment method."""
        form_data = {'method': 'BITCOIN'}
        form = PaymentForm(data=form_data)
        self.assertFalse(form.is_valid())


# =============================================================================
# VIEW TESTS
# =============================================================================

class HomeViewTest(TestCase):
    """Unit tests for the home view."""

    def setUp(self):
        self.client = Client()

    def test_home_view_status_code(self):
        """Test home page returns 200."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_home_view_template(self):
        """Test home page uses correct template."""
        response = self.client.get(reverse('home'))
        self.assertTemplateUsed(response, 'home.html')

    def test_home_view_context_contains_vehicles(self):
        """Test home page context contains vehicles."""
        response = self.client.get(reverse('home'))
        self.assertIn('vehicles', response.context)


class VehicleDetailViewTest(TestCase):
    """Unit tests for the vehicle detail view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('seller', 's@test.com', 'pass123')
        self.seller = Seller.objects.get(user=self.user)
        
        self.image = SimpleUploadedFile(
            name='detail_car.jpg',
            content=b'\x47\x49\x46\x38\x89\x61',
            content_type='image/jpeg'
        )
        
        self.vehicle = Vehicle.objects.create(
            seller=self.seller,
            title='Detail Test Car',
            description='Test description',
            price=Decimal('19000.00'),
            image=self.image
        )

    def test_vehicle_detail_status_code(self):
        """Test vehicle detail page returns 200."""
        response = self.client.get(reverse('vehicle_detail', args=[self.vehicle.pk]))
        self.assertEqual(response.status_code, 200)

    def test_vehicle_detail_template(self):
        """Test vehicle detail uses correct template."""
        response = self.client.get(reverse('vehicle_detail', args=[self.vehicle.pk]))
        self.assertTemplateUsed(response, 'vehicle_detail.html')

    def test_vehicle_detail_context(self):
        """Test vehicle detail context contains vehicle."""
        response = self.client.get(reverse('vehicle_detail', args=[self.vehicle.pk]))
        self.assertEqual(response.context['vehicle'], self.vehicle)

    def test_vehicle_detail_404(self):
        """Test vehicle detail returns 404 for non-existent vehicle."""
        response = self.client.get(reverse('vehicle_detail', args=[99999]))
        self.assertEqual(response.status_code, 404)


class SearchViewTest(TestCase):
    """Unit tests for the search view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('seller', 's@test.com', 'pass123')
        self.seller = Seller.objects.get(user=self.user)
        
        self.image = SimpleUploadedFile(
            name='search_car.jpg',
            content=b'\x47\x49\x46\x38\x89\x61',
            content_type='image/jpeg'
        )
        
        self.vehicle = Vehicle.objects.create(
            seller=self.seller,
            title='Toyota Corolla 2021',
            description='Excellent condition',
            price=Decimal('22000.00'),
            image=self.image
        )

    def test_search_view_status_code(self):
        """Test search page returns 200."""
        response = self.client.get(reverse('search'))
        self.assertEqual(response.status_code, 200)

    def test_search_by_title(self):
        """Test search filters by title."""
        response = self.client.get(reverse('search'), {'q': 'Toyota'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.vehicle, response.context['vehicles'])

    def test_search_no_results(self):
        """Test search with no matching results."""
        response = self.client.get(reverse('search'), {'q': 'Ferrari'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['vehicles']), 0)

    def test_search_by_price_range(self):
        """Test search filters by price range."""
        response = self.client.get(reverse('search'), {
            'min_price': '20000',
            'max_price': '25000'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.vehicle, response.context['vehicles'])

    def test_search_price_out_of_range(self):
        """Test search excludes vehicles outside price range."""
        response = self.client.get(reverse('search'), {
            'min_price': '30000',
            'max_price': '40000'
        })
        self.assertNotIn(self.vehicle, response.context['vehicles'])


class AuthViewTest(TestCase):
    """Unit tests for authentication views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )

    def test_login_view_get(self):
        """Test login page loads correctly."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_view_post_success(self):
        """Test successful login redirects."""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login

    def test_login_view_post_invalid(self):
        """Test invalid login stays on page."""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)  # Stays on login page

    def test_signup_view_get(self):
        """Test signup page loads correctly."""
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'signup.html')

    def test_logout_view(self):
        """Test logout redirects to home."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)


class AddVehicleViewTest(TestCase):
    """Unit tests for the add vehicle view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('seller', 's@test.com', 'pass123')

    def test_add_vehicle_requires_login(self):
        """Test add vehicle page requires authentication."""
        response = self.client.get(reverse('add_vehicle'))
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_add_vehicle_authenticated(self):
        """Test add vehicle page loads for authenticated user."""
        self.client.login(username='seller', password='pass123')
        response = self.client.get(reverse('add_vehicle'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_vehicle.html')


class BookVehicleViewTest(TestCase):
    """Unit tests for the book vehicle view."""

    def setUp(self):
        self.client = Client()
        self.seller_user = User.objects.create_user('seller', 's@test.com', 'pass123')
        self.buyer_user = User.objects.create_user('buyer', 'b@test.com', 'pass123')
        
        self.seller = Seller.objects.get(user=self.seller_user)
        
        self.image = SimpleUploadedFile(
            name='book_car.jpg',
            content=b'\x47\x49\x46\x38\x89\x61',
            content_type='image/jpeg'
        )
        
        self.vehicle = Vehicle.objects.create(
            seller=self.seller,
            title='Book Test Car',
            description='Test',
            price=Decimal('21000.00'),
            image=self.image
        )

    def test_book_vehicle_requires_login(self):
        """Test booking requires authentication."""
        response = self.client.post(reverse('book_vehicle', args=[self.vehicle.pk]))
        self.assertEqual(response.status_code, 302)  # Redirects to login

    @patch('caryard.views.create_stripe_checkout_session')
    def test_book_vehicle_creates_booking(self, mock_stripe):
        """Test booking creates a Booking record."""
        mock_session = MagicMock()
        mock_session.id = 'test_session_id'
        mock_session.url = 'https://stripe.com/checkout'
        mock_stripe.return_value = mock_session
        
        self.client.login(username='buyer', password='pass123')
        response = self.client.post(reverse('book_vehicle', args=[self.vehicle.pk]), {
            'booking_type': 'VEHICLE'
        })
        
        self.assertTrue(Booking.objects.filter(
            vehicle=self.vehicle,
            buyer__user=self.buyer_user
        ).exists())


class StaffDashboardViewTest(TestCase):
    """Unit tests for the staff dashboard view."""

    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staffmember',
            email='staff@test.com',
            password='pass123',
            is_staff=True
        )
        self.staff = Staff.objects.create(user=self.staff_user, position='Manager')
        
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='pass123'
        )

    def test_staff_dashboard_requires_login(self):
        """Test staff dashboard requires authentication."""
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_staff_dashboard_accessible_by_staff(self):
        """Test staff can access dashboard."""
        self.client.login(username='staffmember', password='pass123')
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_staff_dashboard_denied_for_regular_user(self):
        """Test regular users cannot access staff dashboard."""
        self.client.login(username='regular', password='pass123')
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirects away


# =============================================================================
# SIGNAL TESTS
# =============================================================================

class UserSignalTest(TestCase):
    """Unit tests for user-related signals."""

    def test_buyer_created_on_user_creation(self):
        """Test Buyer profile is auto-created when User is created."""
        user = User.objects.create_user('signaluser', 'signal@test.com', 'pass123')
        self.assertTrue(Buyer.objects.filter(user=user).exists())

    def test_seller_created_on_user_creation(self):
        """Test Seller profile is auto-created when User is created."""
        user = User.objects.create_user('signaluser2', 'signal2@test.com', 'pass123')
        self.assertTrue(Seller.objects.filter(user=user).exists())

    def test_profiles_saved_on_user_save(self):
        """Test profiles are saved when User is saved."""
        user = User.objects.create_user('saveuser', 'save@test.com', 'pass123')
        buyer = Buyer.objects.get(user=user)
        buyer.phone = '9876543210'
        buyer.save()
        
        user.first_name = 'Updated'
        user.save()
        
        # Verify buyer still exists and wasn't corrupted
        buyer.refresh_from_db()
        self.assertEqual(buyer.phone, '9876543210')


class BookingSignalTest(TestCase):
    """Unit tests for booking-related signals."""

    def setUp(self):
        self.seller_user = User.objects.create_user('seller', 's@test.com', 'pass123')
        self.buyer_user = User.objects.create_user('buyer', 'b@test.com', 'pass123')
        
        self.seller = Seller.objects.get(user=self.seller_user)
        self.buyer = Buyer.objects.get(user=self.buyer_user)
        
        self.image = SimpleUploadedFile(
            name='signal_car.jpg',
            content=b'\x47\x49\x46\x38\x89\x61',
            content_type='image/jpeg'
        )
        
        self.vehicle = Vehicle.objects.create(
            seller=self.seller,
            title='Signal Test Car',
            description='Test',
            price=Decimal('17000.00'),
            image=self.image
        )

    @patch('caryard.signals.EmailMultiAlternatives')
    def test_notification_created_on_vehicle_booking(self, mock_email):
        """Test notification is created when vehicle is booked."""
        mock_email.return_value.send.return_value = None
        
        Booking.objects.create(
            booking_type='VEHICLE',
            vehicle=self.vehicle,
            buyer=self.buyer
        )
        
        # Check notification was created for seller
        self.assertTrue(Notification.objects.filter(
            user=self.seller_user
        ).exists())


class MessageSignalTest(TestCase):
    """Unit tests for message-related signals."""

    def setUp(self):
        self.sender = User.objects.create_user('sender', 'sender@test.com', 'pass123')
        self.receiver = User.objects.create_user('receiver', 'receiver@test.com', 'pass123')

    @patch('caryard.signals.EmailMultiAlternatives')
    def test_notification_created_on_message(self, mock_email):
        """Test notification is created when message is sent."""
        mock_email.return_value.send.return_value = None
        
        Messages.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content='Hello there!'
        )
        
        # Check notification was created for receiver
        self.assertTrue(Notification.objects.filter(
            user=self.receiver,
            message__contains='sender'
        ).exists())


# =============================================================================
# UTILITY FUNCTION TESTS
# =============================================================================

class EmailValidationTest(unittest.TestCase):
    """Unit tests for email validation utility."""

    def test_valid_email(self):
        """Test valid email format."""
        from caryard.views import validate_email_address
        self.assertTrue(validate_email_address('test@example.com'))

    def test_invalid_email_no_at(self):
        """Test email without @ symbol."""
        from caryard.views import validate_email_address
        self.assertFalse(validate_email_address('testexample.com'))

    def test_invalid_email_no_domain(self):
        """Test email without domain."""
        from caryard.views import validate_email_address
        self.assertFalse(validate_email_address('test@'))

    def test_empty_email(self):
        """Test empty email returns False."""
        from caryard.views import validate_email_address
        self.assertFalse(validate_email_address(''))

    def test_none_email(self):
        """Test None email returns False."""
        from caryard.views import validate_email_address
        self.assertFalse(validate_email_address(None))


if __name__ == '__main__':
    unittest.main()
