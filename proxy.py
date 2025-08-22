import socket
import datetime
import json
import sys

# -----------------------------------------------------------
# Utilidades iguales a las de tu server.py
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
# Lectura simple
# -----------------------------------------------------------

def recv_until(sock, marker: bytes, bufsize: int = 4096) -> bytes:
    data = b""
    while marker not in data:
        chunk = sock.recv(bufsize)
        if not chunk:
            break
        data += chunk
    return data

def recv_exact(sock, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = sock.recv(min(4096, n - len(data)))
        if not chunk:
            break
        data += chunk
    return data

def read_http_request_bytes(client_sock: socket.socket) -> bytes:
    head = recv_until(client_sock, b"\r\n\r\n")
    if not head:
        return b""
    header_text = head.decode("latin1")
    headers_part = header_text.split("\r\n\r\n", 1)[0]
    content_length = 0
    for line in headers_part.split("\r\n")[1:]:
        if line.lower().startswith("content-length:"):
            v = line.split(":", 1)[1].strip()
            if v.isdigit():
                content_length = int(v)
            break
    body = b""
    if content_length > 0:
        body = recv_exact(client_sock, content_length)
    return head + body

def read_http_response_bytes(upstream_sock: socket.socket) -> bytes:
    head = recv_until(upstream_sock, b"\r\n\r\n")
    if not head:
        return b""
    header_text = head.decode("latin1")
    headers_part = header_text.split("\r\n\r\n", 1)[0]
    content_length = None
    for line in headers_part.split("\r\n")[1:]:
        if line.lower().startswith("content-length:"):
            v = line.split(":", 1)[1].strip()
            if v.isdigit():
                content_length = int(v)
            break
    body = b""
    if content_length is None:
        while True:
            chunk = upstream_sock.recv(4096)
            if not chunk:
                break
            body += chunk
    else:
        body = recv_exact(upstream_sock, content_length)
    return head + body

# -----------------------------------------------------------
# Helpers de proxy HTTP (mínimos)
# -----------------------------------------------------------

def header_get(headers_dict, name):
    for k, v in headers_dict.items():
        if k.lower() == name.lower():
            return v
    return None

def header_del(headers_dict, name):
    target = None
    for k in list(headers_dict.keys()):
        if k.lower() == name.lower():
            target = k
            break
    if target is not None:
        del headers_dict[target]

def to_origin_form_and_target(request_bytes):
    # Convierte absolute-form -> origin-form y obtiene (host, port)
    text = request_bytes.decode("latin1")
    head, sep, body = text.partition("\r\n\r\n")
    lines = head.split("\r\n")
    start = lines[0]

    parsed = parse_HTTP_message(text)
    headers = parsed["headers"]

    parts = start.split(" ")
    method = parts[0] if len(parts) > 0 else "GET"
    target = parts[1] if len(parts) > 1 else "/"
    version = parts[2] if len(parts) > 2 else "HTTP/1.1"

    host = ""
    port = 80
    if target.startswith("http://"):
        rest = target[7:]
        s = rest.find("/")
        hostport = rest if s == -1 else rest[:s]
        path = "/" if s == -1 else rest[s:]
        if ":" in hostport:
            host, p = hostport.split(":", 1)
            if p.isdigit():
                port = int(p)
        else:
            host = hostport
        target = path
        if header_get(headers, "Host") is None:
            headers["Host"] = host if port == 80 else f"{host}:{port}"
    else:
        # origin-form ya; usa Host
        host_hdr = header_get(headers, "Host")
        if host_hdr:
            hv = host_hdr.strip()
            if ":" in hv:
                host, p = hv.split(":", 1)
                if p.isdigit():
                    port = int(p)
            else:
                host = hv
        if not target.startswith("/"):
            target = "/"

    # Quitar Proxy-Connection y forzar Connection: close (simpleza)
    header_del(headers, "Proxy-Connection")
    saw_connection = False
    for k in list(headers.keys()):
        if k.lower() == "connection":
            headers[k] = "close"
            saw_connection = True
    if not saw_connection:
        headers["Connection"] = "close"

    new_start = f"{method} {target} {version}"
    new_parsed = {"start_line": new_start, "headers": headers, "body": body}
    new_bytes = create_HTTP_message(new_parsed).encode("latin1")
    return new_bytes, host, port

# -----------------------------------------------------------
# PROXY HTTP genérico mínimo (para curl -x localhost:8000)
# -----------------------------------------------------------

if __name__ == "__main__":
    # (Opcional) JSON, mantenido por simetría con tu server.py
    # if len(sys.argv) >= 2 and sys.argv[1].endswith(".json"):
    #     with open(sys.argv[1], "r") as f:
    #         config = json.load(f)
    # else:
    #     config = {}

    proxy_address = ("localhost", 8000)  # el test usa -x localhost:8000

    print("Creando socket - PROXY HTTP")
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # opcional
    proxy_socket.bind(proxy_address)
    proxy_socket.listen(20)

    print(f"Proxy HTTP escuchando en http://{proxy_address[0]}:{proxy_address[1]}")
    print()

    while True:
        client_sock, client_addr = proxy_socket.accept()
        print(f"[PROXY] Cliente conectado: {client_addr}")

        raw_req = read_http_request_bytes(client_sock)
        if not raw_req:
            client_sock.close()
            print(f"[PROXY] (vacío) conexión cerrada: {client_addr}")
            continue

        # --- Opcional: ver request original ---
        # print(raw_req.decode("latin1"))

        new_req, dst_host, dst_port = to_origin_form_and_target(raw_req)
        if not dst_host:
            client_sock.close()
            print(f"[PROXY] (sin host) conexión cerrada: {client_addr}")
            continue

        upstream_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        upstream_sock.connect((dst_host, dst_port))
        upstream_sock.sendall(new_req)

        resp = read_http_response_bytes(upstream_sock)
        client_sock.sendall(resp)

        upstream_sock.close()
        client_sock.close()
        print(f"[PROXY] Conexión con {client_addr} finalizada\n")
