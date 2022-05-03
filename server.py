# server.py
# Archivo donde se encuentra el código del servidor
# Versión: Python 3.10
# Agustín González y Benjamín Castro
# otoño 2022 - Principios de Comunicaciones - Proyecto 1

import socket
import threading
import json
import sys
from custom_classes import *

# Variables para hacer setup del servidor, se usa localhost y el puerto 30000
HOST = "127.0.0.1"
PORT = 30001

# True si se desea activar NLP, False si no se desea usar
use_NLP = False
if use_NLP:
    print("[INFO] Cargando modelo...")
    from intencion import intencion  # Para usar NLP

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
# y luego lo agrega a la lista de usuarios. También devuelve la cantidad existente de solicitudes,
# ya sean activas o inactivas.
def process_users():
    number_of_requests = 0
    with open('users.json', 'r') as users_in_database:  # Abrimos y leemos el archivo
        database_users = json.load(users_in_database)

    for user in database_users:  # Le damos el formato a solicitudes activas, inactivas y creamos y agregamos el usuario
        user['solicitudes_activas'] = list(map(lambda request: Solicitud(**request), user['solicitudes_activas']))
        user['solicitudes_inactivas'] = list(map(lambda request: Solicitud(**request), user['solicitudes_inactivas']))
        number_of_requests += len(user['solicitudes_activas']) + len(user['solicitudes_inactivas'])

        if user['is_executive']:  # Si el usuario es ejecutivo se agrega a 'execs', si no, a 'clients'
            execs.append(Usuario(**user))
        else:
            clients.append(Usuario(**user))

    return number_of_requests  # Se devuelve la cantidad de solicitudes existentes


# Interpreta el mensaje del usuario y entrega su intención (uso de NLP), según si se activó o no se usa.
if use_NLP:
    def interpret_user_input(user_msg):
        return intencion(user_msg)
else:
    def interpret_user_input(user_msg):
        return None


