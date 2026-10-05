import socket
import threading
import time

HOST = "localhost"
PORT = 8084
ENCODING = "utf-8"
MAX_NAME_LENGTH = 20
MAX_LINE_LENGTH = 4096
JOIN_TIMEOUT = 2
EXIT_COMMAND = "/exit"

clients = {}
clients_lock = threading.Lock()
connections = set()
connections_lock = threading.Lock()
stopping = threading.Event()


def send_line(connection, text):
    connection.sendall((text + "\n").encode(ENCODING, errors="replace"))


def read_line(reader):
    line = reader.readline(MAX_LINE_LENGTH + 1)
    if len(line) > MAX_LINE_LENGTH:
        return ""
    return line


def broadcast(text, sender=None):
    with clients_lock:
        print(text)
        for connection in clients:
            if connection is sender:
                continue
            try:
                send_line(connection, text)
            except OSError:
                pass


def check_name(name):
    if not name:
        return "Имя не должно быть пустым"
    if len(name) > MAX_NAME_LENGTH:
        return f"Имя должно быть не длиннее {MAX_NAME_LENGTH} символов"
    if not name.isalnum():
        return "В имени допустимы только буквы и цифры"
    return None


def register(connection, reader, address):
    while True:
        line = read_line(reader)
        if not line:
            return None
        name = line.strip()
        problem = check_name(name)
        if problem is None:
            with clients_lock:
                if name not in clients.values():
                    others = ", ".join(clients.values())
                    send_line(connection, "OK")
                    if others:
                        send_line(connection, f"* Сейчас в чате: {others}")
                    else:
                        send_line(connection, "* Кроме вас в чате пока никого нет")
                    clients[connection] = name
                    print(f"Пользователь {name} подключился с адреса {address}")
                    return name
            problem = "Это имя уже занято"
        send_line(connection, problem)


def handle_client(connection, client_address):
    address = f"{client_address[0]}:{client_address[1]}"
    reader = connection.makefile("r", encoding=ENCODING, errors="replace", newline="\n")
    with connection, reader:
        try:
            name = register(connection, reader, address)
            if name is None:
                return
            broadcast(f"* Пользователь {name} вошёл в чат", sender=connection)
            while not stopping.is_set():
                line = read_line(reader)
                if not line:
                    break
                text = line.strip()
                if text == EXIT_COMMAND:
                    break
                if text:
                    broadcast(f"[{name}] {text}", sender=connection)
        except OSError:
            pass
        finally:
            with clients_lock:
                left_name = clients.pop(connection, None)
            if left_name is not None and not stopping.is_set():
                broadcast(f"* Пользователь {left_name} вышел из чата")
            with connections_lock:
                connections.discard(connection)


def close_all_connections():
    with connections_lock:
        open_connections = list(connections)
    for connection in open_connections:
        try:
            connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


def wait_for_threads():
    deadline = time.monotonic() + JOIN_TIMEOUT
    for thread in threading.enumerate():
        if thread is not threading.current_thread():
            thread.join(max(0, deadline - time.monotonic()))


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((HOST, PORT))
    except OSError as error:
        print(f"Не удалось занять порт {PORT}: {error}")
        server_socket.close()
        return
    server_socket.listen()
    print(f"Чат-сервер запущен на {HOST}:{PORT}")

    try:
        while True:
            try:
                connection, client_address = server_socket.accept()
            except OSError as error:
                print(f"Не удалось принять подключение: {error}")
                time.sleep(0.5)
                continue
            with connections_lock:
                connections.add(connection)
            thread = threading.Thread(
                target=handle_client, args=(connection, client_address), daemon=True
            )
            thread.start()
    except KeyboardInterrupt:
        print("\nСервер остановлен")
    finally:
        stopping.set()
        server_socket.close()
        close_all_connections()
        wait_for_threads()


if __name__ == "__main__":
    main()
