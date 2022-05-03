# client.py
# Archivo donde se encuentra el código del cliente
# Versión: Python 3.10
# Agustín González y Benjamín Castro
# otoño 2022 - Principios de Comunicaciones - Proyecto 1

import socket
import sys
import threading

if sys.platform in ('win32', 'win', 'cygwin', 'msys'):
    def _remove_cmdline_entry(msg_sent):
        print('\b\r' + " " * len(msg_sent), end='\r')

else: #  sys.platform in ('darwin', 'linux') y otros OS-ses 
    def _remove_cmdline_entry(_):
        print('\b\033[1A' + '\033[K', end="\r")

def main():

    # Prefijo/nombre que se imprimirá en la consola del cliente (en vez de su nombre)
    user_prefix = "Yo"
    connection_ended = False  # Para establecer que se cerró la conexión

    # Dirección y puerto del servidor
    HOST = "127.0.0.1"
    PORT = 30001

    print("\n[INFO] Conectandose al servidor...")

    # Se inicia el socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    # Función que escucha al socket, esperando recibir información. De recibir la imprime
    def listen_to_server(s):

        while True:
            try:
                data = s.recv(1024).decode()
            except OSError:
                return

            if connection_ended or data == '':
                return

            print(data)

    # Se crea un hilo donde se escuchará información por recibir
    listener = threading.Thread(target=listen_to_server, args=[sock])
    listener.start()

    # Se lee la consola (entrada estándar) y ejecutan comandos según se cumplan ciertos requisitos
    try:
        for user_message in sys.stdin:
            clean_msg = user_message.rstrip()
            _remove_cmdline_entry(user_message)  # Esto borra el mensaje anterior para imprimirlo con 'Yo: {data}'
            _remove_cmdline_entry(user_message)

            if clean_msg == '':  # Si el mensaje está en blanco no se hace nada
                continue

            print(f"{user_prefix}: {clean_msg}")

            if clean_msg != "":
                sock.sendall(clean_msg.encode())  # Si el mensaje no está vacío, se envía

            if clean_msg == "4" or not listener.is_alive():  # Si el hilo murió o si se envía 4, se cierra el socket
                connection_ended = True
                _remove_cmdline_entry(user_message)
                break

    except KeyboardInterrupt:
        connection_ended = True  # Para avisarle al hilo que se cerró la conexión
    
    finally:
        sock.close()  # Se cierra el socket

if __name__ == '__main__':
    main()
    print("Asistente: Gracias por contactarse con nosotros, que tenga un buen dia.")
    print("[INFO] Desconectado del servidor.\n")
