import socket
import datetime
import json
import sys
from dnslib import DNSRecord
import dnslib

def parse_dns_message(raw_data):
    # Usamos DNSRecord de dnslib para parsear el mensaje DNS
    dns_record = DNSRecord.parse(raw_data)

    # Extraemos la información clave
    qname = str(dns_record.q.qname) # dominio a consultar
    ancount = len(dns_record.rr)       # Resource Records (RRs) respondiendo la pregunta que haremo
    nscount = len(dns_record.auth)     # RRs que corresponden a una respuesta autorizada
    arcount = len(dns_record.ar)       # RRs con información adicional

    # Armar estructura con todas las secciones parseadas
    parsed = {
        "QNAME": qname, # dominio a consultar: example.com
        "ANCOUNT": ancount,
        "NSCOUNT": nscount,
        "ARCOUNT": arcount,
        "Answers": [str(rr) for rr in dns_record.rr],
        "Authority": [str(rr) for rr in dns_record.auth],
        "Additional": [str(rr) for rr in dns_record.ar],
    }

    return parsed

def resolver_redirigido(ip_destino, mensaje_consulta):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    sock.sendto(mensaje_consulta, (ip_destino, ROOT_SERVER_PORT))
    data, _ = sock.recvfrom(512)
    sock.close()
    return data
    

#recibe el mensaje de query en bytes obtenido desde el cliente
def resolver(mensaje_consulta):
    # a.- Envíe el mensaje query al servidor raíz de DNS y espere su respuesta. 
    # Se recomienda dejar la IP del servidor raíz en una variable global de su programa. 
    # La dirección del servidor raíz es la siguiente: 192.33.4.12 y el puerto es el correspondiente 
    # a servidores DNS.
    new_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   # Enviamos el mensaje al servidor raíz
    new_socket.sendto(mensaje_consulta, (ROOT_SERVER_ADDRESS, ROOT_SERVER_PORT))
    # Esperamos la respuesta del servidor raíz
    data, addr = new_socket.recvfrom(buff_size) # buffer de 4096 bytes
    # Parseamos el mensaje recibido
    mensaje_recv = parse_dns_message(data)
    dominio = mensaje_recv["QNAME"].rstrip('.')
    print(f"(debug) Consultando '{dominio}' a '.' con dirección IP '{ROOT_SERVER_ADDRESS}'")

    # Cerramos el socket
    # new_socket.close()
    #b.- Si el mensaje answer recibido tiene la respuesta a la consulta, es decir, 
    # viene alguna respuesta de tipo A en la sección Answer del mensaje, 
    # entonces simplemente haga que su función retorne el mensaje recibido.
    for rr_str in mensaje_recv.get("Answers", []):
        if " A " in rr_str:
            return data # Retornamos el mensaje recibido si tiene respuesta de tipo A

    #c.- Si la respuesta recibida corresponde a una delegación a otro Name Server, es decir, 
    # vienen respuestas de tipo NS en la sección Authority, revise si viene alguna respuesta 
    # de tipo A en la sección Additional.
    # Check for NS records in Authority section
    for auth_rr in mensaje_recv.get("Authority", []):
        if " NS " in auth_rr:
            # Check Additional section for A records
            for additional_rr in mensaje_recv.get("Additional", []):
                if " A " in additional_rr:
                    print(f"(debug) Consultando '{dominio}' a '{auth_rr.split()[-1]}' con dirección IP '{ip}'")
                    # Obtenemos la IP de la sección Additional 
                    ip = additional_rr.split()[-1]
                    # Enviamos la query al Name Server con la IP obtenida
                    print(f"[->] Redirigiendo a {ip} (glue record)")
                    return resolver_redirigido(ip, mensaje_consulta)
                    # return resolver(data)?
            # Si no encontramos una IP en Additional
            ns_name = auth_rr.split()[-1].rstrip('.') # Obtenemos un NS del Authority
            print(f"[->] Resolviendo IP de {ns_name}...")
            # use recursivamente su función para resolver la IP asociada al nombre de dominio del Name Server
            ns_query = DNSRecord.question(ns_name + ".").pack() # pack -> lo pasa a bytes
            ip_response = resolver(ns_query) # Implementar resolver_dns para obtener la IP del NS
            parsed_response = parse_dns_message(ip_response)
            for rr_str in parsed_response.get("Answers", []):
                if " A " in rr_str:
                    print(f"(debug) Consultando '{dominio}' a '{ns_name}' con dirección IP '{ip}'")
                    ip = rr_str.split()[-1]
                    print(f"[->] Redirigiendo a {ip} (resuelto recursivamente)")
                    return resolver_redirigido(ip, mensaje_consulta)
            # d. Si recibe algún otro tipo de respuesta simplemente ignórela.
            print("[X] No se pudo resolver la consulta: sin respuesta útil.")
            return None
    


    # for rr_str in mensaje_recv.get("Additional", []):
    #     if " A " in rr_str:
    #         # i.- Si encuentra una respuesta tipo A, entonces envíe la query del paso a) a la primera dirección IP contenida en la sección Additional.
    #         return resolver(mensaje_consulta)

    # i.- Si encuentra una respuesta tipo A, entonces envíe la query del paso a) a la primera dirección IP contenida en la sección Additional.
    # ii.- En caso de no encontrar alguna IP en la sección Additional, tome el nombre de un Name Server desde la sección Authority y use recursivamente su función para resolver la IP asociada al nombre de dominio del Name Server. Una vez obtenga la IP del Name Server, envíe la query obtenida en el paso a) a dicha IP. Una vez recibida la respuesta, vuelva al paso b).
