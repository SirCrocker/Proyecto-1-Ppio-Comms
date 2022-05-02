import socket
import threading
import json
from custom_classes import *

# Variables para hacer setup del servidor, se usa localhost y el puerto 30000
HOST = "127.0.0.1"
PORT = 30001

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
# y luego lo agrega a la lista. También devuelve la cantidad existente de solicitudes, ya sea activa o inactivas.
def process_users():
    number_of_requests = 0
    with open('users.json', 'r') as users_in_database:  # Abrimos y leemos el archivo
        database_users = json.load(users_in_database)

    for user in database_users:  # Le damos el formato a solicitudes activas, inactivas y creamos y agregamos el usuario
        user['solicitudes_activas'] = list(map(lambda request: Solicitud(**request), user['solicitudes_activas']))
        user['solicitudes_inactivas'] = list(map(lambda request: Solicitud(**request), user['solicitudes_inactivas']))
        number_of_requests += len(user['solicitudes_activas']) + len(user['solicitudes_inactivas'])
        if user['is_executive']:
            execs.append(Usuario(**user))
        else:
            clients.append(Usuario(**user))

    return number_of_requests


# Interpreta el mensaje del usuario y entrega su intención
def interpret_user_input(user_msg):
    return 0


def exec_loop(exec_connection: Conexion):
    global requests_number

    exec_socket = exec_connection.socket
    executive = exec_connection.user

    commands = '\t:name <nombre> (cambia su nombre)\n' \
               '\t:exit (termina conexión con el servidor)\n' \
               '\t:connect (conecta al ejecutivo a un cliente en la lista de espera)\n' \
               '\t:close (cierra la conexión con el cliente)\n' \
               '\t:new (crea una nueva solicitud, debe estarse conectado con un usuario)\n' \
               '\t:requests (imprime las solicitudes activas del cliente conectado, pudiendo escoger una)\n' \
               '\t:subject <new subject> (cambia el sujeto de una solicitud del cliente conectado)\n' \
               '\t:state [abierto|cerrado] (cambia el estado de una solicitud del cliente conectado)\n' \
               '\t:history <new history> (agrega historia a la solicitud del cliente conectado)\n' \
               '\t:restart (reinicia los servicios del cliente)\n' \
               '\t:help (imprime la lista de comandos)'

    exec_socket.sendall(f'Asistente: Bienvenide {executive.name} los comandos disponibles son:\n{commands}'.encode())

    while True:
        working_request = None

        with threading_lock:
            if len(waiting_list) != 0:
                exec_socket.sendall(f"Asistente: Hay {len(waiting_list)} clientes en la lista de espera. "
                                    f"Envíe :connect para conectarse con el primero en la fila.".encode())

        data = exec_socket.recv(1024).decode()

        # -------------------------------------------------------------------------------------------- #
        # Opción :name, cambia el nombre del ejecutivo al cual desee
        if data[0:len(':name')] == ':name':
            old_name = executive.name
            executive.name = data.lstrip(':name').lstrip()
            exec_socket.sendall(f"Asistente: Su nombre fue cambiado a {executive.name}".encode())
            print(f"[INFO] Ejecutive {old_name} cambió su nombre a {executive.name}")

        # -------------------------------------------------------------------------------------------- #
        # Opción :exit, cierra la conexión del ejecutivo con el servidor
        elif data[0:len(':exit')] == ':exit' or data == '4':
            exec_socket.sendall("Asistente: Desconectandole del servidor".encode())
            break

        # -------------------------------------------------------------------------------------------- #
        # Opción :help, imprime los comandos disponibles
        elif data[0:len(':help')] == ':help':
            exec_socket.sendall(f"Asistente: Los comandos disponibles son:\n{commands}".encode())

        # -------------------------------------------------------------------------------------------- #
        # Opción :connect, conecta al ejecutivo con un cliente, de haber clientes en la fila de espera
        elif data[0:len(':connect')] == ':connect':
            with threading_lock:
                clients_waiting = len(waiting_list)
            if clients_waiting == 0:
                exec_socket.sendall('Asistente: No hay clientes esperando hablar con un ejecutive'.encode())
            else:
                with threading_lock:
                    client_connection = waiting_list.pop(0)
                client_connection.exec_info = exec_connection
                client = client_connection.user
                client_socket = client_connection.socket
                exec_socket.sendall(f'Asistente: Conectandole con {client.name}...'
                                    f'\nYo: Hola soy {executive.name}, ¿en qué le puedo ayudar?'.encode())

                while True:
                    try:

                        data_received = exec_socket.recv(1024).decode()

                        # -------------------------------------------------------------------------------------------- #
                        # Opción :close, termina el chat con un cliente
                        if data_received == '' or data_received[0:len(':close')] == ':close':
                            client_socket.sendall("Asistente: Ejecutive se ha desconectado.".encode())
                            exec_socket.sendall("Asistente: Conexion con el cliente terminada".encode())
                            client_connection.reset_connection = True
                            break

                        # -------------------------------------------------------------------------------------------- #
                        # Opción :requests, revisa las solicitudes activas de un cliente
                        elif data_received[0:len(':requests')] == ':requests':
                            message = 'Asistente: El cliente tiene las siguientes solicitudes activas:'
                            local_number = 1

                            for request in client.solicitudes_activas:
                                message = message + f'\n\t ({local_number}) ' + str(request)
                                local_number += 1

                            message += '\nAsistente: ¿Que solicitud desea escoger?'
                            exec_socket.sendall(message.encode())
                            chosen_order = exec_socket.recv(1024).decode()

                            if chosen_order.isalnum() and 0 < int(chosen_order) <= len(client.solicitudes_activas):
                                working_request = client.solicitudes_activas[int(chosen_order) - 1]
                                exec_socket.sendall(f"Asistente: "
                                                    f"solicitud {working_request.number} seleccionada.".encode())
                            else:
                                exec_socket.sendall(b"Asistente: No se ha seleccionado una solicitud del cliente.")
                        # -------------------------------------------------------------------------------------------- #
                        # Opción :new, crea una nueva solicitud para el cliente actual
                        elif data_received[0:len(':new')] == ':new':
                            exec_socket.sendall(f"Asistente: Se va a crear una nueva solicitud para {client.name},"
                                                f" por favor envíe la descripción. "
                                                f"(Para cancelar envie ':cancel' )".encode())
                            subject = exec_socket.recv(1024).decode()

                            if subject[0:len(':cancel')] == ':cancel':
                                exec_socket.sendall('Asistente: acción cancelada.'.encode())
                                continue

                            history = f'Creación de la solicitud por {executive.name}'

                            with threading_lock:
                                requests_number += 1
                                _requests_number = requests_number

                            new_request = Solicitud(subject, True, [history], _requests_number)

                            exec_socket.sendall(f"Asistente: La solicitud ha sido creada. ¿Desea guardarla? [Y/n]\n"
                                                f"\tSolicitud {_requests_number}\n"
                                                f"\t Descripción: {subject}\n"
                                                f"\t Historia: {history}\n"
                                                f"\t Estado: abierta".encode())
                            response = exec_socket.recv(1024).decode()

                            if response.lower() in ('si', 'yes', 's', 'y', 'ye'):
                                client.solicitudes_activas.append(new_request)
                                exec_socket.sendall("Asistente: La solicitud fue guardada.".encode())
                            else:
                                exec_socket.sendall("Asistente: La solicitud fue descartada.".encode())
                            del new_request

                        # -------------------------------------------------------------------------------------------- #
                        # Opción :subject, cambia la descripción de una solicitud escogida anteriormente
                        elif data_received[0:len(':subject')] == ':subject':

                            if working_request is None:
                                exec_socket.sendall(b'Asistente: No ha seleccionado una solicitud del cliente.')

                            else:
                                new_subject = data_received.lstrip(':subject').lstrip()
                                old_subject = working_request.subject

                                exec_socket.sendall(f"Asistente: Se va a cambiar la descripción de la solicitud "
                                                    f"{working_request.number}\n"
                                                    f"\tDe: {old_subject}\n"
                                                    f"\tA: {new_subject}\n"
                                                    f"¿Desea continuar? [Y/n]".encode())

                                data = exec_socket.recv(1024).decode()

                                if data.lower() in ('si', 'yes', 'y', 'ye', 's'):
                                    working_request.subject = new_subject
                                    exec_socket.sendall(
                                        'Asistente: La descripción de la solicitud fue cambiada.'.encode())
                                else:
                                    exec_socket.sendall('Asistente: Se ha cancelado el cambio de descripción.'.encode())

                        # -------------------------------------------------------------------------------------------- #
                        # Opción :state, cambia el estado de una solicitud escogida anteriormente
                        elif data_received[0:len(':state')] == ':state':
                            if working_request is None:
                                exec_socket.sendall(b'Asistente: No ha seleccionado una solicitud del cliente.')
                            else:
                                new_state = data_received.lstrip(':state').lstrip()
                                old_state = working_request.open

                                if new_state.lower() in ('abierto', 'open'):
                                    new_state = True
                                elif new_state.lower() in ('cerrado', 'closed'):
                                    new_state = False
                                else:
                                    exec_socket.sendall('Asistente: Opción invalida, operación cancelada.')
                                    continue

                                exec_socket.sendall(
                                    f"Asistente: Se va a cambiar el estado de la solicitud "
                                    f"{working_request.number}\n"
                                    f"\tDe: {'abierto' if old_state else 'cerrado'}\n"  # Estado antiguo
                                    f"\tA: {'abierto' if new_state else 'cerrado'}\n"  # Estado nuevo
                                    f"¿Desea continuar? [Y/n]".encode())

                                data = exec_socket.recv(1024).decode()

                                if data.lower() in ('si', 'yes', 'y', 'ye', 's'):
                                    working_request.state = new_state
                                    exec_socket.sendall('Asistente: El estado de la solicitud fue cambiada.'.encode())
                                else:
                                    exec_socket.sendall('Asistente: Se ha cancelado el cambio de estado.'.encode())

                        # -------------------------------------------------------------------------------------------- #
                        # Opción :history, agrega una nueva entrada a una solicitud escogida anteriormente
                        elif data_received[0:len(':history')] == ':history':
                            if working_request is None:
                                exec_socket.sendall(b'Asistente: No ha seleccionado una solicitud del cliente.')
                            else:
                                new_history = data_received.lstrip(':history').lstrip()

                                exec_socket.sendall(
                                    f"Asistente: Se va a agregar la siguiente entrada a la historia de la solicitud "
                                    f"{working_request.number}:\n"
                                    f"\t\"{new_history}\"\n"
                                    f"¿Desea continuar? [Y/n]".encode())

                                data = exec_socket.recv(1024).decode()

                                if data.lower() in ('si', 'yes', 'y', 'ye', 's'):
                                    working_request.history.append(new_history)
                                    exec_socket.sendall('Asistente: La entrada fue agregada.'.encode())
                                else:
                                    exec_socket.sendall('Asistente: No se agregó la nueva entrada.'.encode())

                        # -------------------------------------------------------------------------------------------- #
                        # Opción :restart, reinicia los servicios del modem del cliente
                        elif data_received[0:len(':restart')] == ':restart':
                            exec_socket.sendall(f'Asistente: Se reiniciaron los servicios de {client.name}.'.encode())
                            client_socket.sendall(f'Asistente: {executive.name} ha reiniciado su modem.'.encode())
                            print(f"[INFO] {executive.name} reinició los servicios de {client.name}.")

                        # -------------------------------------------------------------------------------------------- #
                        # Opción :help, imprime los comandos disponibles
                        elif data_received[0:len(':help')] == ':help':
                            exec_socket.sendall(f"Asistente: Los comandos disponibles son:\n{commands}".encode())

                        else:
                            data_to_send = (executive.name + ': ' + data_received).encode()
                            client_socket.sendall(data_to_send)

                    except OSError:
                        break

        # TODO: Implementar logica del ejecutivo (Hasta aqui funcionan todas)


