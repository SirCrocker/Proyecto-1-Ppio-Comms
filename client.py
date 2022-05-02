import socket
import sys
import threading

def main():

    # Prefix for the user
    user_prefix = "Yo"
    connection_ended = False

    HOST = "127.0.0.1"
    PORT = 30001

    print("\n[INFO] Conectandose al servidor...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    # Function that listens from server's messages, returns in case of an error
    def listen_to_server(s):

        while True:
            try:
                data = s.recv(1024).decode()
            except OSError:
                return

            if connection_ended or data == '':
                return

            print(data.replace('\nAsistente:', 'Asistente:').replace('Asistente:', '\nAsistente:'))

    # We start a thread that will listen for messages sent from the server
    listener = threading.Thread(target=listen_to_server, args=[sock])
    listener.start()

    for user_message in sys.stdin:
        clean_msg = user_message.rstrip()
        print('\b\033[1A' + '\033[K', end="\r")

        if clean_msg == '':
            continue

        print(f"{user_prefix}: {clean_msg}")

        if clean_msg != "":
            sock.sendall(clean_msg.encode())

        if clean_msg == "4" or not listener.is_alive():
            connection_ended = True
            print('\b\033[1A' + '\033[K', end="\r")
            break

    sock.close()

if __name__ == '__main__':
    main()
    print("Asistente: Gracias por contactarse con nosotros, que tenga un buen dia.")
    print("[INFO] Desconectado del servidor.\n")
