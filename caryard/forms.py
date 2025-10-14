from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import re
from .models import Booking, Comment, Vehicle, Payment, Messages


def validate_email_format(email):
    """Custom email validation function"""
    if not email:
        raise ValidationError("Email is required.")
    
    # Basic email format validation
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        raise ValidationError("Please enter a valid email address.")
    
    # Check if email already exists
    if User.objects.filter(email=email).exists():
        raise ValidationError("An account with this email already exists.")
    
    return email


class StyledFormMixin:
    """
    Adds Bootstrap classes to form fields automatically.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
            visible.field.widget.attrs['placeholder'] = visible.label


class SignupForm(StyledFormMixin, forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        min_length=8,
        help_text="Password must be at least 8 characters long."
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="Please confirm your password."
    )
    email = forms.EmailField(
        validators=[validate_email_format],
        help_text="Please enter a valid email address."
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("A user with this username already exists.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")
        
        return cleaned_data


class BookingForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Booking
        fields = []  # booking just links vehicle + buyer


class CommentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']


class VehicleForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['title', 'description', 'price', 'image']


class PaymentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['method']


class MessageForm(forms.ModelForm):
    class mete:
        model = Messages
        fields = ['content']
        widgets ={
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Type your message here...'}),
        }

