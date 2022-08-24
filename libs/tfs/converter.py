import logging
import xml.etree.ElementTree as ET


from libs.tfs.api import APITFS
from utils.string_converters import replacer
from utils.writer import writer_xml
from typing import Union, List, Dict, Tuple
from datetime import datetime
from tqdm import tqdm
from html import escape



class TypesCollections:
    TYPE_SUITE = 'suite'
    TYPE_TEST = 'test'


class TestsConverter:
    def __init__(self, api:APITFS) -> None:
        self.api = api
        self.tabPriority = {
            1:'Critical',
            2:'High',
            3:'Medium',
            4:'Low'
        }
        self.readyForWrite:ET.ElementTree = None

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

        LINK_childIds = TestsConverter._get_link_mutable_object(
            suite_tree, (suite_tree_index, 'childIds'))
        LINK_childIds[suite_index] = suite_tree_static[suiteMainIndex]

        LINK_subChildIds = TestsConverter._get_link_mutable_object(
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
        # logging.info(f'Обработка шагов теста № {case_id}')
        try:
            root = ET.fromstring(steps_string)
            steps = root
            stepsList = []
            for step in steps:
                actual = replacer(step[0].text)
                expected = replacer(step[1].text) \
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
        testCaseIds = self.api.get_tests_from_suite(id_plan,suite_id)['response']['testCaseIds']
        tests = []
        for case in testCaseIds:
            caseId = case
            test = self.api.get_work_item(caseId)['response']
            fields = test['fields']
            stepsString = fields.get('Microsoft.VSTS.TCM.Steps',caseId)
            stepsString = stepsString if type(stepsString) is str else stepsString
            steps = self._parse_steps(stepsString,case_id=caseId)
            test = {
                'id': str(caseId),
                'name':fields.get('System.Title'),
                'steps':steps,
                'priority': fields.get('Microsoft.VSTS.Common.Priority',''),
                'link': test['url']
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

        rSuite = self.api.get_test_suites_from_plan(root_id)['response']
        allSuites = rSuite['testSuites']
        logging.info(f"Plan ID: {id_plan}")
        tq = tqdm(allSuites)
        for index, suite in enumerate(tq):
            suiteId = suite['id']
            tq.set_description(f'Обработка набора тестов № {suiteId}')
            suiteInfo = self.api.get_work_item(suiteId)['response']
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

    def _generate_tests(self,cases:ET.SubElement, test:dict, index:int, date_review:datetime):
        """Генерация тестов для представление их в XML

        Args:
            cases (ET.SubElement): Ссылка на размещение теста в XML коллекции
            test (dict): Непреобразованный тест
        """
        
        case = ET.SubElement(cases,"case")
        _id = ET.SubElement(case,"id")
        _id.text = test.get('id')
        title = ET.SubElement(case,"title")
        template = ET.SubElement(case,"template")
        template.text = 'Test Case (Steps)'
        typeT = ET.SubElement(case,"type")
        typeT.text = 'Usability'
        priority = ET.SubElement(case,"priority")
        estimate = ET.SubElement(case,"estimate")
        estimate.text = "1000"
        references = ET.SubElement(case,"references")
        custom1 = ET.SubElement(case,"custom")
        # custom2 = ET.SubElement(case,"custom")

        title.text = test.get('name', 'Неизвестный тест')

        review_date = ET.SubElement(custom1,'review_date')
        review_date.text = date_review
        steps_separated = ET.SubElement(custom1,'steps_separated')

        #TODO: На стороне testIT не реализованы ссылки!
        # linkToUserStory = ET.SubElement(references,'reference',name="Ссылка на User Story")
        # linkToUserStory = ET.SubElement(references,'reference')
        # linkToUserStory.text = 'http://google.com'
        references.text = test.get('link')

        gettingPriority = test.get('priority','')
      
        priority.text = self.tabPriority.get(gettingPriority,'')

        for step in test['steps']:
            _step =  ET.SubElement(steps_separated,'step')
            ET.SubElement(_step,"index").text = str(index+1)
            content = ET.SubElement(_step,'content')
            expected = ET.SubElement(_step,'expected')
            content.text = escape(step[0])
            expected.text = step[1]

    def convert_json_to_xml(self,plan_id:Union[str,int]):
        """Преобразование словаря в XML

        Args:
            plan_id (Union[str,int]): ID плана

        Returns:
            _type_: Готовая XML коллекция для записи в файл
        """
        jsonSuites, testPlanInfo = self._get_tree_ids(plan_id)
        root = ET.Element('suite')
        # ET.SubElement(root,'id').text = str(testPlanInfo.get('id'))
        ET.SubElement(root,'id').text = str(plan_id)
        ET.SubElement(root,'name').text = testPlanInfo.get('title')
        ET.SubElement(root,'description').text = f"Test Plan ID: {plan_id}"

        date_now = datetime.now().strftime('%Y-%m-%d')
        
        logging.info(f"Convert created JSON to XML")
        def _recursive_generate_xml(root_suites,root_element):
            
            if root_suites:
                sections = ET.SubElement(root,"sections")
            
            for numb, suite in enumerate(root_suites):
                section = ET.SubElement(sections,"section")
                name = ET.SubElement(section,'name')
                name.text = str(suite['title'])
                description = ET.SubElement(section,'description')
                description.text = f"Description: {suite['desc']}"

                tests = suite['tests']
                if tests:
                    cases = ET.SubElement(section,"cases")
                for index, test in enumerate(tests):
                    self._generate_tests(cases,test,index, date_now)
                    

                childIds = suite['childIds']
                if childIds:
                    _recursive_generate_xml(childIds,section)
                # for test in suite.get('tests',[]):
                #     Section.text = test['title']
                #     tree = ET.ElementTree(root)
            return root_element

        self.readyForWrite = _recursive_generate_xml(jsonSuites, root)
        
        return self.readyForWrite
        
        
        # ET.indent(tree, space=" ", level=0)
    def write(self,name='result'):
        logging.info(f"Saving XML")
        writer_xml(self.readyForWrite,name)