# client_loop: loop en donde se encuentran los usuarios correspondientes a clientes
#
# PARAMS:
def client_loop(client_connection: Conexion):
    client = client_connection.user
    client_socket = client_connection.socket

    assistant_options = f"\t (1) Revisar atenciones anteriores.\n" \
                        f"\t (2) Contactar a un ejecutivo.\n" \
                        f"\t (3) Reiniciar servicios.\n" \
                        f"\t (4) Salir\n"

    # Loop de ayuda/otro
    client_socket.sendall(f"Bienvenido {client.name}, en que podemos ayudarle?\n{assistant_options}".encode())

    # TODO: clean up this
    while True:
        if close_thread.is_set():
            break

        data = client_socket.recv(1024)

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
                client_socket.sendall(b'No posee solicitudes activas.')
            else:

                message = 'Asistente: Usted tiene las siguientes solicitudes en curso:'
                local_number = 1

                for solicitud in client.solicitudes_activas:
                    message = message + f'\n\t ({local_number}) ' + str(solicitud)
                    local_number += 1

                message += '\nAsistente: ¿Que solicitud desea consultar?'
                client_socket.sendall(message.encode())
                chosen_order = client_socket.recv(1024).decode()

                if chosen_order.isalnum() and 0 < int(chosen_order) <= len(client.solicitudes_activas):

                    solicitud = client.solicitudes_activas[int(chosen_order) - 1]
                    client_socket.sendall(f'Asistente: {solicitud.history[-1]}\n'.encode())
                else:
                    client_socket.sendall(f'Asistente: usted no seleccionó una solicitud valida.\n'.encode())

        # ------------------------------------------------------------------------------------------------------------ #
        # Opción ejecutivo
        # Descripción:
        if data == "2" or intencion == 'ejecutivo':
            with threading_lock:
                waiting_list.append(client_connection)
                queue_number = len(waiting_list)

            client_socket.sendall(f'Asistente: Usted se encuentra número {queue_number} en la fila, '
                                  f'por favor espere'.encode())

            while True:
                with threading_lock:
                    if client_connection.exec_info is not None:
                        break

            executive = client_connection.exec_info.user
            exec_socket = client_connection.exec_info.socket
            client_socket.sendall(f"\n{executive.name}: Hola {client.name}, ¿en qué le puedo ayudar?".encode())
            print(f"[SERVER] Cliente {client.name} ha sido redirigido a {executive.name}.")

            while True:
                try:
                    data_received = client_socket.recv(1024).decode()
                    data_to_send = (client.name + ': ' + data_received).encode()

                    if data_received == '' or client_connection.reset_connection:
                        del exec_socket
                        client_connection.exec_info = None
                        client_connection.reset_connection = False
                        break

                    exec_socket.sendall(data_to_send)

                except OSError:
                    break

            client_socket.sendall(f"Asistente: se ha cerrado su conexion con {executive.name}.".encode())

        # ------------------------------------------------------------------------------------------------------------ #
        # Opción reiniciar servicios
        # Descripción:
        if data == "3" or intencion == 'reiniciar_servicios':
            client_socket.sendall("Asistente: Se ha reiniciado su modem.".encode())
            print(f"[INFO] Se ha reiniciado el modem del cliente {client.name}.")

        # ------------------------------------------------------------------------------------------------------------ #
        # Opción despedida
        # Descripción:
        if data == "4" or intencion == 'despedida':
            break

        # Cada vez que se termina una acción solicitada por el usuario el servidor envía el mensaje de las opciones
        # disponibles.
        client_socket.sendall(f"\nAsistente: ¿De qué otra manera podemos ayudarle?\n{assistant_options}".encode())

    # Fin del loop donde se encuentra el usuario, guardamos su información, donde se pudo haber cambiado el estado,
    # o agregado una solicitud
    with threading_lock:
        old_user = list(filter(lambda x: x.rut == client.rut, clients))
    if len(old_user) != 0:
        with threading_lock:
            clients.remove(old_user[0])
            clients.append(client)


