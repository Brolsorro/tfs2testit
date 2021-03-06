import configparser
import logging


from libs.tfs.api import APITFS
from libs.testit.api import TestITAPI
from libs.tfs.converter import TestsConverter
from libs.testit.upload import *
from utils.command_line import getCommandLine
from pathlib import Path


ROOT_PATH = Path().absolute()
EXAMPLE_CONFIG_TEXT = """
Например,
[TFS Settings]
addressTFS = https:\\tfs.com
tokenTfs = Токен PAT, для доступа к API TFS
"""

CONFIG_PATH = ROOT_PATH / 'config.ini'
if not CONFIG_PATH.exists():
    logging.error(f'Создайте и настройте файл config.ini\nПуть поиска: {CONFIG_PATH}\n{EXAMPLE_CONFIG_TEXT}')
    raise SystemExit(1)


if __name__ == '__main__':
    options = getCommandLine()
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    try:
        if options.action == 'to-xml':
            address_tfs = config['TFS Settings']['addressTFS']
            tokenTfs = config['TFS Settings']['tokenTfs']
            
        if options.action == 'to-api':
            tokenTestIt = config['TestIT Settings']['tokenTestIT']
            address_testIt = config['TestIT Settings']['addressTestIT']
    except KeyError as e:
        logging.error(f'Не указан параметр в конфиге {e}\n')

    if options.action == 'to-xml':
        organization = options.collection
        project = options.project
        cert = options.cert
        api = APITFS(
            address_tfs,
            organization,
            project,
            tokenTfs,
            cert
        )
        idPlan = options.id
        tsConv = TestsConverter(api)
        tsConv.convert_json_to_xml(idPlan)
        tsConv.write()

    if options.action == 'to-api':
        apiTestIt = TestITAPI(
        address_testIt,
        tokenTestIt,
        )
        b = apiTestIt.get_project_by_name('test')
        sections = apiTestIt.get_sections_on_project(b['id'])
        # a = apiTestIt.create_test_suite()
        a = apiTestIt.create_test_case()
        print(a)
        ...
