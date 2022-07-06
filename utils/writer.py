import json
import xml.etree.ElementTree as ET

from xml.etree.ElementTree import ElementTree
from pathlib import Path
from xml.dom import minidom




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
        
    # content = minidom.parseString(ET.tostring(root,encoding=encoding)).toprettyxml(indent = "   ")
    # open(path_file / f'{name}.xml','w',encoding=encoding).write(content)
    ElementTree(root).write(path_file / f'{name}.xml', xml_declaration=True, encoding='UTF-8')
    return