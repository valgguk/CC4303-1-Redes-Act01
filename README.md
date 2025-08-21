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