# Función encargada de manejar las conexiones
def connection_(a_socket):
    user_connection = None

    try:
        with a_socket as user_socket:

            # -------------------------------------------------------------------------------------------------------- #
            # Bienvenida
            user_socket.sendall(f'Hola! Bienvenide, ingrese su RUT'.encode())

            # -------------------------------------------------------------------------------------------------------- #
            # Autenticación
            while True:
                user_rut = user_socket.recv(2048).decode()

                # TODO: Implementar correctamente NLP / RUT
                intencion = interpret_user_input(user_rut)

                if user_rut.lower() in ('4', 'chao', 'bye', 'no') or intencion == 'despedida':
                    print("[SERVER] Usuario no autenticado se desconectó.")
                    user_socket.close()
                    return

                try:
                    with threading_lock:
                        user = list(filter(lambda x: x.rut == user_rut, clients + execs))[0]
                        matching_connections = list(filter(lambda x: user == x.user, connections))

                    if len(matching_connections) != 0:
                        user_socket.sendall(b'Asistente: Usuario ya se encuentra conectado.\n'
                                            b'Asistente: Si desea conectarse como otro usuario ingrese un nuevo rut\n'
                                            b'Asistente: Si desea desconectarse apriete 4 o despidase.')
                    else:
                        user_connection = Conexion(user, user_socket)

                        with threading_lock:
                            connections.append(user_connection)
                        break

                except IndexError:
                    user_socket.sendall(b'Asistente: RUT invalido, vuelva a ingresar su RUT o despidase para salir.')

            # -------------------------------------------------------------------------------------------------------- #
            # Usuario ya se encuentra autenticado
            print(f"[SERVER] {user.name} se conectó.")

            if user.is_executive:
                exec_loop(user_connection)  # Si es que es ejecutivo
            else:
                client_loop(user_connection)  # Si es que es usuario

    except ConnectionResetError or BrokenPipeError as in_thread_error:
        print(f"[WARN::] {in_thread_error}")

    finally:
        print(f"[SERVER] {user.name} se desconectó.")
        if user_connection is not None:
            connections.remove(user_connection)


# IF NAME == MAIN
# Inicio del socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((HOST, PORT))
sock.listen()

print(f"[INFO] Server started on {HOST}:{PORT}")  # Imprimos que el servidor inició
# Procesamos a los usuarios y asignamos a requests_number el número total de solicitudes existentes
requests_number = process_users()

try:
    while True:
        try:
            conn, addr = sock.accept()
            new_t = threading.Thread(target=connection_, args=[conn])
            new_t.start()
        except BrokenPipeError or ConnectionResetError as datos:  # Debug
            print(f"[WARN] Someone disconnected\n{datos}")

except KeyboardInterrupt:
    print(f"[INFO] Server interrupted with Ctrl-C, closing everything...")
    close_thread.set()

    if len(connections) != 0:
        print("[INFO] Closing active connections to the server...")

    while True:
        if len(connections) == 0:
            break

except Exception as error:
    print(f"[WARN:] {error}")

finally:

    sock.close()

    with open('users.json', 'w') as file:
        user_data = [u.to_json() for u in clients]
        exec_data = [e.to_json() for e in execs]
        json.dump(exec_data + user_data, file, indent=4, separators=(',', ': '))

    print("[INFO] Saved user data.")

    print("\b\b[INFO] Server closed.")
