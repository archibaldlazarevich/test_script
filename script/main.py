import argparse
import json
import logging
from argparse import Namespace
from datetime import date, datetime
from typing import TextIO

import tabulate


def check_files_not_empty(
    files: list[TextIO], parser_data: argparse.ArgumentParser
):
    """
    Метод для проверки  на то что передан пустой файл
    :param files: список файлов
    :param parser_data: парсер команды для скрипта
    :return:
    """
    for f in files:
        f.seek(0, 2)
        if f.tell() == 0:
            parser_data.error(f"Input file '{f.name}' is empty.")


def valid_date(date_str) -> date:
    """
    Метод для проверки формата даты
    :param date_str: дата, введеная при вызове скрипта
    :return:
    """
    try:
        return datetime.strptime(date_str, "%Y-%d-%m").date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Incorrect date format: '{date_str}'. "
            f"Expected format Y-d-m (ex. - 2025-22-06)."
        )


def create_parser():
    parser_init = argparse.ArgumentParser(
        description="log_to_output", add_help=True
    )
    parser_init.add_argument(
        "-f",
        "--file",
        help="using before log file name",
        required=True,
        nargs="+",
        type=argparse.FileType(mode="r", encoding="utf-8"),
    )

    parser_init.add_argument(
        "-r",
        "--report",
        help='type of report, you can use only "average"',
        required=True,
        choices=["average"],
        default="average",
    )

    parser_init.add_argument(
        "-d",
        "--date",
        help="parameter for generating a report "
        'for a specified date "Y-d-m" ex.: 2025-25-06 '
        "you can use only 1 date argument",
        nargs=1,
        type=valid_date,
    )
    return parser_init


def create_answer_aver_dict(dict_data: dict) -> dict:
    """
    Метод для создания словаря "average"
    :param dict_data: словарь с данными для обработки
    :return: конечные данные для вывода в консоль
    """
    for key, value in dict_data.items():
        dict_data[key] = {
            "count": len(value),
            "aver": round(sum(value) / len(value), 3),
        }
    sorted_data = dict(
        sorted(dict_data.items(), key=lambda x: x[1]["count"], reverse=True)
    )
    new_dict = {
        "": list(range(len(sorted_data))),
        "handler": list(sorted_data.keys()),
        "total": [c["count"] for c in sorted_data.values()],
        "avg_response_time": [c["aver"] for c in sorted_data.values()],
    }
    return new_dict


def create_report_with_date(date_data: date, file_list: list) -> dict | str:
    """
    Метод для обработки данных логов при наличии даты в команде к скрипту
    :param date_data: дата по которой будет происходить анализ данных
    :param file_list: список файлов, которые требуется обработать
    :return: конечные данные для вывода в консоль
    | сообщение о том, что данных на запрашиваемую дату нет в файлах
    """
    dict_init: dict = dict()
    for i in file_list:
        with open(i.name) as f:
            for line in f:
                try:
                    result = json.loads(line)
                    date_log = datetime.fromisoformat(
                        result.get("@timestamp")
                    ).date()
                    if date_log == date_data:
                        url = result.get("url")
                        if url in dict_init:
                            dict_init[url].append(result.get("response_time"))
                        else:
                            dict_init[url] = [result.get("response_time")]
                except json.JSONDecodeError as e:
                    logging.warning(f"JSON reading error in line: {e}")
                    continue
    if dict_init:
        return create_answer_aver_dict(dict_data=dict_init)
    else:
        return (
            f"No logs were found for the date"
            f' "{date_data.strftime('%Y-%m-%d')}".'
        )


def create_report_without_date(file_list: list) -> dict:
    """
    Метод для обработки данных логов при отсутствии даты в команде к скрипту
    :param file_list: список файлов, которые требуется обработать
    :return: конечные данные для вывода в консоль
    """
    dict_init: dict = dict()
    for i in file_list:
        with open(i.name) as f:
            for line in f:
                try:
                    result = json.loads(line)
                    url = result.get("url")
                    if url in dict_init:
                        dict_init[url].append(result.get("response_time"))
                    else:
                        dict_init[url] = [result.get("response_time")]
                except json.JSONDecodeError as e:
                    logging.warning(f"JSON reading error in line: {e}")
                    continue
    return create_answer_aver_dict(dict_data=dict_init)


def args_processing(args: Namespace) -> None:
    """
    Метод для обработки парсера команды к скрипту
    :param args: набор аргументов, передаваемых при вводе команды в консоль
    :return: результат обработки команды
    """
    if args.date:
        answer = create_report_with_date(
            date_data=args.date[0], file_list=args.file
        )
        date_info = (
            f"\nData for {datetime.strftime(args.date[0], '%Y-%m-%d')}."
        )
    else:
        answer = create_report_without_date(file_list=args.file)
        date_info = "\nAll-time data."
    if isinstance(answer, dict):
        print(date_info, end="\n\n")
        print(tabulate.tabulate(tabular_data=answer, headers="keys"))
    else:
        print(answer)


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    check_files_not_empty(files=args.file, parser_data=parser)
    args_processing(args=args)
