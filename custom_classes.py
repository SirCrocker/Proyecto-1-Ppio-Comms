#
# Benjamin Castro y Agustin Gonzalez
# DESC: Archivo con clases a ser usadas en servidor para un manejo más fácil de las solicitudes, usuarios y conexiones.
# Proyecto 1 - Principio de Comunicaciones - otoño 2022
#

class Solicitud:
    """
    Maneja las solicitudes, dandoles una descripcion (subject), un estado que simboliza si esta abierta o cerrada (open)
    una historia (history) y un número identificador (number)

    El método to_json transforma la información almacenada en un diccionario en tipo json para luego poder ser guardado
    un .json con toda la información correspondiente.
    """

    def __init__(self, subject, open, history, number):
        self.subject = subject
        self.open = open
        self.history = history
        self.number = number

    def to_json(self):
        final_dict = {'number': self.number,
                      'subject': self.subject,
                      'open': self.open,
                      'history': self.history}
        return final_dict

    def __str__(self):
        return f"Solicitud {self.number}: {self.subject}"


class Usuario:
    """
    Maneja a los usuarios, teniendo como atributos su nombre (name), su rut (rut), si es que el usuario es un ejecutivo
    (is_executive), las solicitudes activas que tiene (solicitudes_activas) y las solicitudes inactivas que tiene
    (solicitudes_inactivas).

    El método to_json transforma la información almacenada en un diccionario en tipo json para luego poder ser guardado
    un .json con toda la información correspondiente, donde ademas llama a ese método en sus solicitudes activas e
    inactivas. De guardarse información de usuario se hace con el método del usuario.
    """

    def __init__(self, name, rut, solicitudes_activas, solicitudes_inactivas, is_executive=False):
        self.name = name  # "Juan Carlos Bodoque"
        self.rut = rut  # "3.333.333-3"
        self.is_executive = is_executive
        self.solicitudes_activas = solicitudes_activas
        self.solicitudes_inactivas = solicitudes_inactivas

    def to_json(self):
        active_requests = list(map(lambda request: request.to_json(), self.solicitudes_activas))
        inactive_requests = list(map(lambda request: request.to_json(), self.solicitudes_inactivas))

        final_dict = {'name': self.name,
                      'rut': self.rut,
                      'is_executive': self.is_executive,
                      'solicitudes_activas': active_requests,
                      'solicitudes_inactivas': inactive_requests
                      }

        return final_dict


class Conexion:
    """
    Maneja las conexiones existentes, teniendo tres atributos, _exec_conn_ que posee la conexion de un ejecutivo si es
    que el usuario es cliente, _user_ que es el usuario conectado con esa ip y puerto, y _socket_ que es la instancia
    de socket que posee toda la información correspondiente al socket de ese usuario en específico.
    """

    def __init__(self, user, socket_connection, exec_connection=None):
        self.exec_info = exec_connection
        self.user = user
        self.socket = socket_connection
        self.reset_connection = False
