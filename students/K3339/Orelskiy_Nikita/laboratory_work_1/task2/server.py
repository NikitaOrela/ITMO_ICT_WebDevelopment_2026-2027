import math
import socket
from fractions import Fraction

HOST = "localhost"
PORT = 8082
ENCODING = "utf-8"
TIMEOUT = 3
MAX_MESSAGE_LENGTH = 200
MAX_NUMBER_LENGTH = 30
NOT_A_NUMBER = "коэффициенты должны быть числами в десятичной записи"


def format_number(value):
    if value == 0:
        value = 0.0
    return f"{value:.10g}"


def parse_number(text):
    digits = text.lstrip("+-").replace(".", "", 1)
    if not digits.isdecimal():
        raise ValueError(NOT_A_NUMBER)
    if len(text) > MAX_NUMBER_LENGTH:
        raise ValueError(f"число должно быть не длиннее {MAX_NUMBER_LENGTH} символов")
    try:
        return Fraction(text)
    except ValueError:
        raise ValueError(NOT_A_NUMBER) from None


def parse_coefficients(text):
    parts = text.replace(",", ".").split()
    if len(parts) != 3:
        raise ValueError("нужно передать три числа")
    return [parse_number(part) for part in parts]


def solve_quadratic(a, b, c):
    if a == 0:
        raise ValueError("коэффициент a не должен быть равен нулю")

    discriminant = b * b - 4 * a * c
    d_text = format_number(float(discriminant))
    if discriminant < 0:
        return f"D = {d_text}, действительных корней нет"
    if discriminant == 0:
        x = float(-b / (2 * a))
        return f"D = 0, x = {format_number(x)}"

    root = math.sqrt(discriminant)
    q = -(float(b) + math.copysign(root, b)) / 2
    x1 = q / float(a)
    x2 = float(c) / q
    if x1 > x2:
        x1, x2 = x2, x1
    return f"D = {d_text}, x1 = {format_number(x1)}, x2 = {format_number(x2)}"


def build_answer(text):
    try:
        a, b, c = parse_coefficients(text)
        return solve_quadratic(a, b, c)
    except ValueError as error:
        return f"Ошибка: {error}"


def handle_client(connection, client_address):
    connection.settimeout(TIMEOUT)
    print(f"Подключился клиент {client_address[0]}:{client_address[1]}")
    with connection.makefile("r", encoding=ENCODING, errors="replace") as reader:
        line = reader.readline(MAX_MESSAGE_LENGTH + 1)
    if not line:
        print("Клиент отключился, не прислав данные")
        return
    if len(line) > MAX_MESSAGE_LENGTH:
        answer = "Ошибка: сообщение слишком длинное"
    else:
        print(f"Получены коэффициенты: {line.strip()}")
        answer = build_answer(line)
    connection.sendall((answer + "\n").encode(ENCODING))
    print(f"Отправлен ответ: {answer}")


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((HOST, PORT))
    except OSError as error:
        print(f"Не удалось занять порт {PORT}: {error}")
        server_socket.close()
        return
    server_socket.listen(5)
    print(f"TCP-сервер запущен на {HOST}:{PORT}")

    try:
        while True:
            try:
                connection, client_address = server_socket.accept()
                with connection:
                    handle_client(connection, client_address)
            except OSError as error:
                print(f"Ошибка соединения: {error}")
    except KeyboardInterrupt:
        print("\nСервер остановлен")
    finally:
        server_socket.close()


if __name__ == "__main__":
    main()
