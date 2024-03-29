import logging
from cv2 import log
import requests
import base64
import json
import os, sys
import logging
import pathlib

from pathlib import Path
from requests import Response



class System:
    LinkTypes = 'System.LinkTypes'
    WorkItemType = 'System.WorkItemType'
    Title = 'System.Title'


class System_LinkTypes:
        Hierarchy_Reverse = 'System.LinkTypes.Hierarchy-Reverse'
        Hierarchy_Forward = 'System.LinkTypes.Hierarchy-Forward'
        Duplicate_Reverse = 'System.LinkTypes.Duplicate-Reverse'
        Dependency_Reverse = 'System.LinkTypes.Dependency-Reverse'
        Dependency_Forward = 'System.LinkTypes.Dependency-Forward'
        Related = 'System.LinkTypes.Related'
class Microsoft:
    VSTS = 'Microsoft.VSTS'
    
class Microsoft_VSTS:
    TCM = 'Microsoft.VSTS.TCM'

class Microsoft_VSTS_TCM:
    Steps = 'Microsoft.VSTS.TCM.Steps'
        
class Microsoft_VSTS_Common:
    Priority = 'Microsoft.VSTS.Common.Priority'
    TestedBy_Reverse = 'Microsoft.VSTS.Common.TestedBy-Reverse'
    TestedBy_Forward = 'Microsoft.VSTS.Common.TestedBy-Forward'

class Microsoft_VSTS_TestCase:
    SharedStepReferencedBy_Reverse = 'Microsoft.VSTS.TestCase.SharedStepReferencedBy-Reverse'

class APITFS:
    VERSION_API = '4.1'
    ENCODING = 'utf-8'

    def __init__(self, domain: str, organization: str, project: str, token: str, verify:Path=None) -> None:
        self.domain = domain
        self.organization = organization
        self.project = project
        self.token = token
        self.verify = verify
        pat = ":" + self.token
        self.pat_base64 = b'Basic ' + base64.b64encode(pat.encode("utf8"))

        logging.basicConfig(encoding='utf-8', level=logging.INFO)

    def _handler_response(self, response:Response):
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

        except json.JSONDecodeError as e:
            ...
            logging.error(f'Указан невереный параметр: проект <{self.project}>, коллекция <{self.organization}>, номер тестового плана...')
            logging.error(e)
            sys.exit(1)
            # if error_name.exists():
            #     os.remove(error_name)
            # if response.status_code != 200:
                # responseJson = {'error':response.text}
                # with open(error_name, 'wb') as wr:
                #     wr.write(response.content)
        return responseJson
    
    def _get_request(self, url:str,set_api_version=True):

        headers = {
            'Authorization': self.pat_base64,
            'Content-Type': 'application/json; charset=utf-8'
        }
        url = f'{self.domain}/{self.organization}/{self.project}' + url
        if set_api_version:
            url+=f'api-version={self.VERSION_API}'

        response = requests.get(url, verify=self.verify, headers=headers)
        # logging.info(response.url)

        rt_json=self._handler_response(response)
        return {'response':rt_json, 'status': response.status_code}

    def _post_request(self, url:str, body:dict):
        headers = {
            'Authorization': self.pat_base64,
            'Content-Type': 'application/json-patch+json'
        }
        url = f'{self.domain}/{self.organization}/{self.project}' + url + f'api-version={self.VERSION_API}'
        response = requests.post(url, verify=self.verify,
                            headers=headers, json=body, data=json.dumps(body))

        # logging.info(response.url)
        rt_json=self._handler_response(response)

        return {'response':rt_json, 'status': response.status_code}
    def get_any(self,*args, **kwargs):
        """Выполнить любой пользовательский запрос

        Returns:
            _type_: _description_
        """
        return self._get_request(*args, **kwargs)

    #FIXME: not supported
    # def get_information_plans(self,_id):
    #     return self._get_request(f'/_apis/work/plans/{_id}?')

    def get_all_plans(self):
        return self._get_request(f'/_apis/work/plans?')
    
    def get_work_item(self,item_id):
        return self._get_request(f'/_apis/wit/workitems/{item_id}?')
    
    def get_list_work_items(self,ids):
        return self._get_request(f'/_apis/wit/workitems?ids={ids}&$expand=all', set_api_version=False)

    def get_test_suites_from_plan(self,_id):
        return self._get_request(f'/_api/_testManagement/GetTestSuitesForPlan?__v=5&planId={_id}',set_api_version=False)
        
    def get_tests_from_suite(self,plan_id, suite_id):
        payload = {"testPlanId":plan_id,"testSuiteId":suite_id,"repopulateSuite":"true","columns":"[]","top":500,"recursive":"false","outcomeFilter":"","testerFilter":"All","configurationFilter":-1}
        return self._post_request(f'/_api/_testManagement/GetTestPointsForSuite?__v=5',payload)
