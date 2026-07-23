from django.urls import path
from . import views



urlpatterns = [
    path('', views.home, name="home"),

 # Vehicles
    path("vehicle/<int:pk>/", views.vehicle_detail, name="vehicle_detail"),
    path("vehicle/<int:pk>/book/", views.book_vehicle, name="book_vehicle"),
    path("add-vehicle/", views.add_vehicle, name="add_vehicle"),

    # Payment
    path("payment/<int:booking_id>/", views.payment_view, name="payment"),
    path("payment/<int:booking_id>/stripe/", views.stripe_checkout, name="stripe_checkout"),
    path("payment/<int:booking_id>/mpesa/", views.mpesa_payment, name="mpesa_payment"),
    path("payment/mpesa/callback/", views.mpesa_callback, name="mpesa_callback"),
    path("payment/stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),

    # Ajax endpoints
    path("ajax/comment/", views.ajax_comment, name="ajax_comment"),
    path("ajax/rate/", views.ajax_rate, name="ajax_rate"),

    # Auth
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("login/verify/", views.verify_login_code, name="verify_login_code"),
    path("login/resend/", views.resend_login_code, name="resend_login_code"),
    path("logout/", views.logout_view, name="logout"),

    # Search
    path("search/", views.search, name="search"),

     
    #  Chatbot
    path("chatbot/", views.chatbot_response, name="chatbot"),


  
  path("payment/success/<int:booking_id>/", views.payment_success, name="payment_success"),
  path("payment/cancel/<int:booking_id>/", views.payment_cancel, name="payment_cancel"),
   
   
   
    # ... your other urls
  path('inbox/', views.inbox, name='inbox'),
  path('send/<str:username>/', views.send_message, name='send_message'),
  path('profile/', views.profile, name='profile'),
  path('notifications/', views.notifications_view, name='notifications'),


 # caryard/urls.py
path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
path('staff/booking/<int:booking_id>/update/', views.update_booking_status, name='update_booking_status'),
path('staff/signup/', views.staff_signup, name='staff_signup'),
path('assign-staff/<int:booking_id>/', views.assign_staff, name='assign_staff'),
path('chat/<int:user_id>/', views.chat_with_user, name='chat_with_user'),
path("manage/bookings/", views.manage_bookings, name="manage_bookings"),
path("my-bookings/", views.my_bookings, name="my_bookings"),


]
