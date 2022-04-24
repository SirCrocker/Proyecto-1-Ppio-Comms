import socket
import sys
import threading

# Prefix for the user
user_prefix = "ME"
server_prefix = "Asistente"

def main():
    HOST = "127.0.0.1"
    PORT = 30000

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    # Function that listens from server's messages, returns in case of an error
    def listen_to_server(sock):

        while True:
            try:
                data = sock.recv(1024).decode()
            except OSError:
                return
            print(data)

    # We start a thread that will listen for messages sent from the server
    listener = threading.Thread(target=listen_to_server, args=[sock])
    listener.start()

    for user_message in sys.stdin:
        clean_msg = user_message.rstrip()
        print('\b\033[1A' + '\033[K', end="\r")
        print(f"{user_prefix}: {clean_msg}")

        if clean_msg != "":
            sock.sendall(clean_msg.encode())

        if clean_msg == "4":
            break

    sock.close()

if __name__ == '__main__':
    main()
    print("Disconnected from server.")
