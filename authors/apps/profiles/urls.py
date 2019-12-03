from django.urls import path
from .views import ProfileListView, ProfileGetView, FollowUnFollowView, FollowersView, FollowingView, FollowingUserView

app_name = 'profiles'

urlpatterns = [
    path('', ProfileListView.as_view(), name='get-profiles'),
    path('<str:username>/', ProfileGetView.as_view(), name='profiles'),
    path('<str:username>/follow/', FollowUnFollowView.as_view(), name="follow"),
    path('<str:username>/followers/', FollowersView.as_view(), name="followers"),
    path('<str:username>/following/', FollowingView.as_view(), name="following"),
    path('following/<str:username>', FollowingUserView.as_view(), name="is-following"),
]
