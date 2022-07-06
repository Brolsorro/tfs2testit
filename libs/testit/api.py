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

    def _request(self, type_request: _RequestTypes, url: str, data:dict=None):

        headers = {
            'Authorization': f'PrivateToken {self.token}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        url = f'{self.address}' + url
        if type_request is _RequestTypes.GET:
            response = requests.get(url, verify=self.verify, headers=headers)
        elif type_request is _RequestTypes.POST:
            response = requests.post(url, verify=self.verify, headers=headers,json=data)
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
        name = name_project
        projects = self.get_all_projects()
        idProject = [v['id'] for v in projects if v['name'] == name]
        if not idProject:
            raise AssertionError(f"Not project: {name}")
        else:
            idProject = idProject[0]
        return {'id': idProject, 'name': name}

    def get_sections_on_project(self, id_project: str):
        return self._request(_RequestTypes.GET,
                      f'/api/v2/projects/{id_project}/sections')

    def create_test_suite(self):
        data = {
            "name": "base test suite"
        }
        rps = self._request(_RequestTypes.POST, '/api/v2/testSuites',data=data)
        return rps

    def create_test_case(self, id_project:UUID,id_section:UUID):
        data = {
            "entityTypeName": "TestCases",
            "description": "This is a basic test template",
            "state": "NeedsWork",
            "priority": "Lowest",
            "steps": [
                {
                "action": "User press the button",
                "expected": "System makes a beeeep sound",
                "testData": "Some variables values",
                "comments": "Comment on what to look for",
                }
            ],
            "preconditionSteps": [
                {

                "action": "User press the button",
                "expected": "System makes a beeeep sound",
                "testData": "Some variables values",
                "comments": "Comment on what to look for",
   
                }
            ],
            "postconditionSteps": [
                {
                "action": "User press the button",
                "expected": "System makes a beeeep sound",
                "testData": "Some variables values",
                "comments": "Comment on what to look for",
                }
            ],
            "duration": 10000,
            "attributes": {},
            "tags": [
                {
                "name": "string"
                }
            ],
            "attachments": [
                {
                "id": "a834ed64-2d73-448e-9d46-a5027d832d35"
                }
            ],
            "iterations": [
                {
                "parameters": [
                    {
                    "id": "a834ed64-2d73-448e-9d46-a5027d832d35"
                    }
                ],
                "id": "00000000-0000-0000-0000-000000000000"
                }
            ],
            "links": [
                {
                "title": "string",
                "url": "https://google.com/",
                "description": "This link leads to google main page (no advertising)",
                "type": "Related",
                "hasInfo": True
                }
            ],
            "name": "Basic template",
            "projectId": id_project,
            "sectionId": id_section,
            "autoTests": [
                {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
                }
            ]
            }
        # del data['steps']
        # del data['preconditionSteps']
        # del data['postconditionSteps']
        del data['attachments']
        del data['iterations']
        del data['autoTests']
        rps = self._request(_RequestTypes.POST, '/api/v2/workItems',data=data)
        return rps