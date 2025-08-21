import socket
import datetime
import json
import sys

# -----------------------------------------------------------
# Utilidades iguales a las de tu server.py (para que coincida
# la estructura y puedas imprimir/inspeccionar si quieres)
# -----------------------------------------------------------

def parse_HTTP_message(http_message):
    headers = {}
    body = ""
    lines = http_message.split("\r\n")
    start_line = lines[0]
    for i, line in enumerate(lines[1:], start=1):
        if line == "":
            body = "\r\n".join(lines[i+1:])
            break
        if ": " in line:
            header, value = line.split(": ", 1)
            headers[header] = value
    return {"start_line": start_line, "headers": headers, "body": body}

def create_HTTP_message(parsed):
    start_line = parsed["start_line"]
    headers = parsed["headers"]
    body = parsed["body"]
    header_lines = [f"{k}: {v}" for k, v in headers.items()]
    if body:
        return start_line + "\r\n" + "\r\n".join(header_lines) + "\r\n\r\n" + body
    else:
        return start_line + "\r\n" + "\r\n".join(header_lines) + "\r\n\r\n"

# -----------------------------------------------------------
# Pequeñas utilidades de lectura para este proxy
# (sin ser ultra-robustas; suficientes para la tarea)
# -----------------------------------------------------------

def recv_until(sock, marker: bytes, bufsize: int = 4096) -> bytes:
    """
    Lee del socket hasta encontrar 'marker' (p.ej. b'\\r\\n\\r\\n').
    Devuelve los bytes leídos (incluye el marker).
    """
    data = b""
    while marker not in data:
        chunk = sock.recv(bufsize)
        if not chunk:
            break
        data += chunk
    return data

def recv_exact(sock, num_bytes: int) -> bytes:
    """
    Lee exactamente num_bytes del socket (bloqueante, simple).
    """
    data = b""
    while len(data) < num_bytes:
        chunk = sock.recv(min(4096, num_bytes - len(data)))
        if not chunk:
            break
        data += chunk
    return data

def read_http_request_bytes(client_sock: socket.socket) -> bytes:
    """
    Lee una petición HTTP completa del client socket:
    - Lee solamente los headers.
    - Si hay Content-Length, lee exactamente ese cuerpo.
    """
    head = recv_until(client_sock, b"\r\n\r\n")
    if not head:
        return b""

    # Intentar obtener Content-Length
    header_text = head.decode()  
    headers_part = header_text.split("\r\n\r\n", 1)[0]
    content_length = 0
    for line in headers_part.split("\r\n")[1:]:
        if line.startswith("content-length:"):
            try:
                content_length = int(line.split(":", 1)[1].strip())
            except ValueError:
                content_length = 0
            break

    body = b""
    if content_length > 0:
        body = recv_exact(client_sock, content_length)

    return head + body

def read_http_response_bytes(upstream_sock: socket.socket) -> bytes:
    """
    Lee una respuesta HTTP:
    - Lee hasta CRLFCRLF.
    - Si hay Content-Length, lee exactamente ese cuerpo.
    - Si no hay, lee hasta que el servidor cierre (sirve porque tu server.py
      manda 'Connection: close').
    """
    head = recv_until(upstream_sock, b"\r\n\r\n")
    if not head:
        return b""

    header_text = head.decode("latin1")
    headers_part = header_text.split("\r\n\r\n", 1)[0]
    content_length = None
    for line in headers_part.split("\r\n")[1:]:
        if line.lower().startswith("content-length:"):
            try:
                content_length = int(line.split(":", 1)[1].strip())
            except ValueError:
                content_length = 0
            break

    body = b""
    if content_length is None:
        # Leer hasta cierre de conexión
        while True:
            chunk = upstream_sock.recv(4096)
            if not chunk:
                break
            body += chunk
    else:
        body = recv_exact(upstream_sock, content_length)

    return head + body

# -----------------------------------------------------------
# PROXY (estructura similar al server.py de la Parte 1)
# -----------------------------------------------------------

if __name__ == "__main__":
    # (Opcional) archivo JSON, por similitud con tu server.py
    # No lo usamos para la lógica del proxy, pero lo dejamos para mantener estructura.
    if len(sys.argv) >= 2 and sys.argv[1].endswith(".json"):
        config_file = sys.argv[1]
        with open(config_file, "r") as f:
            config = json.load(f)
    else:
        config = {}

    # Dónde escucha el PROXY (cliente se conecta aquí)
    proxy_address = ("localhost", 8080)

    # Dónde está el servidor real (tu server.py de la parte 1)
    upstream_address = ("localhost", 8000)

    print("Creando socket - PROXY")
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy_socket.bind(proxy_address)
    proxy_socket.listen(3)

    print(f"Proxy escuchando en http://{proxy_address[0]}:{proxy_address[1]}")
    print(f"Reenviando al servidor real en {upstream_address[0]}:{upstream_address[1]}")
    print()

    while True:
        client_sock, client_addr = proxy_socket.accept()
        print(f"[PROXY] Cliente conectado: {client_addr}")

        # 1) Leer request completo del cliente (headers + body si hay)
        request_bytes = read_http_request_bytes(client_sock)
        if not request_bytes:
            client_sock.close()
            print(f"[PROXY] (vacío) conexión cerrada: {client_addr}")
            continue

        # (Opcional) mostrar parseo del request para debug, manteniendo tu estilo
        try:
            parsed_req = parse_HTTP_message(request_bytes.decode("latin1"))
            print("=== Request (parseado en el PROXY) ===")
            print(parsed_req)
            print()
        except Exception:
            pass  # si falla el decode, no importa: el proxy sólo reenvía bytes

        # 2) Conectar con el servidor real
        upstream_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        upstream_sock.connect(upstream_address)

        # 3) Enviar request al servidor real
        upstream_sock.sendall(request_bytes)

        # 4) Recibir respuesta completa del servidor real
        response_bytes = read_http_response_bytes(upstream_sock)

        # (Opcional) mostrar parseo de la respuesta
        try:
            parsed_resp = parse_HTTP_message(response_bytes.decode("latin1"))
            print("=== Response (parseada en el PROXY) ===")
            print(parsed_resp["start_line"])
            print(parsed_resp["headers"])
            print()
        except Exception:
            pass

        # 5) Reenviar respuesta al cliente tal cual
        client_sock.sendall(response_bytes)

        # 6) Cerrar ambos lados de esta vuelta
        upstream_sock.close()
        client_sock.close()
        print(f"[PROXY] Conexión con {client_addr} finalizada\n")