# FUNC: exec_loop
# DESC: loop en donde se encuentran los usuarios que corresponden a ejecutives. Implementa todas la funciones,
#       comandos y lógicas realizables.
# PARAMS:
#   exec_connection: objeto conexión con el usuario y socket del ejecutivo
def exec_loop(exec_connection: Conexion):
    global requests_number

    # Identificamos el socket del ejecutivo y su usuario
    exec_socket = exec_connection.socket
    executive = exec_connection.user

    # Comandos disponibles para el ejecutivo
    commands = '\t:name <nombre> (cambia su nombre)\n' \
               '\t:cname <nombre> (cambia nombre de cliente)*\n' \
               '\t:exit (termina conexión con el servidor)\n' \
               '\t:connect (conecta al ejecutivo a un cliente en la lista de espera)\n' \
               '\t:close (cierra la conexión con el cliente)*\n' \
               '\t:new (crea una nueva solicitud, debe estarse conectado con un usuario)*\n' \
               '\t:requests (imprime las solicitudes activas del cliente conectado, pudiendo escoger una)*\n' \
               '\t:subject <new subject> (cambia el sujeto de una solicitud del cliente conectado)*\n' \
               '\t:state [abierto|cerrado] (cambia el estado de una solicitud del cliente conectado)*\n' \
               '\t:history <new history> (agrega historia a la solicitud del cliente conectado)*\n' \
               '\t:restart (reinicia los servicios del cliente)*\n' \
               '\t:help (imprime la lista de comandos)\n' \
               '* Es necesario estar conectade con un cliente.\n' \
               '** No se deben agregar <> o [] al llamar a comandos con argumentos.\n'

    # Se envía una bienvenida al ejecutivo para señalar que se realizó la autenticación correctamente
    exec_socket.sendall(f'Asistente: Bienvenide {executive.name} los comandos disponibles son:\n{commands}'.encode())

    # Se inicia loop donde se encontrará el ejecutivo
    _people_in_queue = 0
    _passed_once_with_nd = False
    while True:
        working_request = None  # Variable donde se guarda la solicitud con la cual se trabajará

        # Se revisa si la señal de cerrar los hilos se activó
        if close_thread.is_set():
            break

        # Se revisa si hay clientes esperando ser atendidos
        with threading_lock:
            _old_number = _people_in_queue
            _people_in_queue = len(waiting_list)

        if _people_in_queue != 0 and not _passed_once_with_nd:
            exec_socket.sendall(f"Asistente: Hay {_people_in_queue} clientes en la lista de espera. "
                                f"Envíe :connect para conectarse con el primero en la fila.".encode())
        elif _old_number != _people_in_queue and _passed_once_with_nd:
            exec_socket.sendall(f"Asistente: Hay {_people_in_queue} clientes en la lista de espera. "
                                f"Envíe :connect para conectarse con el primero en la fila.".encode())

        # Se recibe información del ejecutivo y se decodifica.
        # Si es un comando, se ejecuta, si no, se reenvía al usuario
        try:
            exec_socket.setblocking(False)
            data = exec_socket.recv(1024).decode()
        except BlockingIOError:
            data = '<NO//DATA>'
        finally:
            exec_socket.setblocking(True)

        if data == '<NO//DATA>':
            _passed_once_with_nd = True
        else:
            _passed_once_with_nd = False

        # Se revisa si la señal de cerrar los hilos se activó
        if close_thread.is_set():
            break

        # ------------------------------------------------------------------------------------------------------------ #
        # Opción :name, cambia el nombre del ejecutivo al cual se desee
        if data[0:len(':name')] == ':name':
            old_name = executive.name  # Nombre antiguo
            new_name = data.lstrip(':name').lstrip()  # Se rescata el nuevo nombre

            if new_name.rstrip() == '':
                exec_socket.sendall('Asistente: Nombre inválido, no fue cambiado'.encode())
                continue
            
            executive.name = new_name
            exec_socket.sendall(f"Asistente: Su nombre fue cambiado a {executive.name}".encode())  # Aviso del cambio
            print(f"[INFO] Ejecutive {old_name} cambió su nombre a {executive.name}")  # Se imprime que hubo un cambio

        # ------------------------------------------------------------------------------------------------------------ #
        # Opción :exit, cierra la conexión del ejecutivo con el servidor
        elif data[0:len(':exit')] == ':exit' or data == '4':  # Se mantiene el 4 al estar hard-coded en cliente.py
            exec_socket.sendall("Asistente: Desconectandole del servidor".encode())  # Se avisa de la desconexión
            break

        # ------------------------------------------------------------------------------------------------------------ #
        # Opción :help, imprime los comandos disponibles
        elif data[0:len(':help')] == ':help':
            exec_socket.sendall(f"Asistente: Los comandos disponibles son:\n{commands}".encode())

        # ------------------------------------------------------------------------------------------------------------ #
        # Opción :connect, conecta al ejecutivo con un cliente, de haber clientes en la fila de espera
        elif data[0:len(':connect')] == ':connect':

            # Se revisa si hay clientes en la lista de espera, de haber se conecta, si no se dice que no hay
            with threading_lock:
                clients_waiting = len(waiting_list)

            if clients_waiting == 0:
                exec_socket.sendall('Asistente: No hay clientes esperando hablar con un ejecutive'.encode())
            else:

                # Se recupera el cliente que lleva más tiempo en la lista de espera
                with threading_lock:
                    client_connection = waiting_list.pop(0)

                # Se asigna un ejecutivo a ese cliente
                client_connection.exec_info = exec_connection
                # Se identifican el socket y usuario del cliente
                client = client_connection.user
                client_socket = client_connection.socket
                # Se avisa de la conexión
                exec_socket.sendall(f'Asistente: Conectandole con {client.name}...'
                                    f'\nYo: Hola {client.name}, ¿en qué le puedo ayudar?'.encode())

                # Loop en que se encuentra el ejecutivo cuando está conectado con un cliente.
                # Activa/desactiva ciertos comandos.
                while True:

                    # Para manejo de posibles errores que pueden aparecer
                    try:

                        # Se recibe información del ejecutivo
                        data_received = exec_socket.recv(1024).decode()

                        # ------------------------------------------------------------------------------------------------------------ #
                        # Opción :namec, cambia el nombre del cliente al cual se desee
                        if data_received[0:len(':cname')] == ':cname':
                            old_name = client.name  # Nombre antiguo
                            new_name = data_received.lstrip(':cname').lstrip()  # Se rescata el nuevo nombre

                            if new_name.rstrip() == '':
                                exec_socket.sendall('Asistente: Nombre inválido, no fue cambiado'.encode())
                                continue
                            
                            client.name = new_name
                            exec_socket.sendall(f"Asistente: El nombre fue cambiado a {client.name}".encode())  # Aviso del cambio
                            client_socket.sendall(f"Asistente: Su nombre fue cambiado a {client.name}".encode())  # Aviso del cambio
                            print(f"[INFO] Ejecutive {executive.name} cambió el nombre de {old_name} a {new_name}")  # Se imprime que hubo un cambio

                        # -------------------------------------------------------------------------------------------- #
                        # Opción :close, termina el chat con un cliente
                        elif data_received == '' or data_received[0:len(':close')] == ':close':
                            client_socket.sendall("Asistente: Ejecutive se ha desconectado.".encode())
                            exec_socket.sendall("Asistente: Conexion con el cliente terminada".encode())
                            # Bandera que avisa al cliente del cierre de conexión entre ejecutivo y cliente
                            client_connection.reset_connection = True
                            break

                        # -------------------------------------------------------------------------------------------- #
                        # Opción :requests, revisa las solicitudes activas de un cliente
                        elif data_received[0:len(':requests')] == ':requests':
                            # Mensaje a enviar
                            message = 'Asistente: El cliente tiene las siguientes solicitudes activas:'
                            local_number = 1  # Número de solicitudes activas del cliente

                            # Se agrega por cada solicitud activa una entrada al mensaje
                            for request in client.solicitudes_activas:
                                message = message + f'\n\t ({local_number}) ' + str(request)
                                local_number += 1

                            # De no tener solicitudes activas, se imprime
                            if local_number == 1:
                                exec_socket.sendall(
                                    'Asistente: Acción cancelada, el cliente no tiene solicitudes activas.'.encode())
                                continue  # Se pasa a la siguiente iteración del loop

                            # Se agrega la última información al mensaje
                            message += '\nAsistente: ¿Que solicitud desea escoger?'
                            exec_socket.sendall(message.encode())  # Se envía el mensaje
                            chosen_order = exec_socket.recv(1024).decode()  # Se recibe la orden escogida

                            # Camino a seguir si se escoge una orden válida
                            if chosen_order.isalnum() and 0 < int(chosen_order) <= len(client.solicitudes_activas):
                                working_request = client.solicitudes_activas[int(chosen_order) - 1]
                                exec_socket.sendall(f"Asistente: "
                                                    f"solicitud {working_request.number} seleccionada.".encode())

                            # Camino a seguir si la orden escogida no es válida
                            else:
                                exec_socket.sendall(b"Asistente: No se ha seleccionado una solicitud del cliente.")

                        # -------------------------------------------------------------------------------------------- #
                        # Opción :new, crea una nueva solicitud para el cliente actual
                        elif data_received[0:len(':new')] == ':new':

                            # Mensaje que simboliza que se seleccionó la opción, junto a información de uso
                            exec_socket.sendall(f"Asistente: Se va a crear una nueva solicitud para {client.name},"
                                                f" por favor envíe la descripción. "
                                                f"(Para cancelar envie ':cancel' )".encode())

                            # Se recibe la descripción que tendrá la solicitud
                            subject = exec_socket.recv(1024).decode()

                            # Se revisa si se decidió cancelar la acción
                            if subject[0:len(':cancel')] == ':cancel':
                                exec_socket.sendall('Asistente: acción cancelada.'.encode())
                                continue

                            # Entrada predeterminada para una nueva solicitud.
                            history = f'Creación de la solicitud por {executive.name}'

                            # Se actualiza la cantidad de solicitudes existentes que hay, para asignar un número válido
                            # y único a cada una.
                            with threading_lock:
                                requests_number += 1
                                _requests_number = requests_number

                            # Se crea la solicitud
                            new_request = Solicitud(subject, True, [history], _requests_number)

                            # Se envía, pregunta y recibe respuesta sobre si desea guardar la solicitud creada de ser la
                            # respuesta 'si' se guarda, si no, se descarta.
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
                                # Se recibe la nueva descripción e imprime al ejecutivo si realmente se desea cambiar
                                # de la antigua a la nueva.
                                new_subject = data_received.lstrip(':subject').lstrip()
                                old_subject = working_request.subject

                                exec_socket.sendall(f"Asistente: Se va a cambiar la descripción de la solicitud "
                                                    f"{working_request.number}\n"
                                                    f"\tDe: {old_subject}\n"
                                                    f"\tA: {new_subject}\n"
                                                    f"¿Desea continuar? [Y/n]".encode())

                                data = exec_socket.recv(1024).decode()

                                # De decidir el ejecutivo que se guarda, se guarda la nueva descripción
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
                                # Se identifica el nuevo estado de la solicitud dentro del mensaje
                                new_state = data_received.lstrip(':state').lstrip()
                                old_state = working_request.open

                                # Se identifica según si está abierta (True) o cerrada (False)
                                if new_state.lower() in ('abierto', 'open'):
                                    new_state = True
                                elif new_state.lower() in ('cerrado', 'closed'):
                                    new_state = False
                                else:
                                    exec_socket.sendall('Asistente: Opción invalida, operación cancelada.'.encode())
                                    continue  # De ser inválida la opción escogida, se cancela la operación.

                                # Se envía información para confirmar el cambio que se desea hacer
                                exec_socket.sendall(
                                    f"Asistente: Se va a cambiar el estado de la solicitud "
                                    f"{working_request.number}\n"
                                    f"\tDe: {'abierto' if old_state else 'cerrado'}\n"  # Estado antiguo
                                    f"\tA: {'abierto' if new_state else 'cerrado'}\n"  # Estado nuevo
                                    f"¿Desea continuar? [Y/n]".encode())

                                # Se recibe y lleva a cabo la opción escogida por el usuario
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
                                # Se recupera la historia a agregar de la información recibida
                                new_history = data_received.lstrip(':history').lstrip()
                                # Se confirma con el ejecutivo de la nueva entrada de historia a agregar
                                exec_socket.sendall(
                                    f"Asistente: Se va a agregar la siguiente entrada a la historia de la solicitud "
                                    f"{working_request.number}:\n"
                                    f"\t\"{new_history}\"\n"
                                    f"¿Desea continuar? [Y/n]".encode())

                                data = exec_socket.recv(1024).decode()

                                # Si confirma la acción se agrega, si no, se cancela
                                if data.lower() in ('si', 'yes', 'y', 'ye', 's'):
                                    working_request.history.append(new_history)
                                    exec_socket.sendall('Asistente: La entrada fue agregada.'.encode())
                                else:
                                    exec_socket.sendall('Asistente: No se agregó la nueva entrada.'.encode())

                        # -------------------------------------------------------------------------------------------- #
                        # Opción :restart, reinicia los servicios del modem del cliente
                        elif data_received[0:len(':restart')] == ':restart':
                            # Se imprime y envía mensajes de que se reinició el modem del cliente
                            exec_socket.sendall(f'Asistente: Se reiniciaron los servicios de {client.name}.'.encode())
                            client_socket.sendall(f'Asistente: {executive.name} ha reiniciado su modem.'.encode())
                            print(f"[INFO] {executive.name} reinició los servicios de {client.name}.")

                        # -------------------------------------------------------------------------------------------- #
                        # Opción :help, imprime los comandos disponibles
                        elif data_received[0:len(':help')] == ':help':
                            exec_socket.sendall(f"Asistente: Los comandos disponibles son:\n{commands}".encode())

                        # -------------------------------------------------------------------------------------------- #
                        # Opción :help, imprime los comandos disponibles
                        elif data_received[0:len(':exit')] == ':exit' or data_received[0:len(':name')] == ':name':
                            exec_socket.sendall("Asistente: Comando no disponible al hablar con cliente.".encode())

                        # -------------------------------------------------------------------------------------------- #
                        # Opción :help, imprime los comandos disponibles
                        elif data_received[0:len(':connect')] == ':connect':
                            exec_socket.sendall(f"Asistente: Usted ya se encuentra conectade a un cliente".encode())

                        # -------------------------------------------------------------------------------------------- #
                        # En caso de no haber enviado un comando se reenvía el mensaje al cliente
                        else:
                            data_to_send = (executive.name + ': ' + data_received).encode()
                            client_socket.sendall(data_to_send)

                    # Captura de posibles errores
                    except OSError:
                        break