# Función para setear el bit RA en la respuesta DNS
# De esta forma indicamos que el resolver puede hacer consultas recursivas
def set_ra_bit(dns_response_bytes):
    # Convertimos a bytearray mutable
    response = bytearray(dns_response_bytes)
    # Seteamos el bit RA (bit 7 del byte 3)
    response[3] |= 0b10000000  # o 0x80
    return bytes(response)


ROOT_SERVER_ADDRESS = "192.33.4.12"
ROOT_SERVER_PORT = 53

if __name__ == "__main__":
    # definimos el tamaño del buffer de recepción y la secuencia de fin de mensaje
    buff_size = 4096 #????
    end_of_message = "\n"

    new_socket_address = ('localhost', 8000)

    print('Creando socket - DNS Resolver')
    # armamos el socket
    # los parámetros que recibe el socket indican el tipo de conexión
    # socket.SOCK_STREAM = socket NO orientado a conexión
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    

    # le indicamos al server socket que debe atender peticiones en la dirección address
    # para ello usamos bind
    server_socket.bind(new_socket_address)

    # luego con listen (función de sockets de python) le decimos que puede
    # tener hasta 3 peticiones de conexión encoladas
    # si recibiera una 4ta petición de conexión la va a rechazar

    # nos quedamos esperando a que llegue una petición de conexión
    print('DNS Resolver http://localhost:8000 esperando clientes...')
    print()
    while True:

        request_test, addr = server_socket.recvfrom(buff_size)
        print("Mensaje recibido: ", request_test)
        print("Dirección del cliente: ", addr)

        # Después de recibir request_test
        parsed = parse_dns_message(request_test)
        print("Mensaje DNS parseado:")
        for key, value in parsed.items():
            print(f"{key}: {value}")

        response = resolver(request_test)
        # Si se logró resolver, se envía al cliente
        if response:
            response = set_ra_bit(response) # Seteamos el bit RA en la respuesta
            server_socket.sendto(response, addr)
            print(f"[✓] Respuesta enviada a {addr}")
        else:
            print("[X] No se pudo resolver la consulta.")

        # No cerramos el socket aquí para poder seguir recibiendo consultas
        # server_socket.close()
        # notar que la dirección que se imprime indica un número de puerto distinto al 5000
        print("\n\n") 
        print(f"Consulta procesada para {addr}")

        # seguimos esperando por si llegan otras conexiones


