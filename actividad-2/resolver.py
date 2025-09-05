import socket
import datetime
import json
import sys
import dnslib

def parse_dns_message(raw_data):
    # Parsear el mensaje DNS recibido en formato bytes
    dns_record = dnslib.DNSRecord.parse(raw_data)

    # Extraer información clave
    qname = str(dns_record.q.qname)
    ancount = len(dns_record.rr)       # Respuestas (Answer)
    nscount = len(dns_record.auth)     # Servidores de autoridad (NS)
    arcount = len(dns_record.ar)       # Sección adicional (Additional)

    # Armar estructura con todas las secciones parseadas
    parsed = {
        "QNAME": qname,
        "ANCOUNT": ancount,
        "NSCOUNT": nscount,
        "ARCOUNT": arcount,
        "Answers": [str(rr) for rr in dns_record.rr],
        "Authority": [str(rr) for rr in dns_record.auth],
        "Additional": [str(rr) for rr in dns_record.ar],
    }

    return parsed

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

        # Después de recibir request_test
        parsed = parse_dns_message(request_test)
        print("Mensaje DNS parseado:")
        for key, value in parsed.items():
            print(f"{key}: {value}")

        # cerramos la conexión
        # notar que la dirección que se imprime indica un número de puerto distinto al 5000
        print("\n\n") 
        print(f"conexión con {addr} ha sido cerrada")

        # seguimos esperando por si llegan otras conexiones


