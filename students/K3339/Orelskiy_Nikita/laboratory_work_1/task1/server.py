import socket

HOST = "localhost"
PORT = 8081
BUFFER_SIZE = 1024
REPLY = "Hello, client"


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        server_socket.bind((HOST, PORT))
    except OSError as error:
        print(f"Не удалось занять порт {PORT}: {error}")
        server_socket.close()
        return
    print(f"UDP-сервер запущен на {HOST}:{PORT}")

    try:
        while True:
            try:
                data, client_address = server_socket.recvfrom(BUFFER_SIZE)
                message = data.decode("utf-8", errors="replace")
                sender = f"{client_address[0]}:{client_address[1]}"
                print(f"Сообщение от клиента {sender}: {message}")
                server_socket.sendto(REPLY.encode("utf-8"), client_address)
            except OSError as error:
                print(f"Ошибка обмена: {error}")
    except KeyboardInterrupt:
        print("\nСервер остановлен")
    finally:
        server_socket.close()


if __name__ == "__main__":
    main()
