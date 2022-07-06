from html import unescape, escape
import unicodedata

__all__ = []

def replacer(string:str)->str:
        """Функция для замены ненужных тэгов на аналогичные или альтернативные строки

        Args:
            string (str): Строка для замены

        Returns:
            str: Изменная строка
        """
        # TODO: У некоторых тестов не удаляются блоки тэгов
        # Например тест "Автоматическая активация без разрешения"
        replaceTo = {
            'DIV':('',''),
            'P': ('','\n'),
            'B':('',''),
            'BR':('br','\n')
        }
          
        listTagDelete = replaceTo.keys()
        for tag in listTagDelete:
            string = string.replace(f'<{tag}>',replaceTo[tag][0])
            string = string.replace(f'</{tag}>',replaceTo[tag][1])
            # for xml
            string = string.replace(f'<{tag}/>',replaceTo[tag][1])

        
        string = unescape(string)
        string = unicodedata.normalize('NFKC', string)
        # FIXME: &lt, &gt необходимы для экранирования, иначе ошибка построения xml файла
        # Нет смысла пытаться их убрать
        # string = string.replace(r"&lt;",'')
        # string = string.replace(r"&gt",'')
        # string = string.replace(r"&quot;",'')
        # FIXME: Если бы testIT поддерживал markdown - то можно было бы указать **
        return string
