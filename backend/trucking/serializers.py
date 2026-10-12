from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .domain.geo import haversine_mi
from .services.analysis import Place, TripRequest

MAX_GROSS_WEIGHT_LB = 80_000  # US federal gross vehicle weight limit
INTERVAL_CHOICES = (10, 25, 50)


class PlaceSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    label = serializers.CharField(required=False, allow_blank=True, max_length=200, default="")


class AnalyzeRequestSerializer(serializers.Serializer):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure_time = serializers.DateTimeField()
    load_weight_lb = serializers.IntegerField(min_value=0, max_value=MAX_GROSS_WEIGHT_LB)
    interval_miles = serializers.ChoiceField(choices=INTERVAL_CHOICES, default=25)

    def validate_departure_time(self, value):
        now = timezone.now()
        if value < now - timedelta(hours=24):
            raise serializers.ValidationError("Departure time cannot be more than 24 hours in the past.")
        if value > now + timedelta(days=13):
            raise serializers.ValidationError("Departure time must be within the next 13 days (forecast range).")
        return value

    def validate(self, attrs):
        o, d = attrs["origin"], attrs["destination"]
        if haversine_mi((o["lat"], o["lng"]), (d["lat"], d["lng"])) < 1:
            raise serializers.ValidationError("Origin and destination must be at least 1 mile apart.")
        return attrs

    def to_trip_request(self) -> TripRequest:
        v = self.validated_data
        return TripRequest(
            origin=Place(**v["origin"]),
            destination=Place(**v["destination"]),
            departure=v["departure_time"],
            weight_lb=v["load_weight_lb"],
            interval_mi=v["interval_miles"],
        )
