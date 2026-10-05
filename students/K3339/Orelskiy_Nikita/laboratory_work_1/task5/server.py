import socket
from html import escape
from urllib.parse import parse_qs, urlsplit

HOST = "localhost"
PORT = 8085
SERVER_NAME = "grades-journal"
TIMEOUT = 2
MAX_LINE = 65536
MAX_HEADERS = 100
MAX_BODY = 65536
MAX_DISCIPLINE_LENGTH = 100
GRADES = ("1", "2", "3", "4", "5")
FORM_TYPE = "application/x-www-form-urlencoded"

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 720px;
            margin: 40px auto;
            padding: 0 20px;
        }
        form {
            margin-bottom: 24px;
        }
        input, button {
            padding: 6px 10px;
            font-size: 16px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
        }
        th, td {
            border: 1px solid lightgray;
            padding: 8px 12px;
            text-align: left;
        }
        th {
            background-color: whitesmoke;
        }
    </style>
</head>
<body>
    <h1>{title}</h1>
    {content}
</body>
</html>
"""

FORM = """<form method="post" action="/">
        <label>Дисциплина
            <input type="text" name="discipline" maxlength="100" required>
        </label>
        <label>Оценка
            <input type="number" name="grade" min="1" max="5" required>
        </label>
        <button type="submit">Добавить</button>
    </form>"""

BACK_LINK = '<p><a href="/">Вернуться к журналу</a></p>'


class Request:
    def __init__(self, method, path, params, headers, body):
        self.method = method
        self.path = path
        self.params = params
        self.headers = headers
        self.body = body


class Response:
    def __init__(self, status, reason, body="", headers=None):
        self.status = status
        self.reason = reason
        self.body = body.encode("utf-8")
        self.headers = headers or []


class HTTPError(Exception):
    def __init__(self, status, reason, message, headers=None):
        super().__init__(message)
        self.status = status
        self.reason = reason
        self.message = message
        self.headers = headers


def bad_request(message):
    return HTTPError(400, "Bad Request", message)


def render_page(title, content):
    return PAGE_TEMPLATE.replace("{title}", title).replace("{content}", content)


class MyHTTPServer:
    def __init__(self, host, port, name):
        self.host = host
        self.port = port
        self.name = name
        self.journal = {}

    def serve_forever(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server_socket.bind((self.host, self.port))
        except OSError as error:
            print(f"Не удалось занять порт {self.port}: {error}")
            server_socket.close()
            return
        server_socket.listen(5)
        address = f"http://{self.host}:{self.port}"
        print(f"Сервер {self.name} запущен, откройте {address}")

        try:
            while True:
                try:
                    connection, _ = server_socket.accept()
                    self.serve_client(connection)
                except Exception as error:
                    print(f"Ошибка при обработке запроса: {error}")
        finally:
            server_socket.close()

    def serve_client(self, connection):
        with connection:
            connection.settimeout(TIMEOUT)
            request = None
            try:
                request = self.parse_request(connection)
                if request is None:
                    return
                response = self.handle_request(request)
            except HTTPError as error:
                response = self.make_error_response(error)
            except socket.timeout:
                error = HTTPError(408, "Request Timeout", "Запрос не получен целиком")
                response = self.make_error_response(error)
            self.send_response(connection, response)
            target = "Неразобранный запрос"
            if request is not None:
                target = f"{request.method} {request.path}"
            print(f"{target} -> {response.status} {response.reason}")

    def parse_request(self, connection):
        with connection.makefile("rb") as reader:
            try:
                raw_line = reader.readline(MAX_LINE + 1)
            except socket.timeout:
                return None
            if not raw_line.strip():
                return None
            if len(raw_line) > MAX_LINE:
                raise bad_request("Первая строка запроса слишком длинная")
            parts = raw_line.decode("utf-8", errors="replace").split()
            if len(parts) != 3:
                raise bad_request("Неверная первая строка запроса")
            method, target, version = parts
            if not version.startswith("HTTP/"):
                raise bad_request("Неверная версия протокола в запросе")
            try:
                url = urlsplit(target)
            except ValueError:
                raise bad_request("Неверный адрес в запросе") from None
            params = parse_qs(url.query, keep_blank_values=True)
            headers = self.parse_headers(reader)
            body = self.read_body(reader, headers)
            return Request(method, url.path, params, headers, body)

    def parse_headers(self, reader):
        headers = {}
        for _ in range(MAX_HEADERS + 1):
            raw_line = reader.readline(MAX_LINE + 1)
            if len(raw_line) > MAX_LINE:
                raise bad_request("Слишком длинный заголовок запроса")
            if raw_line in (b"\r\n", b"\n", b""):
                return headers
            line = raw_line.decode("utf-8", errors="replace")
            name, separator, value = line.partition(":")
            if not separator:
                raise bad_request("Неверный заголовок запроса")
            headers[name.strip().lower()] = value.strip()
        raise bad_request("Слишком много заголовков в запросе")

    def read_body(self, reader, headers):
        try:
            length = int(headers.get("content-length", "0"))
        except ValueError:
            length = -1
        if not 0 <= length <= MAX_BODY:
            raise bad_request("Неверный заголовок Content-Length")
        return reader.read(length)

    def handle_request(self, request):
        if request.path != "/":
            raise HTTPError(404, "Not Found", "Такой страницы нет")
        if request.method == "GET":
            return Response(200, "OK", self.render_journal())
        if request.method == "POST":
            params = dict(request.params)
            params.update(self.parse_form(request))
            self.add_grade(params)
            return Response(303, "See Other", "Оценка записана\n", [("Location", "/")])
        raise HTTPError(
            405,
            "Method Not Allowed",
            "Сервер принимает только GET и POST",
            [("Allow", "GET, POST")],
        )

    def parse_form(self, request):
        if not request.body:
            return {}
        content_type = request.headers.get("content-type", FORM_TYPE).lower()
        if not content_type.startswith(FORM_TYPE):
            message = f"Сервер принимает только данные формы {FORM_TYPE}"
            raise HTTPError(415, "Unsupported Media Type", message)
        text = request.body.decode("utf-8", errors="replace")
        return parse_qs(text, keep_blank_values=True)

    def add_grade(self, params):
        discipline = " ".join(params.get("discipline", [""])[0].split())
        grade = params.get("grade", [""])[0].strip()
        if not discipline:
            raise bad_request("Не указана дисциплина, нужны поля discipline и grade")
        if len(discipline) > MAX_DISCIPLINE_LENGTH:
            raise bad_request("Слишком длинное название дисциплины")
        if grade not in GRADES:
            raise bad_request("Оценка должна быть целым числом от 1 до 5")
        key = discipline.casefold()
        if key not in self.journal:
            self.journal[key] = {"name": discipline, "grades": []}
        record = self.journal[key]
        record["grades"].append(int(grade))
        print(f"Записана оценка {grade}, дисциплина {record['name']}")

    def render_journal(self):
        rows = ""
        for record in self.journal.values():
            grades = ", ".join(str(grade) for grade in record["grades"])
            rows += f"<tr><td>{escape(record['name'])}</td><td>{grades}</td></tr>"
        if rows:
            header = "<tr><th>Дисциплина</th><th>Оценки</th></tr>"
            content = f"<table>{header}{rows}</table>"
        else:
            content = "<p>Оценок пока нет</p>"
        return render_page("Журнал оценок", FORM + "\n    " + content)

    def make_error_response(self, error):
        title = f"{error.status} {error.reason}"
        content = f"<p>{escape(error.message)}</p>\n    {BACK_LINK}"
        page = render_page(title, content)
        return Response(error.status, error.reason, page, error.headers)

    def send_response(self, connection, response):
        headers = [
            ("Server", self.name),
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(response.body))),
            ("Connection", "close"),
        ] + response.headers
        lines = [f"HTTP/1.1 {response.status} {response.reason}"]
        lines += [f"{name}: {value}" for name, value in headers]
        head = "\r\n".join(lines) + "\r\n\r\n"
        connection.sendall(head.encode("utf-8") + response.body)


if __name__ == "__main__":
    server = MyHTTPServer(HOST, PORT, SERVER_NAME)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен")
