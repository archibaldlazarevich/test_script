import logging
from datetime import date

import pytest

from script.main import args_processing, check_files_not_empty, create_parser


def test_valid_date():
    """
    Тест для проверки работы скрипта на передачу даты
    :return:
    """
    parser = create_parser()
    args = parser.parse_args(
        ["-f", "tests/test.log", "-r", "average", "-d", "2025-22-06"]
    )
    assert args.date is not None
    assert args.date[0] == date(2025, 6, 22)


def test_not_valid_date():
    """
    Тест для проверки передачи невалидной даты
    :return:
    """

    parser = create_parser()
    with pytest.raises(SystemExit) as e:
        parser.parse_args(
            ["-f", "tests/test.log", "-r", "average", "-d", "2025-225-06"]
        )

    assert e.type == SystemExit
    assert e.value.code == 2


def test_without_date():
    """
    Тест для проверки на отсутствие даты
    :return:
    """
    parser = create_parser()
    args = parser.parse_args(["-f", "tests/test.log", "-r", "average"])
    assert args.date is None


def test_check_answer_with_date(capsys):
    """
    Тест для проверки данных при определенной дате
    :return:
    """
    parser = create_parser()
    args = parser.parse_args(
        ["-f", "tests/test.log", "-r", "average", "-d", "2025-23-06"]
    )
    args_processing(args)

    out = capsys.readouterr()
    assert "/api/context/..." in out.out
    assert "/api/homeworks/..." not in out.out
    assert "1" in out.out
    assert "0.024" in out.out
    assert "2025-06-23" in out.out


def test_check_answer_without_date(capsys):
    """
    Тест для проверки данных без даты
    :return:
    """
    parser = create_parser()
    args = parser.parse_args(["-f", "tests/test.log", "-r", "average"])
    args_processing(args)

    out = capsys.readouterr()
    assert "/api/context/..." in out.out
    assert "/api/homeworks/..." in out.out
    assert "All-time data." in out.out
    assert "2025-06-23" not in out.out


def test_check_file_arg():
    """
    Проверка на отсутствие переданного файла после команды -f
    :return:
    """
    parser = create_parser()
    with pytest.raises(SystemExit) as e:
        parser.parse_args(["-f", "-r", "average"])
    assert e.type == SystemExit
    assert e.value.code == 2


def test_with_double_file(tmp_path, capsys):
    """
    Проверка на передачу с несколькими файлами
    :return:
    """
    parser = create_parser()
    log_content_1 = (
        '{"@timestamp": "2025-06-23T13:57:32+00:00",'
        ' "status": 200, "url": "/api/context/...",'
        ' "request_method": "GET", "response_time": 0.024,'
        ' "http_user_agent": "..."}\n'
        '{"@timestamp": "2025-06-23T13:57:32+00:00",'
        ' "status": 200, "url": "/api/context/...",'
        ' "request_method": "GET", "response_time": 0.014,'
        ' "http_user_agent": "..."}\n'
    )

    log_file_1 = tmp_path / "test1.log"
    log_file_1.write_text(log_content_1, encoding="utf-8")
    log_content_2 = (
        '{"@timestamp": "2025-06-23T13:57:32+00:00",'
        ' "status": 200, "url": "/api/api/...",'
        ' "request_method": "GET", "response_time": 0.084,'
        ' "http_user_agent": "..."}\n'
        '{"@timestamp": "2025-06-23T13:57:32+00:00",'
        ' "status": 200, "url": "/api/api/...",'
        ' "request_method": "GET", "response_time": 0.074,'
        ' "http_user_agent": "..."}\n'
    )
    log_file_2 = tmp_path / "test2.log"
    log_file_2.write_text(log_content_2, encoding="utf-8")

    args = parser.parse_args(
        ["-f", str(log_file_1), str(log_file_2), "-r", "average"]
    )
    args_processing(args)
    out = capsys.readouterr()
    assert "0.019" in out.out
    assert "0.079" in out.out
    assert "/api/api/..." in out.out
    assert "/api/context/..." in out.out
    assert "2" in out.out


def test_check_report_without_argument():
    """
    Проверка на отсутствие аргумента после команды -r
    :return:
    """
    parser = create_parser()
    with pytest.raises(SystemExit) as e:
        parser.parse_args(["-f", "tests/test.log", "-r"])
    assert e.type == SystemExit
    assert e.value.code == 2


def test_check_an_empty_file(tmp_path):
    """
    Проверка на передачу пустого файла
    :return:
    """
    parser = create_parser()
    log_content = ""
    log_file = tmp_path / "test3.log"
    log_file.write_text(log_content, encoding="utf-8")
    with open(log_file, "r", encoding="utf-8") as f:
        with pytest.raises(SystemExit) as e:
            check_files_not_empty([f], parser=parser)
    assert e.type == SystemExit
    assert e.value.code == 2


def test_check_no_such_file():
    """
    Проверка на передачу несуществующего файла
    :return:
    """
    parser = create_parser()
    with pytest.raises(SystemExit) as e:
        parser.parse_args(["-f", "tests/test.lo", "-r"])
    assert e.type == SystemExit
    assert e.value.code == 2


def test_invalid_json_handling(caplog, tmp_path):
    """
    Проверка на некорректный json
    :param caplog:
    :param tmp_path:
    :return:
    """
    content = (
        '{"@timestamp": "2025-06-22T12:00:00+00:00", '
        '"url": "/test", "response_time": 0.1}\n'
        '{"@timestamp": "2025-06-23T12:00:00+00:00", '
        '"url": "/test", "response_time": 0.2\n'
    )

    log_file = tmp_path / "test_invalid.log"
    log_file.write_text(content, encoding="utf-8")

    parser = create_parser()
    args = parser.parse_args(["-f", str(log_file), "-r", "average"])
    with caplog.at_level(logging.WARNING):
        args_processing(args)

    assert any(
        "JSON reading error" in record.message for record in caplog.records
    )
