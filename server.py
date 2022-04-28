import socket
import threading
import json
from custom_classes import *

# Variables para hacer setup del servidor, se usa localhost y el puerto 30000
HOST = "127.0.0.1"
PORT = 30000

# Variables auxiliares a usar:
# Lista con las conexiones actuales al servidor, de tipo _Conexion_
connections = []

# Lista con los clientes existentes en la "base de datos", son de tipo _Usuario_ y aunque no es lo más
# eficiente cumple con lo necesitado.
clients = []

# Lista con los ejecutivos existentes en la "base de datos", son de tipo _Usuario_ y aunque no es lo más
# eficiente cumple con lo necesitado.
execs = []

# Ejecutivos disponibles
available_execs = []

# Nombre del servidor que será mostrado al usuario cuando hable con este
server_id = "Asistente"

# Variable con la cual se podrán bloquear variables cuando se accederán a estas, evitando comportamientos imprevistos.
threading_lock = threading.Lock()


# Función que lee el archivo .json con los usuarios y crea un objeto _Usuario_ para cada uno
# y luego lo agrega a la lista.
def process_users():
    with open('users.json', 'r') as user_data:  # Abrimos y leemos el archivo
        database_users = json.load(user_data)

    for user in database_users:  # Le damos el formato a solicitudes activas, inactivas y creamos y agregamos el usuario
        user['solicitudes_activas'] = list(map(lambda request: Solicitud(**request), user['solicitudes_activas']))
        user['solicitudes_inactivas'] = list(map(lambda request: Solicitud(**request), user['solicitudes_inactivas']))
        if user['is_executive']:
            execs.append(Usuario(**user))
        else:
            clients.append(Usuario(**user))

# Interpreta el mensaje del usuario y entrega su intención
def interpret_user_input(user_msg):
    return 0

def exec_loop(conn, client):
    conn.sendall(b'Eres un ejecutivo. Adios.')


# client_loop: loop en donde se encuentran los usuarios correspondientes a clientes
#
# PARAMS:
#   conn: objeto tipo socket que caracteriza al cliente
#   client: objeto tipo Usuario que caracteriza al usuario
def client_loop(conn, client):
    # Loop de ayuda/otro
            conn.sendall(f"Bienvenido {client.name}, en que podemos ayudarle?\n"
                      f"\t (1) Revisar atenciones anteriores.\n"
                      f"\t (2) Contactar a un ejecutivo.\n"
                      f"\t (3) Reiniciar servicios.\n"
                      f"\t (4) Salir\n".encode())

            while True:
                data = conn.recv(1024)

                if not data:
                    break

                data = data.decode()

                intencion = interpret_user_input(data)

                if data == "1" or intencion == 'historial':
                    if len(client.solicitudes_activas) == 0:
                        conn.sendall(b'No posee solicitudes activas.')
                    else:

                        message = 'Asistente: Usted tiene las siguientes solicitudes en curso:'
                        local_number = 1

                        for solicitud in client.solicitudes_activas:
                            message = message + f'\n\t ({local_number}) ' + str(solicitud)
                            local_number += 1
                        message += '\nAsistente: ¿Que solicitud desea consultar?'
                        conn.sendall(message.encode())
                        chosen_order = conn.recv(1024).decode()

                        if chosen_order.isalnum():
                            solicitud = client.solicitudes_activas[int(chosen_order) - 1]
                            conn.sendall(f'Asistente: {solicitud.history[-1]}'.encode())


                if data == "2" or intencion == 'ejecutivo':
                    conn.sendall("Asistente: [DEBUG] EJECUTIVO".encode())

                if data == "3" or intencion == 'reiniciar':
                    conn.sendall("Asistente: Se ha reiniciado su modem.\n"
                                 "Asistente: Como más podemos ayudarle?".encode())
                    print(f"[INFO] Se ha reiniciado el modem del cliente {client.name}.")
                    client.solicitudes_inactivas.append( Solicitud("reinicio modem",
                                                                   False,
                                                                   [],
                                                                   len(client.solicitudes_inactivas) + 1) )

                if data == "4" or intencion == 'despedida':
                    conn.sendall("Asistente: [DEBUG] DESPEDIDA".encode())
                    break

            # Guardamos la data
            old_user = list(filter(lambda x: x.rut == client.rut, clients))
            if len(old_user) != 0:
                clients.remove(old_user[0])
                clients.append(client)

# Función encargada de manejar las conexiones
def connection_(who):

    client_connection = None

    try:
        with who as s:

            # -------------------------------------------------------------------------------------------------------- #
            # Bienvenida
            s.sendall(f'Hola! Bienvenide, ingrese su RUT'.encode())

            # -------------------------------------------------------------------------------------------------------- #
            # Autenticación
            while True:
                client_RUT = s.recv(2048).decode()

                # TODO: Implementar correctamente NLP / RUT
                intencion = interpret_user_input(client_RUT)

                if client_RUT.lower() in ('4', 'chao', 'bye', 'no') or intencion == 'despedida':
                    print("Usuario no identificado se desconectó.")
                    s.close()
                    return

                try:
                    with threading_lock:
                        user = list(filter(lambda x: x.rut == client_RUT, clients + execs))[0]
                        matching_connections = list(filter(lambda x: user == x.user, connections))

                    if len(matching_connections) != 0:
                        s.sendall(b'Asistente: Usuario ya se encuentra conectado.\n'
                                  b'Asistente: Si desea conectarse como otro usuario ingrese un nuevo rut\n'
                                  b'Asistente: Si desea desconectarse apriete 4 o despidase.')
                    else:
                        client_connection = Conexion(user, s)

                        with threading_lock:
                            connections.append(client_connection)
                        break

                except IndexError:
                    s.sendall(b'Asistente: RUT invalido, vuelva a ingresar su RUT o despidase para salir.')

            # -------------------------------------------------------------------------------------------------------- #

            # Usuario ya se encuentra autenticado
            print(f"{user.name} se conectó.")

            if user.is_executive:
                exec_loop(s, user)  # Si es que es ejecutivo
            else:
                client_loop(s, user)  # Si es que es usuario

        print(f"{user.name} se desconectó.")

    except ConnectionResetError or BrokenPipeError as in_thread_error:
        print(f"[WARN] {in_thread_error}")

    finally:
        if client_connection is not None:
            connections.remove(client_connection)


# Inicio del socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((HOST, PORT))
sock.listen()

print(f"[INFO] Server started on {HOST}:{PORT}")  # Imprimos que el servidor inició
process_users()  # Procesamos a los usuarios

try:
    while True:
        try:
            conn, addr = sock.accept()
            new_t = threading.Thread(target=connection_, args=[conn])
            new_t.start()
        except BrokenPipeError or ConnectionResetError as datos:  # Debug
            print(f"Someone disconnected :c\n{datos}")

except Exception as error:
    print(f"[WARN] {error}")

except KeyboardInterrupt:
    print(f"[INFO] Server interrupted with Ctrl-C, closing everything...")

finally:

    if len(connections) != 0:
        for conn in connections:
            conn.socket.close()

    sock.close()

    with open('users.json', 'w') as file:
        user_data = [u.to_json() for u in clients]
        exec_data = [e.to_json() for e in execs]
        json.dump(exec_data + user_data, file, indent=4, separators=(',', ': '))

    print("[INFO] Saved user data.")

    print("\b\b[INFO] Server closed.")
