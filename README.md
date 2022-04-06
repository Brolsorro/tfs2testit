Запуск 

```
python main.py
```

Установка зависимостей

```
Установка Python >=3.8
```
Для работы нужно переименовать и изменить конфиг `config_example.ini`

Пример конфига

```
# Rename config_example to config.ini
[Default]
pathToGisCert = None

[TFS Settings]
addressTFS = https:\\tfs.com
planTfsID = 80785  (ID Тестового плана!)
collectionName = Имя коллекции
projectName = Имя проекта в коллекции
tokenTfs = Токен PAT, для доступа к API TFS

[TestIT Settings]
# Если реализована функциальности импорта через API
addressTestIT = http:\\testit.com
tokenTestIT = Токен для доступа к API testit
```