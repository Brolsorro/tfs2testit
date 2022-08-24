import argparse
from pathlib import Path

def getCommandLine() -> argparse.ArgumentParser:
    """Получить агрументы коммандной строки

    Returns:
        argparse.ArgumentParser: _description_
    """
    parser = argparse.ArgumentParser(description='Конвертация тестов с TFS в xml формат Testrail/TestIT')
    action = parser.add_subparsers(dest='action', required=True)
    subparser = action.add_parser('to-xml',help='Скачивание и конвертация тестов с TFS в xml',add_help=False)
    subparser.add_argument('-i','--id',type=int,required=True,help='ID тест плана')
    subparser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                    help='Показывает команды для конверта в xml')
    subparser.add_argument('--project','-pj',required=True, type=str,help='Название проекта в коллекции')
    subparser.add_argument('--collection','-ct',required=True,type=str,help='Название коллекции')
    subparser.add_argument('--cert','-c',required=False,type=Path,help='Сертификат для доступа к TFS',default=None)

    subparser = action.add_parser('to-api',help='Скачивание и конвертация тестов с TFS и доставка по API в TestIT',add_help=False)
    subparser.add_argument('-i','--id',type=int,required=True,help='ID тест плана')
    subparser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                    help='Показывает команды для конверта в api')
    subparser.add_argument('--project','-pj',required=True, type=str,help='Название проекта в коллекции')
    subparser.add_argument('--collection','-ct',required=True,type=str,help='Название коллекции')
    subparser.add_argument('--cert','-c',required=False,type=Path,help='Сертификат для доступа к TFS',default=None)

                    
    return parser.parse_args()