from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .presenters import present
from .serializers import AnalyzeRequestSerializer
from .services import get_analyzer, get_geocoder


class AnalyzeView(APIView):
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = AnalyzeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(present(get_analyzer().analyze(serializer.to_trip_request())))


class GeocodeView(APIView):
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < 3:
            return Response([])
        return Response([{"label": r.label, "lat": r.lat, "lng": r.lng} for r in get_geocoder().search(q[:120])])


class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})
