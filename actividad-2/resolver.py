import socket
import datetime
import json
import sys



if __name__ == "__main__":
    # definimos el tamaño del buffer de recepción y la secuencia de fin de mensaje
    buff_size = 5000 #????
    end_of_message = "\n"

    new_socket_address = ('localhost', 8000)

    print('Creando socket - DNS Resolver')
    # armamos el socket
    # los parámetros que recibe el socket indican el tipo de conexión
    # socket.SOCK_STREAM = socket NO orientado a conexión
    socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # le indicamos al server socket que debe atender peticiones en la dirección address
    # para ello usamos bind
    socket.bind(new_socket_address)

    # luego con listen (función de sockets de python) le decimos que puede
    # tener hasta 3 peticiones de conexión encoladas
    # si recibiera una 4ta petición de conexión la va a rechazar

    # nos quedamos esperando a que llegue una petición de conexión
    print('DNS Resolver http://localhost:8000 esperando clientes...')
    print()
    while True:

        request_test, addr = socket.recvfrom(buff_size)
        print("Mensaje recibido: ", request_test)
        print("Dirección del cliente: ", addr)

        # cerramos la conexión
        # notar que la dirección que se imprime indica un número de puerto distinto al 5000
        print("\n\n") 
        print(f"conexión con {addr} ha sido cerrada")

        # seguimos esperando por si llegan otras conexiones


