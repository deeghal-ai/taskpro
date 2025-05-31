# Create a new file: middleware.py
import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        # Log the exception
        logger.exception(f"Unhandled exception in request: {request.path}")
        
        # For API endpoints, return JSON response
        if request.path.startswith('/api/'):
            return JsonResponse({
                'success': False,
                'error': 'An unexpected error occurred. Please try again later.'
            }, status=500)
        
        # For regular requests, the standard Django error page will be shown
        return None