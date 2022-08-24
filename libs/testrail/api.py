import requests
import logging
import json
import os


from requests import Response
from pathlib import Path
from enum import Enum
from uuid import UUID




class _RequestTypes(Enum):
    GET = 'get'
    POST = 'post'
    DELETE = 'delete'



class TestRailAPI:
    def __init__(self, token, address) -> None:
        pass