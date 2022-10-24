# Описание
Утилита для переноса тестов из TFS в testIT через API или xml файл

Через API: D:\Projects\tfs_tests_migration\libs\testit\upload.py 

Через XML: D:\Projects\tfs_tests_migration\libs\tfs\converter.py

# Запуск (скомпилированного)
```
migration_tool.exe to-xml -i <ID-тест-плана> -pj <Название проекта> -ct <Название коллекции> -c Путь до сертификата, если нужен
(есть в tags)
```

# Запуск через исходники

```
python .\main.py to-xml -i <ID-тест-плана> -pj <Название проекта> -ct <Название коллекции> -c Путь до сертификата, если нужен
```

Установка зависимостей

```
Установка Python >=3.8
```
Для работы нужно переименовать и изменить конфиг `config_example.ini`

Пример конфига

```
# Rename config_example to config.ini
[TFS Settings]
addressTFS = https:\\tfs.com
tokenTfs = Токен PAT, для доступа к API TFS

[TestIT Settings]
# Не надо, пока не реализована функциальности импорта через API
addressTestIT = http:\\testit.com
tokenTestIT = Токен для доступа к API testit
```
