import socket
import threading

HOST = "127.0.0.1"
PORT = 30000

connections = []
users = ['1-1', '2-2']

def connection_(who):
    with who:
        print("Someone connected to server")
        while True:
            who.sendall(b"Who are you?")

            data = who.recv(1024)

            if data.decode() == users[0]:
                print("Client connected.")
                who.sendall(b"success")
                break
            elif data.decode() == users[1]:
                print("Executive connected.")
                who.sendall(b"success")
                break
            else:
                print("Unabled to identify, asking again...")
                who.sendall(b"Unabled to identify, asking again...")

        while True:
            data = who.recv(1024)
            if not data:
                break
            who.sendall(data)
    print("CLIENT DISCONNECTED")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((HOST, PORT))
sock.settimeout(0.5)
sock.listen()
print("Started server...")

loop = True

while loop:
    try:
        conn, addr = sock.accept()
        new_t = threading.Thread(target=connection_, args=[conn])
        new_t.start()
        connections.append(new_t)
    except TimeoutError:
        pass

    if len(connections) != 0:
        active = False

        for t in connections:
            # No es weno este codigo, hay que ir liberando información
            active = active or t.is_alive()
            loop = active

sock.close()
print("ENDED")
