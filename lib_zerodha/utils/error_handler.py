"""Error handling utilities for consistent exception management."""

import logging
from typing import Optional, Dict, Any
import requests
from datetime import datetime

from ..exceptions import (
    APIError, NetworkError, AuthenticationError, 
    ValidationError, OrderError, MarketDataError
)


class ErrorHandler:
    """Centralized error handler for consistent exception management."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def handle_request_exception(self, e: requests.exceptions.RequestException, 
                               operation: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Handle requests exceptions with proper chaining and context.
        
        Args:
            e: The original request exception
            operation: Description of the operation that failed
            context: Additional context for debugging
        """
        error_context = {
            'operation': operation,
            'timestamp': datetime.now().isoformat(),
            'original_error_type': type(e).__name__,
            **(context or {})
        }
        
        # Extract detailed error information
        error_details = self._parse_response_error(e.response if hasattr(e, 'response') else None)
        
        # Log with context
        self.logger.error(f"Request failed for {operation}: {error_details or str(e)}", 
                         extra=error_context)
        
        # Determine appropriate exception type and raise with chaining
        if isinstance(e, requests.exceptions.Timeout):
            raise NetworkError(f"Timeout during {operation}: {str(e)}", context=error_context) from e
        elif isinstance(e, requests.exceptions.ConnectionError):
            raise NetworkError(f"Connection failed during {operation}: {str(e)}", context=error_context) from e
        elif hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            if status_code == 401:
                raise AuthenticationError(f"Authentication failed for {operation}: {error_details}", context=error_context) from e
            elif status_code == 400:
                raise ValidationError(f"Validation error in {operation}: {error_details}", context=error_context) from e
            elif status_code == 429:
                raise NetworkError(f"Rate limit exceeded for {operation}: {error_details}", context=error_context) from e
            else:
                raise APIError(f"API error in {operation}: {error_details}", context=error_context) from e
        else:
            raise NetworkError(f"Network error during {operation}: {str(e)}", context=error_context) from e
    
    def _parse_response_error(self, response) -> Optional[str]:
        """Parse API response to extract detailed error information.
        
        Args:
            response: HTTP response object
            
        Returns:
            Detailed error message or None
        """
        if not response:
            return None
        
        try:
            # Check content type
            content_type = response.headers.get('content-type', '')
            
            if content_type.startswith('application/json'):
                try:
                    error_data = response.json()
                    
                    # Handle Kite Connect API error format
                    if error_data.get('status') == 'error':
                        error_type = error_data.get('error_type', 'UnknownError')
                        message = error_data.get('message', 'No message provided')
                        
                        # Include additional details if available
                        details = []
                        if 'data' in error_data and error_data['data']:
                            details.append(f"Data: {error_data['data']}")
                        
                        if details:
                            return f"{error_type}: {message} ({', '.join(details)})"
                        else:
                            return f"{error_type}: {message}"
                    
                    # Generic JSON error response
                    elif 'error' in error_data:
                        return str(error_data['error'])
                    elif 'message' in error_data:
                        return str(error_data['message'])
                        
                except ValueError:
                    # JSON parsing failed
                    pass
            
            # Try to extract useful information from response text
            if hasattr(response, 'text') and response.text:
                # Limit response text to avoid huge error messages
                text = response.text[:500]
                if len(response.text) > 500:
                    text += "... (truncated)"
                return f"HTTP {response.status_code}: {text}"
            
            # Fallback to status code and reason
            return f"HTTP {response.status_code}: {getattr(response, 'reason', 'Unknown Error')}"
            
        except Exception as parse_error:
            self.logger.warning(f"Failed to parse error response: {parse_error}")
            return f"HTTP {getattr(response, 'status_code', 'Unknown')}: Parse error"
    
    def validate_api_response(self, response_data: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Validate API response and extract data with error handling.
        
        Args:
            response_data: Raw response data from API
            operation: Description of the operation
            
        Returns:
            Validated response data
            
        Raises:
            APIError: If response indicates an error
        """
        # Handle Kite Connect API response format
        if isinstance(response_data, dict):
            if response_data.get('status') == 'error':
                error_type = response_data.get('error_type', 'UnknownError')
                message = response_data.get('message', 'Unknown error occurred')
                
                # Create detailed error context
                context = {
                    'operation': operation,
                    'error_type': error_type,
                    'timestamp': datetime.now().isoformat()
                }
                
                if 'data' in response_data:
                    context['error_data'] = response_data['data']
                
                raise APIError(f"{operation} failed - {error_type}: {message}", context=context)
            
            # Return data field if present, otherwise return full response
            return response_data.get('data', response_data)
        
        # For non-dict responses, return as-is
        return response_data


# Global error handler instance
error_handler = ErrorHandler()