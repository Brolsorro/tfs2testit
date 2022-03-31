import requests
import logging
import json
import os

from requests import Response
from pathlib import Path
from enum import Enum


class _RequestTypes(Enum):
    GET = 'get'
    POST = 'post'
    DELETE = 'delete'


class TestITAPI:

    def __init__(self, host, token, verify=None) -> None:
        self.address = host
        self.token = token
        self.verify = verify

    def _write_json_response(self, response: Response):
        # name_file = traceback.extract_stack(None, 3)[0][2]
        # name_file = Path(f'reports/{name_file}.json')
        error_name = Path('reports/error.html')
        responseJson = None
        try:
            # if name_file.exists():
            #     os.remove(name_file)
            res = response.json()
            responseJson = res
            # with open(name_file, 'w',encoding=self.ENCODING) as wr:
            #     wr.write(json.dumps(res,indent=4,ensure_ascii=False))

        except json.JSONDecodeError:
            ...
            if error_name.exists():
                os.remove(error_name)
            if response.status_code != 200:
                # responseJson = {'error':response.text}
                with open(error_name, 'wb') as wr:
                    wr.write(response.content)
        return responseJson

    def _request(self, type_request: _RequestTypes, url: str):

        headers = {
            'Authorization': f'PrivateToken {self.token}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        url = f'{self.address}' + url
        if type_request is _RequestTypes.GET:
            response = requests.get(url, verify=self.verify, headers=headers)
        elif type_request is _RequestTypes.POST:
            ...
        elif type_request is _RequestTypes.DELETE:
            ...
        logging.info(response.url)

        rt_json = self._write_json_response(response)
        if isinstance(rt_json,dict) or isinstance(rt_json,list):
            return rt_json
        else:
            return {'message':rt_json, 'statusCode':response.status_code}

    def get_all_projects(self):
        rps = self._request(_RequestTypes.GET, '/api/v2/projects')
        return rps

    def get_project_by_name(self, name_project: str):
        name = "Тестовый"
        projects = self.get_all_projects()
        idProject = [v['id'] for v in projects if v['name'] == name]
        if not idProject:
            raise AssertionError(f"Not project: {name}")
        else:
            idProject = idProject[0]
        return {'id': idProject, 'name': name}

    def get_sections_on_project(self, id_project: str):
        return self._request(_RequestTypes.GET,
                      '/api/v2/projects/{projectId}/sections')

    def create_test_suite(self):
        data = {
            "parentId": "2ec66cb5-cd34-4a7c-8608-e97d2dfbeb91",
            "testPlanId": "2ec66cb5-cd34-4a7c-8608-e97d2dfbeb91",
            "name": "base test suite"
        }
        rps = self._request(_RequestTypes.POST, '/api/v2/testSuites')
        return rps
