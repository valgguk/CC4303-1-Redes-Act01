# CC4303-1-Redes-Act01  
**Proxy de filtración de contenido web**

### Probar el servidor con `curl`

Si estás en una red con proxy (ej. proxy institucional), `curl` puede no llegar a `localhost` y responder con **403 Forbidden**.  
Para evitarlo, usa la opción `--noproxy`:

```bash
curl -i --noproxy localhost http://localhost:8000