# FUNC: client_loop
# DESC: loop en donde se encuentran los usuarios que corresponden a clientes. Implementa todas la funciones,
#       comandos y lógicas realizables.
# PARAMS:
#   client_connection: objeto conexión con el usuario y socket del cliente
def client_loop(client_connection: Conexion):
    # Definimos el socket y usario del cliente
    client = client_connection.user
    client_socket = client_connection.socket

    # Opciones para los clientes
    assistant_options = f"\t (1) Revisar atenciones anteriores.\n" \
                        f"\t (2) Contactar a un ejecutivo.\n" \
                        f"\t (3) Reiniciar servicios.\n" \
                        f"\t (4) Salir\n"

    # Bienvenida al cliente
    client_socket.sendall(f"Bienvenido {client.name}, en que podemos ayudarle?\n{assistant_options}".encode())

    # Loop del cliente
    _passed_once_with_nd = False
    while True:
        # Se revisa si la señal de cerrar los hilos se activó
        if close_thread.is_set():
            break
        
        try:
            client_socket.setblocking(False)
            data = client_socket.recv(1024).decode()  # Recibir la información del cliente
        except BlockingIOError:
            data = '<NO//DATA>'
        finally:
            client_socket.setblocking(True)

        # En caso de que no llegué información del cliente se reinicia el loop
        if not data or data == '<NO//DATA>':
            continue

        intencion = interpret_user_input(data)  # Interpretación del mensaje del cliente por NLP

        if data in ('1', '2', '3', '4'):
            intencion = ''

        # Inicio de interpretación de la información recibida del cliente
        # ------------------------------------------------------------------------------------------------------------ #
        # Opción historial
        # Descripción: Permite escoger una solicitud activa y muestra la última entrada que tiene en su historia
        if data == "1" or intencion == 'historial':
            # Checkeo de que tenga solicitudes activas
            if len(client.solicitudes_activas) == 0:
                client_socket.sendall(b'No posee solicitudes activas.')
            # De tener solicitudes activas se sigue este camino
            else:
                # Se crea el mensaje a enviar con las solicitudes
                message = 'Asistente: Usted tiene las siguientes solicitudes en curso:'
                local_number = 1

                for solicitud in client.solicitudes_activas:
                    message = message + f'\n\t ({local_number}) ' + str(solicitud)
                    local_number += 1

                message += '\nAsistente: ¿Que solicitud desea consultar?'
                client_socket.sendall(message.encode())  # Se envía el mensaje
                chosen_order = client_socket.recv(1024).decode()  # Se recibe la orden escogida

                # Se verifica que la respuesta sea un número válido
                if chosen_order.isalnum() and 0 < int(chosen_order) <= len(client.solicitudes_activas):
                    solicitud = client.solicitudes_activas[int(chosen_order) - 1]
                    client_socket.sendall(f'Asistente: {solicitud.history[-1]}\n'.encode())
                # En caso de que no sea válido el número se avisa
                else:
                    client_socket.sendall(f'Asistente: usted no seleccionó una solicitud valida.\n'.encode())

        # ------------------------------------------------------------------------------------------------------------ #
        # Opción ejecutivo
        # Descripción: Se agrega al cliente a una lista de espera para luego ser conectado a un ejecutivo, se mantiene
        #              al cliente en espera de un ejecutivo.
        if data == "2" or intencion == 'ejecutivo':
            # Se agrega al cliente a la lista de espera
            with threading_lock:
                waiting_list.append(client_connection)
                queue_number = len(waiting_list)

            # Se avisa que número en la fila tiene el cliente
            client_socket.sendall(
                f'Asistente: Usted se encuentra número {queue_number} en la fila, por favor espere...'.encode())

            # Se revisa si es que ya se asignó un ejecutivo al cliente, se mantiene al cliente en un loop
            while True:
                with threading_lock:
                    if client_connection.exec_info is not None:
                        break
                    current_pos = waiting_list.index(client_connection) + 1
                if current_pos < queue_number:
                    client_socket.sendall(
                        f'Asistente: Usted se encuentra número {current_pos} en la fila, por favor espere...'.encode())
                    queue_number = current_pos

            # El ejecutivo ya se conectó y se identifica su socket y usuario
            executive = client_connection.exec_info.user
            exec_socket = client_connection.exec_info.socket
            # Se avisa de la conexión e imprime de la redirección en la consola del servidor
            client_socket.sendall(f"\n{executive.name}: Hola {client.name}, ¿en qué le puedo ayudar?".encode())
            print(f"[SERVER] Cliente {client.name} ha sido redirigido a {executive.name}.")

            # Loop de comunicación entre cliente y ejecutivo,
            # el cliente no posee comandos, solo envía mensajes a ejecutivo
            while True:
                try:
                    try:
                        client_socket.setblocking(False)
                        data_received = client_socket.recv(1024).decode()  # Información recibida
                        data_to_send = (client.name + ': ' + data_received).encode()  # Información limpiada para enviar
                    except BlockingIOError:
                        data_received = '<NO//DATA>'
                    finally:
                        client_socket.setblocking(True)

                    # Se revisa si se activó la bandera para cerrar conexión cliente-ejecutivo
                    if data_received == '' or client_connection.reset_connection:
                        del exec_socket
                        client_connection.exec_info = None
                        client_connection.reset_connection = False
                        break
                    elif data_received == '<NO//DATA>':
                        continue

                    exec_socket.sendall(data_to_send)  # Envío de información

                except OSError:
                    break

            # Se informa del cierre de conexión
            client_socket.sendall(f"Asistente: se ha cerrado su conexion con {executive.name}.".encode())

        # ------------------------------------------------------------------------------------------------------------ #
        # Opción reiniciar servicios
        # Descripción: Comando 'dummy' que avisa del reinicio del modem al usuario y en la consola del servidor
        if data == "3" or intencion == 'reiniciar_servicios':
            client_socket.sendall("Asistente: Se ha reiniciado su modem.\n".encode())
            print(f"[INFO] Se ha reiniciado el modem del cliente {client.name}.")

        # ------------------------------------------------------------------------------------------------------------ #
        # Opción despedida
        # Descripción: Cierra la conexión del cliente con el servidor
        if data in ("4", ":exit") or intencion == 'despedida':
            break

        # Cada vez que se termina una acción solicitada por el usuario el servidor envía el mensaje de las opciones
        # disponibles.
        client_socket.sendall(f"Asistente: ¿De qué otra manera podemos ayudarle?\n{assistant_options}".encode())


