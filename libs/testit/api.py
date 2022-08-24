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
        self.testit_project_id = ...
        self.testit_section_id = ...

    def _json_response(self, response: Response):
        # name_file = traceback.extract_stack(None, 3)[0][2]
        # name_file = Path(f'reports/{name_file}.json')
        # error_name = Path('reports/error.html')
        responseJson = None
        try:
            # if name_file.exists():
            #     os.remove(name_file)
            res = response.json()
            responseJson = res
            # with open(name_file, 'w',encoding=self.ENCODING) as wr:
            #     wr.write(json.dumps(res,indent=4,ensure_ascii=False))

        except json.JSONDecodeError:
            responseJson = {'error':response.text}
            # if error_name.exists():
            #     os.remove(error_name)
            # if response.status_code != 200:
            #     # responseJson = {'error':response.text}
            #     with open(error_name, 'wb') as wr:
            #         wr.write(response.content)
        return responseJson

    def _request(self, type_request: _RequestTypes, url: str, data:dict='None'):

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
        if not response.ok:
            logging.error(response.json())
            response.raise_for_status()
        rt_json = self._json_response(response)
        if isinstance(rt_json,dict) or isinstance(rt_json,list):
            return rt_json
        else:
            rtn = {'message':rt_json, 'statusCode':response.status_code}
            return rtn
            
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

    def get_id_project_by_name(self, name_project: str) -> UUID:
        name = name_project
        projects = self.get_all_projects()
        idProject = [v['id'] for v in projects if v['name'] == name]
        if not idProject:
            raise AssertionError(f"Not project: {name}")
        else:
            idProject = idProject[0]
        self.testit_project_id = idProject
        return idProject

    def get_id_sections_on_project(self, id_project: str = None):
        id_project = self.testit_project_id if not id_project else id_project
        rsp = self._request(_RequestTypes.GET,
                      f'/api/v2/projects/{id_project}/sections')
        first_section = [r for r in rsp if not r['parentId']][0]
        first_section = first_section.get('id')
        self.testit_section_id = first_section
        return first_section

    def get_sections_on_project(self, id_project: str = None):
        id_project = self.testit_project_id if not id_project else id_project
        rsp = self._request(_RequestTypes.GET,
                      f'/api/v2/projects/{id_project}/sections')
        return rsp

    def create_test_suite(self):
        data = {
            "name": "base test suite"
        }
        rps = self._request(_RequestTypes.POST, '/api/v2/testSuites',data=data)
        return rps

    def get_workitems_on_section(self,section_id):
        rps = self._request(_RequestTypes.GET, f'/api/v2/sections/{section_id}/workItems')
        return rps

    def create_test_case(self,data, attr_id_tfs:dict, project_id:UUID=None,parent_id:UUID=None ):
        
        project_id = self.testit_project_id if not project_id else project_id
        parent_id = self.testit_section_id if not parent_id else parent_id

        # id_attribute = self.get_projects_attributes_by_id_or_global()
        # id_attribute = [attr for attr in id_attribute if attr['id'] == attr_id_tfs['id']]
        # if id_attribute:
            # ...
        _attr_list = list(attr_id_tfs.items())[0]
        workitems = self.get_workitems_on_section(parent_id)
        workitems = [wim for wim in workitems if wim['attributes'][_attr_list[0]] == _attr_list[1] and wim['entityTypeName'] == 'TestCases']
        if workitems:
            logging.info(F'Test already created: ID TFS: {_attr_list[1]}')
            return workitems[0]
        modeldata = {
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
            "projectId": project_id,
            "sectionId": parent_id,
   
            }
        modeldata.update(data)
        rps = self._request(_RequestTypes.POST, '/api/v2/workItems',data=modeldata)
        return rps

    def create_shared_steps(self, data, attr_id_tfs:dict, project_id:UUID=None,parent_id:UUID=None):
        project_id = self.testit_project_id if not project_id else project_id
        parent_id = self.testit_section_id if not parent_id else parent_id

        _attr_list = list(attr_id_tfs.items())[0]
        workitems = self.get_workitems_on_section(parent_id)
        workitems = [wim for wim in workitems if wim['attributes'][_attr_list[0]] == _attr_list[1] and wim['entityTypeName'] == 'SharedSteps']
        if workitems:
            logging.info(F'Shared Steps already created: ID TFS: {_attr_list[1]}')
            return workitems[0]
        modeldata = {
            "entityTypeName": "SharedSteps",
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
                
            ],
            "postconditionSteps": [
                
            ],
            "attributes": {},
            "tags": [
                {
                "name": "string"
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
            "projectId": project_id,
            "sectionId": parent_id,

            }
        modeldata.update(data)
        rps = self._request(_RequestTypes.POST, '/api/v2/workItems',data=modeldata)
        return rps
    
    
    def create_section_on_project(self,name_section:str, project_id:UUID=None,parent_id:UUID=None) -> UUID:
            
        
        project_id = self.testit_project_id if not project_id else project_id
        parent_id = self.testit_section_id if not parent_id else parent_id

        exist_section = [sec for sec in self.get_sections_on_project(project_id) if sec['parentId']==parent_id and sec['name'] == name_section]
        if exist_section:
            logging.info(f'Section <{name_section}> already created!')
            return exist_section[0]['id']
            
        data = {
            "name": name_section,
            "projectId": project_id,

        }
        if parent_id: data.update({"parentId": parent_id})
        
        rps = self._request(_RequestTypes.POST, '/api/v2/sections',data=data)
        return rps['id']
    
    def create_attributes_on_project(self,name_attribute,project_id:UUID=None) -> UUID:
        project_id = self.testit_project_id if not project_id else project_id

        current_attributes = self.get_projects_attributes_by_id_or_global()
        current_attributes = [curr for curr in current_attributes if curr['name']==name_attribute]
        
        if current_attributes:
            logging.info(f'Attribute <{name_attribute}> already created for project!')
            return current_attributes[0]['id']
        
        data = {
            "options": [
                {
                "value": "Неизвестно",
                "isDefault": True
                }
            ],
            "type": "string",
            "name": name_attribute,
            "enabled": True,
            "required": False,
            "isGlobal": False
            }
        rps = self._request(_RequestTypes.POST, f'/api/v2/projects/{project_id}/attributes',data=data)
        return rps['id']

    def get_projects_attributes_by_id_or_global(self,project_id:UUID=None):
        project_id = self.testit_project_id if not project_id else project_id
        rps = self._request(_RequestTypes.GET, f'/api/v2/projects/{project_id}/attributes')
        return rps