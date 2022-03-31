from importlib.resources import path
import json
import logging
from pickle import NONE

import xml.etree.ElementTree as ET


from libs.tfs.api import APITFS
from pathlib import Path
from typing import Union, List, Dict, Any, Tuple
from tqdm import tqdm
from xml.dom import minidom
from html import unescape
import unicodedata


class TypesCollections:
    TYPE_SUITE = 'suite'
    TYPE_TEST = 'test'

def writer_json(content,name='test'):
    open(f'{name}.json','w',encoding='utf-8').write(json.dumps(content,indent=4,ensure_ascii=False))

def writer_xml(root:ET.ElementTree,name='result',path_file:Path = None) -> None:
    """Запись xml в файл

    Args:
        root (ET.ElementTree): _description_
        name (str, optional): _description_. Defaults to 'result'.
    """
    if not path_file:
        path_file = Path(".") / 'exports'
    if not path_file.exists():
        path_file.mkdir()
        
    encoding = 'utf-8'
    content = minidom.parseString(ET.tostring(root,encoding=encoding)).toprettyxml(indent = "   ")
    open(path_file / f'{name}.xml','w',encoding=encoding).write(content)
    return

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

    def _replacer(self,string:str):
        
        # TODO: У некоторых тестов не удаляются блоки тэгов
        # Например тест "Автоматическая активация без разрешения"
        replaceTo = {
            'DIV':('',''),
            'P': ('','\n'),
            'B':('',''),
            'BR':('','\n')
        }
          
        listTagDelete = ['DIV','P','B','BR']
        for tag in listTagDelete:
            string = string.replace(f'<{tag}>',replaceTo[tag][0])
            
            string = string.replace(f'</{tag}>',replaceTo[tag][1])
            string = string.replace(f'<{tag}/>',replaceTo[tag][1])

        
        string = unescape(string)
        string = unicodedata.normalize('NFKC', string)
        # FIXME: &lt, &gt необходимы для экранирования, иначе ошибка построения xml файла
        # Нет смысла пытаться их убрать
        # string = string.replace(r"&lt;",'<')
        # string = string.replace(r"&gt",'>')
        # string = string.replace(r"&quot;",'"')
        # FIXME: Если бы testIT поддерживал markdown - то можно было бы указать **
        return string

    def recursive_nesting_traversal(self, suite_id, suite_index, suite_tree_static, suite_tree, suite_tree_index):

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
                self.recursive_nesting_traversal(
                    sub_child_id, sub_index, suite_tree_static, LINK_childIds, suite_index)
        del suite_tree_static[suiteMainIndex]
        return


    def _parse_steps(self,steps_string,**kwargs):
        case_id = kwargs.get('case_id','')
        # logging.info(f'Обработка шагов теста № {case_id}')
        try:
            root = ET.fromstring(steps_string)
            steps = root
            stepsList = []
            for step in steps:
                actual = self._replacer(step[0].text)
                expected = self._replacer(step[1].text) \
                    if step.get('type') == 'ValidateStep' else ''
                
                stepsList.append((actual,expected))
        except TypeError:
            stepsList = []

        return stepsList

    def _load_content_test(self, id_plan,suite_id):
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
                'name':fields.get('System.Title'),
                'steps':steps,
                'priority': fields.get('Microsoft.VSTS.Common.Priority','')
            }
            tests.append(test)
        
        return tests

    def get_tree_ids(self, id_plan):
        suitesTree = []
        root_id = id_plan

    
        # System.IterationPath
        rSuite = self.api.get_test_suites_from_plan(root_id)['response']
        allSuites = rSuite['testSuites']
        logging.info(f"Plan ID: {id_plan}")
        tq = tqdm(allSuites)
        for suite in tq:
            suiteId = suite['id']
            tq.set_description(f'Обработка набора тестов № {suiteId}')
            suiteInfo = self.api.get_work_item(suiteId)['response']
            if suite.get('title') == '<root>':
                root_id = suiteId
                suite['title'] = suiteInfo['fields']['System.Title']
           
            childSuiteIds = suite['childSuiteIds']

            
            suitesTree.append({
                'id': suiteId,
                'title': suite.get('title'),
                'desc': suiteInfo['fields'].get('System.Description'),
                'childIds': childSuiteIds,
                'type': TypesCollections.TYPE_SUITE,
                'tests':self._load_content_test(id_plan,suiteId)
            })
            

        suiteIdsPre = []
        suiteIndexRoot = 0
        
        for index, st in enumerate(suitesTree):
            if st['id'] == root_id:
                suiteIdsPre = st['childIds']
                suiteIndexRoot = index
                break
        
    
        for index, suite_id in enumerate(suiteIdsPre):
            # Для внутреннего слоя
            self.recursive_nesting_traversal(
                suite_id, index, suitesTree, suitesTree, suiteIndexRoot)

        return suitesTree

    def _generate_tests(self,cases:ET.SubElement, test:dict):
        case = ET.SubElement(cases,"case")
        title = ET.SubElement(case,"title")
        template = ET.SubElement(case,"template")
        typeT = ET.SubElement(case,"type")
        priority = ET.SubElement(case,"priority")
        estimate = ET.SubElement(case,"estimate")
        references = ET.SubElement(case,"references")
        custom1 = ET.SubElement(case,"custom")
        # custom2 = ET.SubElement(case,"custom")

        title.text = test.get('name', 'Неизвестный тест')
        steps_separated = ET.SubElement(custom1,'steps_separated')

        #TODO: На стороне testIT не реализованы ссылки!
        linkToUserStory = ET.SubElement(references,'reference',name="Ссылка на User Story")
        linkToUserStory.text = 'http://google.com'

        gettingPriority = test.get('priority','')
      
        priority.text = self.tabPriority.get(gettingPriority,'')

        for step in test['steps']:
            _step =  ET.SubElement(steps_separated,'step')
            content = ET.SubElement(_step,'content')
            expected = ET.SubElement(_step,'expected')
            content.text = step[0]
            expected.text = step[1]

    def convert_json_to_xml(self,plan_id):
        jsonSuites = self.get_tree_ids(plan_id)
        root = ET.Element('suite')
        
        logging.info(f"Convert created JSON to XML")
        def _recursive_generate_xml(root_suites,root_element):
            
            if root_suites:
                sections = ET.SubElement(root_element,"sections")
            
            for suite in root_suites:

                section = ET.SubElement(sections,"section")
                name = ET.SubElement(section,'name')
                name.text = str(suite['title'])
                description = ET.SubElement(section,'description')
                description.text = suite['desc']

                tests = suite['tests']
                if tests:
                    cases = ET.SubElement(section,"cases")
                for test in tests:
                    self._generate_tests(cases,test)
                    

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