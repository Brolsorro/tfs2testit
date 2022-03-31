import configparser

from libs.tfs.api import APITFS
from libs.testit.api import TestITAPI
from libs.tfs.converter import TestsConverter
from libs.testit.upload import *

from pathlib import Path


ROOT_PATH = Path().absolute()

config = configparser.ConfigParser()
config.read('config.ini')

cert = config['Default'].get('pathToGisCert',None)

organization = config['TFS Settings']['collectionName']
project = config['TFS Settings']['projectName']
token = config['TFS Settings']['tokenTfs']
tokenTestIt = config['TestIT Settings']['tokenTestIT']
address_tfs = config['TFS Settings']['addressTFS']
address_testIt = config['TestIT Settings']['addressTestIT']
idPlan = 80785



api = APITFS(
    address_tfs,
    organization,
    project,
    token,
    cert
)



action = 'xml'

if action == 'xml':
    tsConv = TestsConverter(api)
    tsConv.convert_json_to_xml(idPlan)
    tsConv.write()
else:
    apiTestIt = TestITAPI(
    address_testIt,
    tokenTestIt,
    )
    a = apiTestIt.get_project_by_name('Тестовый')
    print(a)

