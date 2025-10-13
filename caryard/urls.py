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

    # Ajax endpoints
    path("ajax/comment/", views.ajax_comment, name="ajax_comment"),
    path("ajax/rate/", views.ajax_rate, name="ajax_rate"),

    # Auth
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Search
    path("search/", views.search, name="search"),

     
    #  Chatbot
    path("chatbot/", views.chatbot_response, name="chatbot"),


  
  path("payment/success/<int:booking_id>/", views.payment_success, name="payment_success"),
  path("payment/cancel/<int:booking_id>/", views.payment_cancel, name="payment_cancel"),
    # ... your other urls
    

]
