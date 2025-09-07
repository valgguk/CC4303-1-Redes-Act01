import socket
import datetime
import json
import sys
from dnslib import DNSRecord
import dnslib
from dnslib.dns import QTYPE

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

# Función para actualizar la caché de los 3 dominios más frecuentes
def actualizar_cache(dominio, data):
    ultimas_20_consultas.append(dominio)
    if len(ultimas_20_consultas) > 20:
        ultimas_20_consultas.pop(0)

    conteo = {}
    for dom in ultimas_20_consultas:
        conteo[dom] = conteo.get(dom, 0) + 1
    # Obtener los 3 dominios más frecuentes y actualizar la caché
    top3 = sorted(conteo.items(), key=lambda item: item[1], reverse=True)[:3]
    cache_frecuentes.clear()
    for dom, _ in top3:
        cache_frecuentes[dom] = data

#recibe el mensaje de query en bytes obtenido desde el cliente
def resolver(mensaje_consulta, server_ip=None):
    # a.- Envíe el mensaje query al servidor raíz de DNS y espere su respuesta. 
    # Se recomienda dejar la IP del servidor raíz en una variable global de su programa. 
    # La dirección del servidor raíz es la siguiente: 192.33.4.12 y el puerto es el correspondiente 
    # a servidores DNS.
    # Parseamos la consulta para obtener el dominio
    dns_query = parse_dns_message(mensaje_consulta)
    dominio = dns_query["QNAME"].rstrip('.')
    # Para poder aplicar recursividad, fue necesario agregar los parámetros server_ip y server_name
    # Si no se especifica server_ip, usamos el servidor raíz
    if server_ip is None:
        server_ip = ROOT_SERVER_ADDRESS
        # Verificar si está en caché ANTES de consultar servidores DNS
        if dominio in cache_frecuentes:
            print(f"(debug) [CACHÉ] Respondiendo '{dominio}' desde caché")
            return cache_frecuentes[dominio]
    
    print(f"(debug) Consultando '{dominio}' a '.' con dirección IP '{ROOT_SERVER_ADDRESS}'")
    new_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   # Enviamos el mensaje al servidor raíz
    new_socket.sendto(mensaje_consulta, (server_ip, ROOT_SERVER_PORT)) # server_ip -> ROOT_SERVER_ADDRESS
    # Esperamos la respuesta del servidor raíz
    data, addr = new_socket.recvfrom(buff_size) # buffer de 4096 bytes
    # Parseamos el mensaje recibido
    mensaje_recv = parse_dns_message(data)
    #b.- Si el mensaje answer recibido tiene la respuesta a la consulta, es decir, 
    # viene alguna respuesta de tipo A en la sección Answer del mensaje, 
    # entonces simplemente haga que su función retorne el mensaje recibido.
    for rr_str in mensaje_recv.get("Answers", []):
        if " A " in rr_str:
            # Agregar dominio a la lista de últimas consultas (máx 20)
            actualizar_cache(dominio, data)
            return data # Retornamos el mensaje recibido si tiene respuesta de tipo A

    #c.- Si la respuesta recibida corresponde a una delegación a otro Name Server, es decir, 
    # vienen respuestas de tipo NS en la sección Authority, revise si viene alguna respuesta 
    # de tipo A en la sección Additional.
    # Revisamos la sección Authority para ver si hay un NS
    for auth_rr in mensaje_recv.get("Authority", []):
        if " NS " in auth_rr: # Si hay un NS en Authority
            # Revisamos la sección Additional para ver si hay una IP para ese NS
            for additional_rr in mensaje_recv.get("Additional", []):
                if " A " in additional_rr: # Si hay una IP en Additional
                    # i.- Si encuentra una respuesta tipo A, entonces envíe la query del paso a) a la primera dirección IP contenida en la sección Additional.
                    # Obtenemos la IP de la sección Additional 
                    ip = additional_rr.split()[-1]
                    print(f"(debug) Consultando '{dominio}' a '{auth_rr.split()[-1]}' con dirección IP '{ip}'")
                    # Enviamos la query al Name Server con la IP obtenida
                    return resolver(mensaje_consulta, ip)
            # Si no encontramos una IP en Additional
            # ii.- En caso de no encontrar alguna IP en la sección Additional, tome el nombre de un Name Server desde la sección Authority y use recursivamente su función para resolver la IP asociada al nombre de dominio del Name Server. Una vez obtenga la IP del Name Server, envíe la query obtenida en el paso a) a dicha IP. Una vez recibida la respuesta, vuelva al paso b).
            ns_name = auth_rr.split()[-1].rstrip('.') # Obtenemos un NS del Authority
            # use recursivamente su función para resolver la IP asociada al nombre de dominio del Name Server
            ns_query = DNSRecord.question(ns_name + ".").pack() # pack -> lo pasa a bytes
            ip_response = resolver(ns_query) # Resolver para obtener la IP del NS
            parsed_response = parse_dns_message(ip_response)
            for rr_str in parsed_response.get("Answers", []):
                if " A " in rr_str:
                    # Obtenemos la IP del NS resuelto
                    ip = rr_str.split()[-1]
                    print(f"(debug) Consultando '{dominio}' a '{ns_name}' con dirección IP '{ip}'")
                    return resolver(mensaje_consulta, ip)
            # d. Si recibe algún otro tipo de respuesta simplemente ignórela.
            return None


# Crear respuesta limpia manteniendo el ID de la consulta original
def crear_respuesta_limpia(mensaje_consulta, respuesta_completa):
    # Parsear ambos mensajes con dnslib
    query = DNSRecord.parse(mensaje_consulta)
    full_response = DNSRecord.parse(respuesta_completa)
    
    # Copiar solo las respuestas tipo A
    for rr in full_response.rr:
        if rr.rtype == QTYPE.A:
            query.add_answer(rr)
    
    # Configurar flags
    query.header.qr = 1
    query.header.rd = 1  
    query.header.ra = 1
    
    # Crear respuesta limpia
    clean_response = query.pack()
    
    # Mantener el Transaction ID original para cuando usamos
    original_id = mensaje_consulta[:2]  # Primeros 2 bytes = Transaction ID
    response = bytearray(clean_response)
    response[0:2] = original_id         # Sobrescribimos el ID en la respuesta
    return bytes(response)

ROOT_SERVER_ADDRESS = "192.33.4.12"
ROOT_SERVER_PORT = 53

# Lista simple para guardar las últimas 20 consultas
ultimas_20_consultas = []

# Diccionario que almacenará las respuestas DNS en caché (solo para los 3 dominios más frecuentes)
cache_frecuentes = {}

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
            # Crear respuesta limpia (incluye mantener Transaction ID)
            clean_response = crear_respuesta_limpia(request_test, response)
            server_socket.sendto(clean_response, addr)
            print(f"[✓] Respuesta enviada a {addr}")
        else:
            print("[X] No se pudo resolver la consulta.")

        # No cerramos el socket aquí para poder seguir recibiendo consultas
        # server_socket.close()
        # notar que la dirección que se imprime indica un número de puerto distinto al 5000
        print("\n\n") 
        print(f"Consulta procesada para {addr}")

        # seguimos esperando por si llegan otras conexiones


