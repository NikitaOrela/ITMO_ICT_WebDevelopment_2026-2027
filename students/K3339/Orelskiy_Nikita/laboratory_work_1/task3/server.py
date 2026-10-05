import socket
from pathlib import Path

HOST = "localhost"
PORT = 8083
BUFFER_SIZE = 1024
MAX_REQUEST_SIZE = 65536
TIMEOUT = 2
HEADERS_END = b"\r\n\r\n"
PAGE_PATH = Path(__file__).resolve().parent / "index.html"
NOT_FOUND_PAGE = "<h1>404 Not Found</h1><p>Файл index.html не найден</p>"


def read_request(connection):
    data = b""
    try:
        while HEADERS_END not in data and len(data) < MAX_REQUEST_SIZE:
            chunk = connection.recv(BUFFER_SIZE)
            if not chunk:
                break
            data += chunk
    except socket.timeout:
        pass
    return data.decode("utf-8", errors="replace")


def load_page():
    try:
        return "200 OK", PAGE_PATH.read_bytes()
    except OSError:
        return "404 Not Found", NOT_FOUND_PAGE.encode("utf-8")


def build_response(status, body):
    headers = [
        f"HTTP/1.1 {status}",
        "Content-Type: text/html; charset=utf-8",
        f"Content-Length: {len(body)}",
        "Connection: close",
    ]
    head = "\r\n".join(headers) + "\r\n\r\n"
    return head.encode("utf-8") + body


def handle_client(connection, client_address):
    connection.settimeout(TIMEOUT)
    request = read_request(connection)
    if not request.strip():
        return
    request_line = request.splitlines()[0]
    print(f"Запрос от {client_address[0]}:{client_address[1]}: {request_line}")
    status, body = load_page()
    connection.sendall(build_response(status, body))
    print(f"Ответ: {status}, тело {len(body)} байт")


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
    print(f"HTTP-сервер запущен, откройте http://{HOST}:{PORT}")

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
