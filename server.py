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

# Lista de espera (clientes que desean conectarse con un ejecutivo)
waiting_list = []

# Threading_lock permite bloquear hilos cuando se acceda a una variable, evitando comportamientos imprevistos
# por accesos múltiples a una misma variable. Close_thread genera un evento con el que los hilos pueden revisar si deben
# cerrarse.
threading_lock = threading.Lock()
close_thread = threading.Event()

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


def exec_loop(exec_connection : Conexion):
    exec_connection.socket.sendall(b'Eres un ejecutivo.')

    while True:
        with threading_lock:
            if len(waiting_list) != 0:
                the_client = waiting_list.pop(0)
                the_client.exec_info = exec_connection
                break

    while True:
        data2 = exec_connection.socket.recv(1024)

        if data2.decode() == '-':
            break

        the_client.socket.sendall(data2)

# client_loop: loop en donde se encuentran los usuarios correspondientes a clientes
#
# PARAMS:
#   conn: objeto tipo socket que caracteriza al cliente
#   client: objeto tipo Usuario que caracteriza al usuario
def client_loop(client_connection : Conexion):
    client = client_connection.user
    conn = client_connection.socket

    assistant_options = f"\t (1) Revisar atenciones anteriores.\n" \
                        f"\t (2) Contactar a un ejecutivo.\n" \
                        f"\t (3) Reiniciar servicios.\n" \
                        f"\t (4) Salir\n"

    # Loop de ayuda/otro
    conn.sendall(f"Bienvenido {client.name}, en que podemos ayudarle?\n{assistant_options}".encode())

    while True:
        if close_thread.is_set():
            break

        data = conn.recv(1024)

        if close_thread.is_set():
            break

        if not data:
            continue

        data = data.decode()

        intencion = interpret_user_input(data)

        # ------------------------------------------------------------------------------------------------------------ #
        # Opción historial
        # Descripción:
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

                if chosen_order.isalnum() and int(chosen_order) > 0 \
                        and int(chosen_order) <= len(client.solicitudes_activas):

                    solicitud = client.solicitudes_activas[int(chosen_order) - 1]
                    conn.sendall(f'Asistente: {solicitud.history[-1]}\n'.encode())
                else:
                    conn.sendall(f'Asistente: usted no seleccionó una solicitud valida.\n'.encode())

        # ------------------------------------------------------------------------------------------------------------ #
        # Opción ejecutivo
        # Descripción:
        if data == "2" or intencion == 'ejecutivo':
            with threading_lock:
                waiting_list.append(client_connection)
                queue_number = len(waiting_list)

            conn.sendall(f'Asistente: Usted se encuentra número {queue_number} en la fila, por favor espere'.encode())

            while True:
                with threading_lock:  # TODO: revisar si tira problemas lockear aquí
                    if client_connection.exec_info is not None:
                        break

            executive = client_connection.exec_info.user
            exec_conn = client_connection.exec_info.socket
            conn.sendall(f"{executive.name}: Hola soy {executive.name}, ¿en qué le puedo ayudar?".encode())
            print(f"[INFO] Cliente {client.name} ha sido redirigido a {executive.name}.")

            while True:
                data2 = conn.recv(1024)

                if data2.decode() == '-':
                    break

                # TODO: checkear conexiones existentes, y que la desconexión de uno implique la del otro y lo que pide
                # el enunciado.

                exec_conn.sendall(data2)



        # ------------------------------------------------------------------------------------------------------------ #
        # Opción reiniciar servicios
        # Descripción:
        if data == "3" or intencion == 'reiniciar_servicios':
            conn.sendall("Asistente: Se ha reiniciado su modem.".encode())
            print(f"[INFO] Se ha reiniciado el modem del cliente {client.name}.")

        # ------------------------------------------------------------------------------------------------------------ #
        # Opción despedida
        # Descripción:
        if data == "4" or intencion == 'despedida':
            break

        # Cada vez que se termina una acción solicitada por el usuario el servidor envía el mensaje de las opciones
        # disponibles.
        conn.sendall(f"\nAsistente: ¿De qué otra manera podemos ayudarle?\n{assistant_options}".encode())

    # Fin del loop donde se encuentra el usuario, guardamos su información, donde se pudo haber cambiado el estado,
    # o agregado una solicitud
    old_user = list(filter(lambda x: x.rut == client.rut, clients))
    if len(old_user) != 0:
        clients.remove(old_user[0])
        clients.append(client)


# Función encargada de manejar las conexiones
def connection_(who):
    user_connection = None

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
                        user_connection = Conexion(user, s)

                        with threading_lock:
                            connections.append(user_connection)
                        break

                except IndexError:
                    s.sendall(b'Asistente: RUT invalido, vuelva a ingresar su RUT o despidase para salir.')

            # -------------------------------------------------------------------------------------------------------- #

            # Usuario ya se encuentra autenticado
            print(f"{user.name} se conectó.")

            if user.is_executive:
                exec_loop(user_connection)  # Si es que es ejecutivo
            else:
                client_loop(user_connection)  # Si es que es usuario

        print(f"{user.name} se desconectó.")

    except ConnectionResetError or BrokenPipeError as in_thread_error:
        print(f"[WARN] {in_thread_error}")

    finally:
        if user_connection is not None:
            connections.remove(user_connection)


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
    close_thread.set()

    if len(connections) != 0:
        print("[INFO] Closing active connections to the server...")

    while True:
        if len(connections) == 0:
            break

finally:

    sock.close()

    with open('users.json', 'w') as file:
        user_data = [u.to_json() for u in clients]
        exec_data = [e.to_json() for e in execs]
        json.dump(exec_data + user_data, file, indent=4, separators=(',', ': '))

    print("[INFO] Saved user data.")

    print("\b\b[INFO] Server closed.")
