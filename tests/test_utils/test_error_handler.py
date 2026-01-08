"""Unit tests for ErrorHandler."""

import pytest
from unittest.mock import Mock
import requests
from lib_zerodha.utils.error_handler import error_handler
from lib_zerodha.exceptions import APIError, NetworkError, AuthenticationError, ValidationError

class TestErrorHandler:
    def test_handle_timeout(self):
        e = requests.exceptions.Timeout("Timeout")
        with pytest.raises(NetworkError, match="Timeout"):
            error_handler.handle_request_exception(e, "test_op")

    def test_handle_connection_error(self):
        e = requests.exceptions.ConnectionError("ConnErr")
        with pytest.raises(NetworkError, match="Connection failed"):
            error_handler.handle_request_exception(e, "test_op")

    def test_handle_401(self):
        response = Mock()
        response.status_code = 401
        response.headers = {'content-type': 'application/json'}
        response.json.return_value = {"status": "error", "message": "Auth failed", "error_type": "TokenException"}
        e = requests.exceptions.HTTPError(response=response)
        
        with pytest.raises(AuthenticationError, match="Auth failed"):
            error_handler.handle_request_exception(e, "test_op")

    def test_handle_400(self):
        response = Mock()
        response.status_code = 400
        response.headers = {'content-type': 'application/json'}
        response.json.return_value = {"status": "error", "message": "Bad request", "error_type": "InputException"}
        e = requests.exceptions.HTTPError(response=response)
        
        with pytest.raises(ValidationError, match="Bad request"):
            error_handler.handle_request_exception(e, "test_op")

    def test_validate_api_response_success(self):
        data = {"status": "success", "data": {"key": "value"}}
        result = error_handler.validate_api_response(data, "test_op")
        assert result == {"key": "value"}

    def test_validate_api_response_error(self):
        data = {"status": "error", "message": "API Failure", "error_type": "GeneralException"}
        with pytest.raises(APIError, match="API Failure"):
            error_handler.validate_api_response(data, "test_op")
