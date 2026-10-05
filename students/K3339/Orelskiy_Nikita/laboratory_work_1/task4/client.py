import socket
import sys
import threading

SERVER_ADDRESS = ("localhost", 8084)
ENCODING = "utf-8"
JOIN_TIMEOUT = 2
EXIT_COMMAND = "/exit"


def send_line(connection, text):
    connection.sendall((text + "\n").encode(ENCODING, errors="replace"))


def read_line(prompt=""):
    if prompt:
        print(prompt, end="", flush=True)
    line = sys.stdin.readline()
    if not line:
        raise EOFError
    return line.strip()


def register(connection, reader):
    while True:
        name = read_line("Введите имя: ")
        if name == EXIT_COMMAND:
            return None
        send_line(connection, name)
        reply = reader.readline().strip()
        if reply == "OK":
            return name
        if not reply:
            print("Сервер закрыл соединение")
            return None
        print(reply)


def receive_messages(reader, stopped):
    try:
        for line in reader:
            if stopped.is_set():
                break
            print(line.rstrip("\n"))
    except (OSError, ValueError):
        pass
    if not stopped.is_set():
        stopped.set()
        print("Соединение с сервером закрыто, нажмите Enter для выхода")


def chat(connection, stopped):
    while not stopped.is_set():
        text = read_line()
        if stopped.is_set():
            break
        if text == EXIT_COMMAND:
            stopped.set()
            send_line(connection, EXIT_COMMAND)
            break
        if text:
            send_line(connection, text)


def main():
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        connection.connect(SERVER_ADDRESS)
    except OSError:
        print("Не удалось подключиться к серверу")
        connection.close()
        return

    reader = connection.makefile("r", encoding=ENCODING, errors="replace", newline="\n")
    stopped = threading.Event()
    receiver = threading.Thread(
        target=receive_messages, args=(reader, stopped), daemon=True
    )
    joined = False
    try:
        name = register(connection, reader)
        if name is None:
            return
        print(f"Вы вошли в чат как {name}. Для выхода введите {EXIT_COMMAND}")
        joined = True
        receiver.start()
        chat(connection, stopped)
    except (KeyboardInterrupt, EOFError):
        stopped.set()
        print()
    except OSError:
        print("Соединение с сервером потеряно")
    finally:
        stopped.set()
        try:
            connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        if receiver.is_alive():
            receiver.join(JOIN_TIMEOUT)
        connection.close()
        if joined:
            print("Вы вышли из чата")


if __name__ == "__main__":
    main()
