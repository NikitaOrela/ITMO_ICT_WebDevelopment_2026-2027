import socket

SERVER_ADDRESS = ("localhost", 8081)
BUFFER_SIZE = 1024
TIMEOUT = 3
MESSAGE = "Hello, server"


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(TIMEOUT)

    try:
        client_socket.sendto(MESSAGE.encode("utf-8"), SERVER_ADDRESS)
        data, _ = client_socket.recvfrom(BUFFER_SIZE)
        answer = data.decode("utf-8", errors="replace")
        print(f"Ответ сервера: {answer}")
    except (socket.timeout, ConnectionResetError):
        print("Сервер не отвечает")
    finally:
        client_socket.close()


if __name__ == "__main__":
    main()
