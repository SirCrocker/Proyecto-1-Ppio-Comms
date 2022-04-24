import socket
import threading
import json

# Variables para hacer setup del servidor
HOST = "127.0.0.1"
PORT = 30000

# Variables auxiliares a usar
connections = [] # {getpeername(), Conexion()}
server_id = "Asistente"
users = []
t_lock = threading.Lock()


with open('data.json', 'r') as user_data:
    database_info = json.load(user_data)

def process_users(users_data):

    for user in users_data:
        user['solicitudes_activas'] = list(map(lambda request: Solicitud(**request), user['solicitudes_activas']))
        user['solicitudes_inactivas'] = list(map(lambda request: Solicitud(**request), user['solicitudes_inactivas']))
        users.append(Usuario(**user))


class Solicitud:

    def __init__(self, subject, open, history, number):
        self.subject = subject
        self.open = open
        self.history = history
        self.number = number

    def to_json(self):
        final_dict = {'number' : self.number,
                      'subject' : self.subject,
                      'state' : self.open,
                      'history' : self.history}
        return final_dict

class Usuario:

    def __init__(self, name, rut, solicitudes_activas, solicitudes_inactivas, is_executive = False):
        self.name = name # "Juan Carlos Bodoque"
        self.rut = rut # "3.333.333-3"
        self.is_executive = is_executive
        self.solicitudes_activas = solicitudes_activas
        self.solicitudes_inactivas = solicitudes_inactivas

    def to_json(self):
        active_requests = list(map(lambda request: request.to_json(), self.solicitudes_activas))
        inactive_requests = list(map(lambda request: request.to_json(), self.solicitudes_inactivas))

        final_dict = {'name' : self.name,
                      'rut' : self.rut,
                      'is_executive' : self.is_executive,
                      'solicitudes_activas' : active_requests,
                      'solicitudes_inactivas' : inactive_requests
                      }

        return final_dict

class Conexion:

    def __init__(self, user, socket_connection):
        self.peername = socket_connection.getpeername()
        self.user = user
        self.socket = socket_connection

def connection_(who):
    try:
        with who as s:

            s.sendall(f'Hola! Bienvenido {s.getpeername()}, Ingrese su RUT'.encode())

            # Autenticación
            while True:
                client_RUT = s.recv(2048).decode()

                if client_RUT == '4':
                    print("Usuario no identificado se desconectó.")
                    s.close()
                    return

                try:
                    t_lock.acquire()
                    client = list(filter(lambda x: x.rut == client_RUT, users))[0]
                    matching_connections = list(filter(lambda x: client == x.user, connections))
                    t_lock.release()

                    if len(matching_connections) != 0:
                        s.sendall(b'Asistente: Usuario ya se encuentra conectado.\n'
                                  b'Asistente: Si desea conectarse como otro usuario ingrese un nuevo rut\n'
                                  b'Asistente: Si desea desconectarse apriete 4.')
                    else:
                        client_connection = Conexion(client, s)

                        t_lock.acquire()
                        connections.append(client_connection)
                        t_lock.release()
                        break

                except IndexError:
                    s.sendall(b'Asistente: RUT invalido, vuelva a ingresar su RUT')

            # Usuario ya se encuentra autenticado
            print(f"{client.name} se conectó.")

            # Loop de ayuda/otro
            s.sendall(f"Bienvenido {client.name}, en que podemos ayudarle?\n"
                           f"\t (1) Revisar atenciones anteriores.\n"
                           f"\t (2) Contactar a un ejecutivo.\n"
                           f"\t (3) Reiniciar servicios.\n"
                           f"\t (4) Salir\n".encode())

            while True:
                data = who.recv(1024)
                if not data:
                    break

                if data.decode() == '4':
                    connections.remove(client_connection)
                    break

        print(f"{client.name.upper()} DISCONNECTED")

    except ConnectionResetError or BrokenPipeError as error:
        print(f"CLONTO DOSCONNOCTOD {error}")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((HOST, PORT))
sock.settimeout(0.5)
sock.listen()
print("Server started...")
process_users(database_info)
loop = True

try:
    while loop:
        try:
            conn, addr = sock.accept()
            new_t = threading.Thread(target=connection_, args=[conn])
            new_t.start()
        except TimeoutError:
            pass
        except BrokenPipeError or ConnectionResetError as datos:
            print(f"Someone disconnected :c\n{datos}")
        except:
            break

except:
    sock.close()

print("\b\bENDED")
