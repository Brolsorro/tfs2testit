import xml.etree.ElementTree as ET
import logging


from libs.testit.api import TestITAPI
from libs.tfs.api import *
from typing import Union, List, Dict, Tuple
from datetime import datetime
from tqdm import tqdm
from uuid import UUID
from bs4 import BeautifulSoup





class TypesCollections:
    TYPE_SUITE = 'suite'
    TYPE_TEST = 'test'

class MigrateTfsToTest():
    def __init__(self,
            testit_address,
            testit_token,
            tfs_address,
            tfs_organization,
            tfs_project,
            tfs_token,
            tfs_cert
            ) -> None:
        self.api_testit = TestITAPI(
            testit_address,
            testit_token,
        )
        self.api_tfs = APITFS(
            tfs_address, tfs_organization, tfs_project, tfs_token, tfs_cert
        )

        self.tabPriority = {
            1:'Highest',
            2:'High',
            3:'Medium',
            4:'Lowest'
        }

        self.tfs_address = tfs_address
        self.tfs_organization = tfs_organization
        self.tfs_project = tfs_project

    @classmethod
    def _get_link_mutable_object(cls, obj: Union[Dict, List], list_keys: Union[List, Tuple]) -> Union[Dict, List]:
        """Для создания ссылок вложенный объектов

        Args:
                obj (Union[Dict,List]): _description_
                list_keys (Any): _description_

        Returns:
                Union[Dict,List]: _description_
        """
        link = None
        for index, key in enumerate(list_keys):
            if index == 0:
                link = obj.pop(key)

                if type(obj) is dict:
                    obj[key] = link
                else:
                    obj.insert(key, link)
            else:
                tmp = link
                link = tmp.pop(key)
                if type(tmp) is dict:
                    tmp[key] = link
                else:
                    tmp.insert(0, link)

        return link

    def _recursive_nesting_traversal(self, suite_id, suite_index, suite_tree_static, suite_tree, suite_tree_index):
        """Рекурсивный обход полученного JSON через API для преобразования его иерархическое дерево
        с уникальнами ID и привязанным к ним сущностям. Один ко многим

        Args:
            suite_id (_type_): Первичный ID для сопоставления
            suite_index (_type_): Индекс смещения в словаре, с местоположение сущности с первичным ID
            suite_tree_static (_type_): Неизменяемая коллекция с оставшимися для связи сущностями
            suite_tree (_type_): Изменяемая коллекция с оставшимися для связи сущностями
            suite_tree_index (_type_): Индекс для изменения по срезу содержимого изменяемой сущности
        Returns:
            Нет возврата так, как идет работа с глобальными объектами класса

        """
        
        # Получить номер элементы для замены вложенности
        suiteMainIndex = [i for i, v in enumerate(
            suite_tree_static) if v['id'] == suite_id]
        if suiteMainIndex:
            suiteMainIndex = suiteMainIndex[0]
        else:
            return

        LINK_childIds = MigrateTfsToTest._get_link_mutable_object(
            suite_tree, (suite_tree_index, 'childIds'))
        LINK_childIds[suite_index] = suite_tree_static[suiteMainIndex]

        LINK_subChildIds = MigrateTfsToTest._get_link_mutable_object(
            LINK_childIds, (suite_index, 'childIds'))

        if LINK_subChildIds:
            for sub_index, sub_child_id in enumerate(LINK_subChildIds):
                self._recursive_nesting_traversal(
                    sub_child_id, sub_index, suite_tree_static, LINK_childIds, suite_index)
        del suite_tree_static[suiteMainIndex]

        return


    def _parse_steps(self,steps_string:str,**kwargs) -> list:
        """Парсинг шагов для тестов и распределение их на "актуальное" и "ожидание"

        Args:
            steps_string (str): Строка с шагами

        Returns:
            list: Список с распределенными шагами
        """
        # case_id = kwargs.get('case_id','')
        # logging.info(f'Обработка шагов теста № {case_id}')
        try:
            root = ET.fromstring(steps_string)

            steps = root
            stepsList = []

            def _get_all_steps(steps):
                for step in steps:
                    if step.get('ref'):
                        stepsList.append({
                            'type':'ref',
                            'ref':step.get('ref')
                        })

                        _get_all_steps(step)

                    else:
                        actual = step[0].text
                        expected = step[1].text \
                            if step.get('type') == 'ValidateStep' else ''

                        stepsList.append({
                            'type':'step',
                            'steps': (actual,expected)

                        })
                    
            _get_all_steps(steps)
                
        except TypeError:
            stepsList = []

        return stepsList

    def _try_delete_tags_from_string(self, s:str) -> str:
        result = ""
        if s:
            try:
                root = BeautifulSoup(s,'html.parser')
                for el in root.find_all(text=True):
                    result+=el.get_text()
                return result
            except: ...
        return s

    def _create_shared_steps_on_testit(self,api_testit:TestITAPI, shared_steps_id:Union[str,int], date_review:str) -> UUID:
        shared_steps_id = int(shared_steps_id) if type(shared_steps_id) is str else shared_steps_id
        
        shar_rps = self.api_tfs.get_work_item(shared_steps_id)['response']
        sharedsteps_data = {}
        sharedsteps_data['name'] = shar_rps['fields']['System.Title']
        sharedsteps_data['description'] = self._try_delete_tags_from_string(shar_rps['fields'].get('System.Description',''))
        _raw_steps = self._parse_steps(shar_rps['fields']['Microsoft.VSTS.TCM.Steps'])
        sharedsteps_data['priority'] =  self.tabPriority[shar_rps['fields'].get('Microsoft.VSTS.Common.Priority',2)]
        sharedsteps_data["tags"]= [
                {
                "name": "migrate"
                }
            ]
        
        sharedsteps_data['steps'] = []
        for step in _raw_steps:  
            sharedsteps_data['steps'].append(
                {
                    'action':step['steps'][0],
                    'expected':step['steps'][1]
                }
            )
    
        sharedsteps_data['links'] = [
            {
                'title': 'Ссылка на TFS',
                'url': f"{self.tfs_address}/{self.tfs_organization}/{self.tfs_project}/_workitems?id={shared_steps_id}&_a=edit",
                'description': 'link to tfs',
                'type': "Related",
                "hasInfo": True

            }
        ]
        _attr_unigue_shared_steps_tfs = {self.ID_attr_tfsid: str(shared_steps_id)}
        
        sharedsteps_data['attributes'] = {
                    self.ID_attr_date: date_review, **_attr_unigue_shared_steps_tfs}

        rps = api_testit.create_shared_steps(sharedsteps_data,_attr_unigue_shared_steps_tfs)
        return rps['id']

    def _load_content_test(self, id_plan:Union[str,int],suite_id:Union[str,int]) -> list:
        """Выгрузка тестов по набору тетстов из TFS

        Args:
            id_plan (Union[str,int]): ID плана
            suite_id (Union[str,int]): ID тестового набора

        Returns:
            list: Набор тестов
        """
        # logging.info(f"Plan ID: {id_plan} Suite ID: {suite_id}")
        testCaseIds = self.api_tfs.get_tests_from_suite(id_plan,suite_id)['response']['testCaseIds']
        tests = []
        for case in testCaseIds:
            caseId = case
            # aa = self.api_tfs.get_list_work_items(caseId)
            test = self.api_tfs.get_list_work_items(caseId)['response']['value'][0]
            fields = test['fields']

            relations = []
            for col in test.get('relations',[]):
                condition = any([res in col['rel'] for res in
                [
                    System.LinkTypes,
                    Microsoft_VSTS_Common.TestedBy_Reverse,
                    Microsoft_VSTS_Common.TestedBy_Forward
                ]])
                
                if condition:
                    url = col['url']
                    id_url = int(Path(url).stem)
                    element = self.api_tfs.get_work_item(id_url)['response']['fields']
                    tmp = dict()
                
                    tmp['title'] = f"{element[System.WorkItemType]}: {element[System.Title]}"
                    tmp['url'] = f"{self.tfs_address}/{self.tfs_organization}/{self.tfs_project}/_workitems?id={id_url}&_a=edit"
                    tmp['description'] = f"ID {element[System.WorkItemType]}: {id_url}"
                    tmp['type'] = "Related"
                    tmp['hasInfo'] = True
             
                    relations.append(tmp)
            

            stepsString = fields.get(Microsoft_VSTS_TCM.Steps,caseId)
            stepsString = stepsString if type(stepsString) is str else stepsString
            
            steps = self._parse_steps(stepsString,case_id=caseId)
            urlto = f"{self.tfs_address}/{self.tfs_organization}/{self.tfs_project}/_workitems?id={caseId}&_a=edit"
            description = self._try_delete_tags_from_string(fields.get('System.Description',''))
            test = {
                'id': str(caseId),
                'name':fields.get('System.Title'),
                'description':description,
                'steps':steps,
                'priority': fields.get(Microsoft_VSTS_Common.Priority,2),
                'link': [
                        {
                            'title': 'Ссылка на тест в TFS',
                            'url': urlto,
                            'description': f'ID тест: {caseId}',
                            'type': "Related",
                            "hasInfo": True

                        },*relations
            ]
            
                
            }

            tests.append(test)
        
        return tests

    def _get_tree_ids(self, id_plan:Union[str,int]):
        """Получить дерево сьюитов без тестов
        Args:
            id_plan (Union[str,int]): ID плана

        Returns:
            _type_: _description_
        """
        suitesTree = []
        root_id = id_plan

        rSuite = self.api_tfs.get_test_suites_from_plan(root_id)['response']
        allSuites = rSuite['testSuites']
        logging.info(f"Plan ID: {id_plan}")
        tq = tqdm(allSuites)
        for index, suite in enumerate(tq):
            suiteId = suite['id']
            tq.set_description(f'Обработка набора тестов № {suiteId}')
            suiteInfo = self.api_tfs.get_work_item(suiteId)['response']
            if suite.get('title') == '<root>':
                root_id = suiteId
                suite['title'] = suiteInfo['fields']['System.Title']
           
            childSuiteIds = suite['childSuiteIds']

            su = {
                'id': suiteId,
                'title': suite.get('title'),
                'desc': suiteInfo['fields'].get('System.Description'),
                'childIds': childSuiteIds,
                'type': TypesCollections.TYPE_SUITE,
                'tests':self._load_content_test(id_plan,suiteId)
            }
            if index == 0:
                testPlanInfo = su
    
            suitesTree.append(su)
            
        
        suiteIdsPre = []
        suiteIndexRoot = 0
        
        for index, st in enumerate(suitesTree):
            if st['id'] == root_id:
                suiteIdsPre = st['childIds']
                suiteIndexRoot = index
                break
        
    
        for index, suite_id in enumerate(suiteIdsPre):
            # Для внутреннего слоя
            self._recursive_nesting_traversal(
                suite_id, index, suitesTree, suitesTree, suiteIndexRoot)

        return suitesTree, testPlanInfo

    def _generate_tests(self,api:TestITAPI,section_id, test:dict, index:int, date_review:datetime):
        """Генерация тестов для представление их в API testit

        Args:
            api (TestITAPI): _description_
            section_id (_type_): _description_
            test (dict): _description_
            index (int): _description_
            date_review (datetime): _description_
        """
        Testit = api

        testdata = {}

        testdata['name'] = test.get('name', 'Неизвестный тест')
        testdata['description'] = test.get('description','')
        testdata['priority'] = self.tabPriority.get(test.get('priority',2))
        testdata['duration'] = 10000
        testdata['preconditionSteps'] = []
        testdata['postconditionSteps'] = []
        testdata['links'] = test['link']
        testdata["tags"]= [
                {
                "name": "migrate"
                }
            ]
        tfs_case_id = test.get('id')
        _attr_unigue = {self.ID_attr_tfsid: tfs_case_id}
        testdata['attributes'] = {
            self.ID_attr_date: date_review,
        
        }
        testdata['attributes'].update(_attr_unigue)

        testdata['steps'] = []
        for step in test['steps']:  
            if step.get('type') == 'step':
                testdata['steps'].append(
                    {
                        'action':step['steps'][0],
                        'expected':step['steps'][1]
                    }
                )
            elif step.get('type') == 'ref':
                tfs_shared_steps_id = step.get('ref')
                shar_id = self._create_shared_steps_on_testit(Testit, tfs_shared_steps_id,date_review)
                testdata['steps'].append(
                    {
                        'workItemId' : shar_id
                    }
                )
            
            

        Testit.create_test_case(testdata,_attr_unigue,parent_id=section_id)



    def migrate(self,plan_id:Union[str,int]):
        """Миграция тестов из TFS в TestIT

        Args:
            plan_id (Union[str,int]): ID плана

        Returns:
            _type_: Мигрированные тесты из tfs в testit по API
        """
        TestITAPI = self.api_testit
        jsonSuites, testPlanInfo = self._get_tree_ids(plan_id)

        TestITAPI.get_id_project_by_name('test')
        TestITAPI.get_id_sections_on_project()
        
        self.ID_attr_date = TestITAPI.create_attributes_on_project('Дата создания')
        self.ID_attr_tfsid = TestITAPI.create_attributes_on_project('TfsID')
        root_section = None

        date_now = datetime.now().strftime('%Y-%m-%d')
        
        def _recursive_fill_sections_and_tests(root_suites,root_section):
            

            for _, suite in enumerate(root_suites):
                current_section = TestITAPI.create_section_on_project(suite['title'],parent_id=root_section)
                tests = suite['tests']
                # if tests:
                #     cases = ET.SubElement(section,"cases")
                for index, test in enumerate(tests):
                    self._generate_tests(TestITAPI,current_section,test,index, date_now)
                    
                child_suite = suite['childIds']
                if child_suite:
                    _recursive_fill_sections_and_tests(child_suite,current_section)
                # for test in suite.get('tests',[]):
                #     Section.text = test['title']
                #     tree = ET.ElementTree(root)
        _recursive_fill_sections_and_tests(jsonSuites,root_section)
        


def migrate_tfs_to_testit(*args,plan_id):
        """_summary_

        Args:
            plan_id (_type_): Запуск миграции
        """
        apiTestIt = MigrateTfsToTest(*args)
        apiTestIt.migrate(plan_id)