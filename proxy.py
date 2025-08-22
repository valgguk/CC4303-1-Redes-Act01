import socket
import datetime
import json
import sys

# Servidor HTTP : recibe mensajes de tipo HTTP (interpretar HEAD + BODY HTTP)

# estructura de datos
# - headers: diccionario para los encabezados
# - body: cuerpo del mensaje de tipo texto

# -- funciones de utilidad 

# función toma mensaje HTTP y lo transfiere a estruct datos -> Diccionario, texto
# recibe mensaje en STRING 
# -> start line ver casos (if Request ... else response)
def parse_HTTP_message(http_message):
    headers = {}                        # diccionario para los encabezados
    body = ""                           # cuerpo del mensaje de tipo texto
    lines = http_message.split("\r\n")  # dividir headers en líneas
    start_line = lines[0]                # primera línea (request line o status line)
    for i, line in enumerate(lines[1:], start=1):
        if line == "":
            body = "\r\n".join(lines[i+1:])
            break
        if ": " in line:
            header, value = line.split(": ", 1)
            headers[header] = value

    return {
        "start_line": start_line,
        "headers": headers,
        "body": body
    }

# función toma estructura de datos y lo convierte a mensaje HTTP
def create_HTTP_message(parsed):
    start_line = parsed["start_line"]
    headers = parsed["headers"]
    body = parsed["body"]

    header_lines = [f"{k}: {v}" for k, v in headers.items()]
    if body:
        return start_line + "\r\n" + "\r\n".join(header_lines) + "\r\n\r\n" + body
    else:
        return start_line + "\r\n" + "\r\n".join(header_lines) + "\r\n\r\n"



def build_http_response(username):
    body = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Mi Servidor Scala</title>
</head>
<body>
    <h1>Hola desde mi servidor Scala jejeje nooo</h1>
    <h3><a href="replace">El proxy es cuando</a></h3>
</body>
</html>"""

    body_bytes = body.encode("utf-8")

    # Fecha en formato HTTP (RFC 1123)
    date_str = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    headers = (
        "HTTP/1.1 200 OK\r\n"
        "Server: PythonSocket/0.1\r\n"
        f"Date: {date_str}\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        "Connection: close\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        f"X-ElQuePregunta: {username} \r\n"
        "\r\n"
    )

    return headers.encode("utf-8") + body_bytes




# --- funciones inspiradas en act no evaluada INSPIRACION ❗

# esta función se encarga de recibir el mensaje completo desde el cliente
# en caso de que el mensaje sea más grande que el tamaño del buffer 'buff_size', esta función va esperar a que
# llegue el resto. Para saber si el mensaje ya llegó por completo, se busca el caracter de fin de mensaje (parte de nuestro protocolo inventado)

def receive_full_message(connection_socket, buff_size, end_sequence):
    # recibimos la primera parte del mensaje
    recv_message = connection_socket.recv(buff_size)
    full_message = recv_message

    # verificamos si llegó el mensaje completo o si aún faltan partes del mensaje
    is_end_of_message = contains_end_of_message(full_message.decode(), end_sequence)

    # entramos a un while para recibir el resto y seguimos esperando información
    # mientras el buffer no contenga secuencia de fin de mensaje
    while not is_end_of_message:
        # recibimos un nuevo trozo del mensaje
        recv_message = connection_socket.recv(buff_size)

        # lo añadimos al mensaje "completo"
        full_message += recv_message

        # verificamos si es la última parte del mensaje
        is_end_of_message = contains_end_of_message(full_message.decode(), end_sequence)

    # removemos la secuencia de fin de mensaje, esto entrega un mensaje en string
    full_message = remove_end_of_message(full_message.decode(), end_sequence)

    # finalmente retornamos el mensaje
    return full_message

def contains_end_of_message(message, end_sequence):
    return message.endswith(end_sequence)


def remove_end_of_message(full_message, end_sequence):
    index = full_message.rfind(end_sequence)
    return full_message[:index]

# --- PROXY ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    config_file = sys.argv[1]
    with open(config_file, "r") as f:
        config = json.load(f)
    nombre_usuario = config.get("nombre", "Desconocido")

    proxy_address = ('localhost', 8000)
    print('Creando socket - Proxy HTTP')
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.bind(proxy_address)
    proxy_socket.listen(3)

    print('Proxy HTTP escuchando en http://localhost:8000/\n')

    while True:
        client_socket, client_address = proxy_socket.accept()
        print(f"[PROXY] Cliente conectado: {client_address}")

        # 1) Leer solicitud del cliente
        client_request = b""
        while True:
            chunk = client_socket.recv(4096)
            client_request += chunk
            if len(chunk) < 4096:
                break

        request_text = client_request.decode("utf-8", errors="replace")
        parsed = parse_HTTP_message(request_text)
        print("=== Request parseado ===")
        print(parsed["start_line"])
        print(parsed["headers"])

        # 2) Obtener host real desde los headers
        target_host = parsed["headers"].get("Host", "")
        target_port = 80

        # 3) Conectar al servidor real
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((target_host, target_port))

        # 4) Reenviar solicitud al servidor real
        server_socket.sendall(client_request)

        # 5) Leer respuesta del servidor real
        server_response = b""
        while True:
            chunk = server_socket.recv(4096)
            if not chunk:
                break
            server_response += chunk

        # 6) Reenviar respuesta al cliente
        client_socket.sendall(server_response)

        # 7) Cerrar sockets
        server_socket.close()
        client_socket.close()
        print(f"[PROXY] Conexión cerrada: {client_address}\n")