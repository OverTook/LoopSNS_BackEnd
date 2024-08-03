from abc import ABC, abstractmethod
from flask import request, jsonify

# KUMap Exception abstract class
class AppException(ABC, Exception):
    @property
    @abstractmethod
    def status_code(self):
        pass

    @property
    @abstractmethod
    def err_msg(self):
        pass
    
    @abstractmethod
    def __str__(self):
        pass

class MissingParamException(AppException):
    def __init__(self, missing_params):
        self.missing_params = missing_params
    
    @property
    def status_code(self):
        return 400
    
    @property
    def err_msg(self):
        return f"missing json parameters: {', '.join(self.missing_params)}"
    
    def __str__(self):
        return self.err_msg

def validate_args_params(*params):
    _params = list(params)
    missing_params = [param for param in _params if param not in request.args]
    if missing_params:
        raise MissingParamException(missing_params)

def validate_json_params(*params):
    _params = list(params)
    missing_params = [param for param in _params if param not in request.json]
    if missing_params:
        raise MissingParamException(missing_params)