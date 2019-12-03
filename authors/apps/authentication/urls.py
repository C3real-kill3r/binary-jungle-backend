from django.urls import path

from .views import (
    LoginAPIView,
    RegistrationAPIView,
    AccountVerificationView,
    UserRetrieveUpdateAPIView,
    ForgotPasswordView,
    ResetPasswordView,
    SocialSignUp, LogoutView,
    UsersAPIView)

app_name = "authentication"

urlpatterns = [
    path('user/', UserRetrieveUpdateAPIView.as_view(), name="user-retrieve-update"),
    path('users/', RegistrationAPIView.as_view(), name="user-register"),
    path('users/login/', LoginAPIView.as_view(), name="user-login"),
    path('users/logout/', LogoutView.as_view(), name="logout"),
    path('users/search/', UsersAPIView.as_view(), name='users-list'),
    path('account/verify/<str:token>/<str:uid>/', AccountVerificationView.as_view(),
         name='activate-account'),
    path('account/forgot_password/', ForgotPasswordView.as_view(), name="forgot-password"),
    path('account/reset_password/<str:token>/', ResetPasswordView.as_view(), name="reset-password"),
    path('users/social-auth/', SocialSignUp.as_view(), name='social'),
]
