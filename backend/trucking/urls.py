from django.urls import path

from . import views

urlpatterns = [
    path("routes/analyze", views.AnalyzeView.as_view()),
    path("geocode", views.GeocodeView.as_view()),
    path("health", views.HealthView.as_view()),
]