# FUNC: _connection_manager
# DESC: función encargada de autenticar al usuario, manejar que la conexión se mantenga/cierre y administrar la
#       aparición de errores.
# PARAMS:
#   a_socket: objeto tipo socket del usuario a conectar
def _connection_manager(a_socket):
    user_connection = None  # Variable que guardará el objeto tipo Conexión del usuario

    try:
        with a_socket as user_socket:

            # -------------------------------------------------------------------------------------------------------- #
            # Bienvenida
            user_socket.sendall(f'Hola! Bienvenide, ingrese su RUT'.encode())

            # -------------------------------------------------------------------------------------------------------- #
            # Autenticación
            while True:
                user_rut = user_socket.recv(2048).decode()  # Se recibe el RUT

                # TODO: Implementar correctamente NLP / RUT
                intencion = interpret_user_input(user_rut)  # Se interpreta el mensaje del usuario con NLP

                # En caso de ser la intención del usuario despedirse, se cierra la conexión
                if user_rut.lower() in ('4', 'chao', 'bye', 'no') or intencion == 'despedida':
                    print("[SERVER] Usuario no autenticado se desconectó.")
                    user_socket.close()
                    return

                # Si la respuesta no es despedida se intenta autenticar al usuario
                try:
                    with threading_lock:
                        # Se busca al usuario entre clientes y ejecutivos, de no encontrarse se levanta 'IndexError'
                        user = list(filter(lambda x: x.rut == user_rut, clients + execs))[0]
                        # Se busca si el usuario ya está conectado
                        matching_connections = list(filter(lambda x: user == x.user, connections))

                    # Si el usuario ya está conectado, se informa y reinicia el proceso
                    if len(matching_connections) != 0:
                        user_socket.sendall(b'Asistente: Usuario ya se encuentra conectado.\n'
                                            b'Asistente: Si desea conectarse como otro usuario ingrese un nuevo rut\n'
                                            b'Asistente: Si desea desconectarse apriete 4 o despidase.')
                    else:
                        # Se crea un objeto Conexión y se agrega a la lista de conexiones existentes
                        user_connection = Conexion(user, user_socket)

                        with threading_lock:
                            connections.append(user_connection)
                        break

                except IndexError:
                    # Se informa que el RUT es inválido
                    user_socket.sendall(b'Asistente: RUT invalido, vuelva a ingresar su RUT o despidase para salir.')

            # -------------------------------------------------------------------------------------------------------- #
            # Usuario ya se encuentra autenticado
            print(f"[SERVER] {user.name} se conectó.")

            # -------------------------------------------------------------------------------------------------------- #
            # Se inicia el proceso del usuario según si es ejecutivo o cliente
            if user.is_executive:
                exec_loop(user_connection)  # Si es que es ejecutivo
            else:
                client_loop(user_connection)  # Si es que es usuario

    # Manejo de errores en caso de que se haya interrumpido la conexión
    except ConnectionResetError or BrokenPipeError as in_thread_error:
        print(f"[WARN::] {in_thread_error}")

    # Se finaliza la sesión de usuario, informa en la consola y remueve la conexión de conexiones existentes
    finally:
        print(f"[SERVER] {user.name} se desconectó.")
        if user_connection is not None:
            connections.remove(user_connection)

