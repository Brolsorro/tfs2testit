from libs.testit.api import TestITAPI
from libs.tfs.api import APITFS
from utils.string_converters import replacer
from typing import Union, List, Dict, Tuple
from datetime import datetime
from tqdm import tqdm
import xml.etree.ElementTree as ET

import logging



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
        case_id = kwargs.get('case_id','')
        logging.info(f'Обработка шагов теста № {case_id}')
        try:
            root = ET.fromstring(steps_string)
            steps = root
            stepsList = []
            for step in steps:
                actual = step[0].text
                expected = step[1].text \
                    if step.get('type') == 'ValidateStep' else ''
                
                stepsList.append((actual,expected))
        except TypeError:
            stepsList = []

        return stepsList

    def _load_content_test(self, id_plan:Union[str,int],suite_id:Union[str,int]) -> list:
        """Выгрузка тестов по набору тетстов

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
            test = self.api_tfs.get_work_item(caseId)['response']
            fields = test['fields']
            stepsString = fields.get('Microsoft.VSTS.TCM.Steps',caseId)
            stepsString = stepsString if type(stepsString) is str else stepsString
            steps = self._parse_steps(stepsString,case_id=caseId)
            urlto = f"{self.tfs_address}/{self.tfs_organization}/{self.tfs_project}/_workitems?id={caseId}&_a=edit"
            description = fields.get('System.Description')
            test = {
                'id': str(caseId),
                'name':fields.get('System.Title'),
                'description':description,
                'steps':steps,
                'priority': fields.get('Microsoft.VSTS.Common.Priority',''),
                'link': urlto
                
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
            else:
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
        testdata['priority'] = self.tabPriority.get(test.get('priority',''),'')
        testdata['duration'] = 10000
        testdata['preconditionSteps'] = []
        testdata['postconditionSteps'] = []
        testdata['links'] = [
            {
                'title': 'Ссылка на TFS',
                'url': test.get('link'),
                'description': 'link to tfs',
                'type': "Related",
                "hasInfo": True

            }
        ]
        testdata["tags"]= [
                {
                "name": "migrate"
                }
            ]
        _attr_unigue = {self.ID_attr_tfsid: test.get('id')}
        testdata['attributes'] = {
            self.ID_attr_date: date_review,
        
        }
        testdata['attributes'].update(_attr_unigue)

        testdata['steps'] = []
        for step in test['steps']:  
            testdata['steps'].append(
                {
                    'action':step[0],
                    'expected':step[1]
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
        root_section = TestITAPI.create_section_on_project(
            testPlanInfo.get('title'))


        date_now = datetime.now().strftime('%Y-%m-%d')
        
        logging.info(f"Convert created JSON to XML")
        def _recursive_fill_sections_and_tests(root_suites):
            
            
            for _, suite in enumerate(root_suites):
                current_section = TestITAPI.create_section_on_project(suite['title'],parent_id=root_section)

                tests = suite['tests']
                # if tests:
                #     cases = ET.SubElement(section,"cases")
                for index, test in enumerate(tests):
                    self._generate_tests(TestITAPI,current_section,test,index, date_now)
                    
                childIds = suite['childIds']
                if childIds:
                    _recursive_fill_sections_and_tests(childIds,current_section)
                # for test in suite.get('tests',[]):
                #     Section.text = test['title']
                #     tree = ET.ElementTree(root)

        _recursive_fill_sections_and_tests(jsonSuites)
        


def migrate_tfs_to_testit(*args,plan_id):
        """_summary_

        Args:
            plan_id (_type_): Запуск миграции
        """
        apiTestIt = MigrateTfsToTest(*args)
        apiTestIt.migrate(plan_id)