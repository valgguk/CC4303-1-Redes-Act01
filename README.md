# CC4303-1-Redes-Act01  
> **Proxy de filtración de contenido web**

### Integrantes

- Pablo Osorio N.
- Valentina Ramírez J.

## Parte 1

Partiremos creando y probando un servidor HTTP. Para construir su servidor puede usar como guía* el ejemplo de comunicación orientada a conexión `tcp_socket_server.py` visto en el módulo 1. Recuerde que para que un servidor sea en efecto un servidor HTTP, debe ser capaz de recibir mensajes HTTP, es decir, debe ser capaz de leer e interpretar HEAD + BODY HTTP.

## Parte 2

Ahora que ya tenemos listo nuestro servidor HTTP vamos a modificarlo para convertirlo en un proxy. Nuestro proxy tendrá dos funcionalidades principales:

- Bloquear tráfico hacia páginas no permitidas (como un control parental)
- Reemplazar contenido inadecuado (reemplazo del string A con el string B)

### Probar el servidor con `curl`

Si se testea código en una red con proxy (ej. proxy institucional), `curl` puede no llegar a `localhost` y responder con **403 Forbidden**.  
Para evitarlo, usa la opción `--noproxy`:

```bash
curl -i --noproxy localhost http://localhost:8000
```

## Pruebas para garantizar todos los puntos de la tarea en curl 

```bash
curl -i http://localhost/build -x localhost:8000
```

```bash
curl -i http://localhost/case1 -x localhost:8000
```

```bash
curl -i http://localhost/case2 -x localhost:8000
```

```bash
curl http://cc4303.bachmann.cl/ -x localhost:8000
```

```bash
curl http://cc4303.bachmann.cl/secret -x localhost:8000
```

```bash
curl -i http://www.dcc.uchile.cl/ -x localhost:8000
```

```bash
curl http://cc4303.bachmann.cl/replace -x localhost:8000
```


### Manejo de sitios bloqueados y errores de conexión - Resumir para el informe ! 😃

El proxy fue diseñado para soportar únicamente **HTTP**, no HTTPS, por requerimiento del proyecto. Muchas páginas modernas (como `www.dcc.uchile.cl`) redirigen automáticamente de HTTP a HTTPS, lo que puede causar errores si el proxy intenta establecer la conexión.

Para manejar estos casos y asegurar estabilidad, se tomaron las siguientes decisiones de diseño:

1. **Detección de HTTPS**  
   - Si la solicitud del cliente utiliza el método `CONNECT` (indicativo de HTTPS), el proxy inmediatamente responde con un código `403 Forbidden`.
   - Esto evita que el proxy intente establecer un túnel HTTPS, que no está soportado.

2. **Manejo de redirecciones y hosts inaccesibles**  
   - Cuando el proxy intenta conectarse a un servidor HTTP real, se envuelve la conexión en un bloque `try-except` para capturar errores de DNS o problemas de resolución de hostname.
   - Si ocurre un error, el proxy devuelve un `403 Forbidden` al cliente en lugar de cerrarse inesperadamente.
   - Esto asegura que el proxy nunca se caiga por solicitudes a páginas que automáticamente redirigen a HTTPS o cuyos hostnames no existen.

Esta estrategia garantiza que el proxy cumpla con los requerimientos del proyecto, proporcionando bloqueo efectivo de sitios y palabras prohibidas, manteniendo la estabilidad del servidor en todo momento.


