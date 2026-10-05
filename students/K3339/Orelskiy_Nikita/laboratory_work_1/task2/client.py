import socket

SERVER_ADDRESS = ("localhost", 8082)
ENCODING = "utf-8"
TIMEOUT = 5


def ask_server(message):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(TIMEOUT)
    try:
        client_socket.connect(SERVER_ADDRESS)
        client_socket.sendall((message + "\n").encode(ENCODING, errors="replace"))
        with client_socket.makefile("r", encoding=ENCODING, errors="replace") as reader:
            return reader.readline().strip()
    except OSError:
        return ""
    finally:
        client_socket.close()


def main():
    print("Решение квадратного уравнения ax^2 + bx + c = 0")
    a = input("Введите a: ")
    b = input("Введите b: ")
    c = input("Введите c: ")

    answer = ask_server(f"{a} {b} {c}")
    if answer:
        print(f"Ответ сервера: {answer}")
    else:
        print("Не удалось получить ответ сервера")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nВвод прерван")
