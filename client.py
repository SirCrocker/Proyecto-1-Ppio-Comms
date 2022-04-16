import socket

HOST = "127.0.0.1"
PORT = 30000

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))

while True:
    data = sock.recv(1024)
    if data.decode() == "success":
        break
    print(f"[SERVER]: {data.decode()}")
    val = input("Message: ")
    sock.sendall(val.encode())


for i in range(5):
    val = input("Message: ")
    sock.sendall(val.encode())
    data = sock.recv(1024)
    print(f"Received: {data.decode()}")
sock.close()