if __name__ == '__main__':
    # Inicio del socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, PORT))
    sock.listen()
    sock.settimeout(0.5)

    # Imprimos que el servidor inició e información de estado
    print(f"[INFO] Server started on {HOST}:{PORT}\n"
          f"[INFO] NLP se encuentra {'ACTIVADO' if use_NLP else 'DESACTIVADO'}")
    # Procesamos a los usuarios y asignamos a requests_number el número total de solicitudes existentes
    requests_number = process_users()

    try:
        while True:
            try:
                conn, addr = sock.accept()
                new_t = threading.Thread(target=_connection_manager, args=[conn])
                new_t.start()
            except BrokenPipeError or ConnectionResetError as datos:  # Manejo de errores
                print(f"[WARN] Someone disconnected\n{datos}")

            except socket.timeout:
                continue

    except KeyboardInterrupt:  # En caso de apretar Ctrl-C se guarda la data
        print(f"[INFO] Server interrupted with Ctrl-C, closing everything...")
        close_thread.set()

        if len(connections) != 0:
            print("[INFO] Closing active connections to the server...")

        while True:
            if len(connections) == 0:
                break

    except Exception as error:  # En caso de un error inesperado
        print(f"[WARN:] {error}")

    finally:  # Se cierra el socket del servidor

        sock.close()

        # Se guarda la información de usuarios y ejecutivos
        with open('users.json', 'w') as file:
            user_data = [u.to_json() for u in clients]
            exec_data = [e.to_json() for e in execs]
            json.dump(exec_data + user_data, file, indent=4, separators=(',', ': '))

        # Se informa de que se cerró el server y que se guardó la información de usuarios
        print("[INFO] Saved user data.")
        print("\b\b[INFO] Server closed.")
