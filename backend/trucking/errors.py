from rest_framework import status
from rest_framework.exceptions import APIException


class NoRouteError(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "No drivable route was found between these locations."


class ForecastUnavailableError(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Weather forecast is not available for the requested time window."


class UpstreamError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "An upstream data provider failed. Please retry shortly."
