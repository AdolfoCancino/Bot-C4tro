# Bot-C4tro — Bot Estadístico para Discord

Bot modular en Python que publica un panel de metas y **edita el mismo mensaje**
cuando cambian las estadísticas. La configuración por servidor, sus metas y el
ID del panel se conservan en SQLite, incluso después de reiniciar el proceso.

## Estadísticas incluidas

| Estadística | Meta inicial | Fuente |
| --- | ---: | --- |
| Personas en el servidor | 1000 | Total de miembros de Discord, incluidos bots |
| Boosts | 6 | Boosts activos, no cantidad de usuarios que dan boost |
| Raptors | 10 | Miembros con el rol que selecciones |
| Ceras | 7 | Miembros con el rol que selecciones |
| Carnos | 5 | Miembros con el rol que selecciones |
| Spinos | 3 | Miembros con el rol que selecciones |
| T-rex | 2 | Miembros con el rol que selecciones |
| Deinosuchus | 1 | Miembros con el rol que selecciones |

El conteo por rol representa usuarios de Discord, no criaturas detectadas en un
juego. Un miembro con varios roles cuenta una vez en cada estadística asociada.
El bot no asigna roles: los cuenta cuando se asignan o retiran. Las estadísticas
sin rol configurado muestran un aviso en lugar de un cero engañoso.

## 1. Crear e invitar el bot

1. En [Discord Developer Portal](https://discord.com/developers/applications), crea
   una aplicación y su bot. Guarda el token únicamente en `.env` o en el gestor
   de secretos del alojamiento; no lo publiques ni lo pegues en el chat.
2. En **Bot → Privileged Gateway Intents**, activa **Server Members Intent**.
   No se necesita Message Content Intent ni Presence Intent.
3. En **OAuth2 → URL Generator**, selecciona los scopes `bot` y
   `applications.commands`. Dale estos permisos en el canal del panel:
   **View Channels**, **Send Messages**, **Embed Links** y **Read Message History**.
   No necesita Administrador ni Gestionar roles.
4. Abre la URL generada e invítalo al servidor.

Para bots verificados en muchos servidores, Discord puede exigir aprobación del
intent de miembros. Es necesario para contar roles de forma fiable.

## 2. Instalar y ejecutar

Requisitos: Python 3.12+ y [uv](https://docs.astral.sh/uv/).
Desde el directorio de este repositorio:

```bash
uv sync --frozen
cp .env.example .env
```

Edita `.env`:

```dotenv
DISCORD_TOKEN=tu_token_privado
DISCORD_GUILD_ID=ID_DE_TU_SERVIDOR
DATABASE_PATH=data/bot.sqlite3
```

`DISCORD_GUILD_ID` es opcional. Durante el desarrollo permite registrar los
comandos directamente en ese servidor. Para un bot en varios servidores, déjalo
vacío y reinicia; los comandos globales pueden tardar en aparecer. Al pasar a
globales, retira los comandos de prueba de ámbito servidor para evitar duplicados.

```bash
uv run --frozen python -m bot
```

Mantén el proceso encendido para recibir eventos. Conserva `data/` en un volumen
persistente si lo ejecutas en contenedores. Perder SQLite implica perder la
configuración y el vínculo con el mensaje publicado. No ejecutes dos instancias
simultáneas para el mismo bot. Ejecuta desde el directorio del proyecto, pues
la ruta predeterminada de SQLite es relativa a ese directorio.

## 3. Configurar desde Discord

Los comandos `/metas` requieren **Gestionar servidor**, comprobado también al
ejecutarlos. Las respuestas de configuración solo son visibles para quien usa
el comando; el panel publicado es visible en su canal.

| Comando | Uso |
| --- | --- |
| `/metas publicar` | Publicar el panel en el canal de texto actual. Si ya existe, actualizarlo y devolver su enlace. |
| `/metas rol estadistica:Raptors rol:@Raptor` | Vincular una criatura con un rol. Repetir para cada criatura. |
| `/metas objetivo estadistica:Boosts cantidad:6` | Cambiar una meta sin alterar su contador ni fuente. |
| `/metas ver` | Consultar todas las estadísticas sin publicar otro mensaje. |
| `/metas actualizar` | Solicitar una actualización inmediata del panel. |
| `/metas valor estadistica:Raptors cantidad:3` | Usar un valor manual en lugar de un rol; es opcional. Volver a `/metas rol` restaura el conteo automático. |

Los nombres de estadísticas se seleccionan en el menú del comando. Primero
vincula los seis roles y ejecuta `/metas publicar` en el canal deseado.

Los eventos se agrupan en ciclos de 10 segundos para evitar editar el mensaje
por cada cambio individual; además hay una revisión cada 5 minutos. Al reiniciar
se recuperan el panel y la configuración. Las bajas y la retirada de boosts o
roles también reducen los contadores. Las metas cumplidas muestran ✅ y el
contador real puede superar la meta; la barra se limita al 100 %.

Si borras el mensaje o el canal, usa `/metas publicar` de nuevo. Para mover el
panel, elimina el mensaje anterior y publica en otro canal. Los errores de
permisos se registran y se reintentan sin descartar la configuración. Si un rol
se elimina, el panel lo indica y puedes seleccionar otro con `/metas rol`.

## Estructura y ampliación

```text
bot/
  __main__.py           # Entrada: python -m bot
  client.py             # Cliente, carga de extensiones y errores
  config.py             # Variables de entorno
  metrics.py            # Catálogo de estadísticas y metas iniciales
  storage.py            # Persistencia SQLite aislada por servidor
  presentation.py       # Aspecto del panel
  boards.py             # Publicación y actualización del mismo mensaje
  cogs/
    goals.py            # Comandos /metas
    tracking.py         # Eventos y ciclo de actualización
  providers/
    discord_stats.py   # Miembros, boosts y roles
    manual.py          # Valores manuales
tests/                  # Pruebas sin token ni conexión a Discord
```

### Agregar una función desde otro archivo

Crea, por ejemplo, `bot/cogs/saludo.py`. Los módulos públicos de `cogs/` se cargan
al iniciar; no hace falta editar `client.py`:

```python
import discord
from discord import app_commands
from discord.ext import commands


class Saludo(commands.Cog):
    @app_commands.command(description="Saludar al bot")
    async def hola(self, interaction: discord.Interaction):
        await interaction.response.send_message("¡Hola!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Saludo())
```

Reinicia el bot para cargar y sincronizar el comando nuevo.

### Agregar otra estadística o fuente

Para otra estadística basada en roles, añade una entrada `Metric` a
`bot/metrics.py`, con clave única, etiqueta, meta y fuente `"role"`. Reinicia y
configura su rol con `/metas rol`. SQLite incorpora las nuevas métricas sin
restablecer las existentes. Los menús actuales admiten hasta 25 estadísticas;
si amplías más, sustituye las opciones fijas por autocompletado.

Para una fuente diferente, crea un archivo en `bot/providers/` y registra una
función usando `@register("mi_fuente")`. Recibe `(guild, goal)` y devuelve un entero
no negativo; puede lanzar `DataUnavailable` si faltan datos. Usa ese nombre de
fuente en el catálogo. El módulo se descubre automáticamente. Las funciones de
lectura son síncronas y no deben bloquear: para una API externa, usa una tarea
asíncrona en un Cog que mantenga un caché y un proveedor que lo lea. Al actualizar
el caché, llama `bot.boards.mark_dirty(guild_id)`.

## Validación local

```bash
uv sync --frozen --group dev
uv run --frozen python -m pytest
uv run --frozen ruff check .
uv run --frozen ruff format --check .
```

Las pruebas cubren persistencia y aislamiento entre servidores, conteo por roles,
miembros y boosts, permisos de comandos, carga de módulos, publicación y edición
del panel, recuperación de mensajes eliminados y reintentos tras fallos.
Usan dobles de Discord; la conexión real requiere tu aplicación y token.

Para comprobarlo en tu servidor: publica el panel, asigna y retira un rol a un
miembro, confirma el cambio en unos 10 segundos y reinicia el proceso para
comprobar que actualiza el mismo mensaje.

## Problemas frecuentes

- **Falta DISCORD_TOKEN:** crea `.env` a partir del ejemplo e introduce el token.
- **PrivilegedIntentsRequired / código 4014:** activa Server Members Intent en
  el portal de Discord y reinicia.
- **Los comandos no aparecen:** revisa el scope `applications.commands`, el ID
  del servidor, los permisos del usuario y los registros de sincronización.
- **El panel espera miembros:** el bot está cargando la lista completa. Si no
  termina, revisa el intent y la conectividad con el Gateway de Discord.
- **Errores de permisos:** revisa los permisos efectivos del bot en ese canal,
  incluidas las sobrescrituras por rol.
- **Alojamiento con red restringida:** permite `discord.com` para la API y
  `gateway.discord.gg` para WebSocket; la instalación usa `pypi.org` y
  `files.pythonhosted.org`. El cliente debe poder mantener HTTPS/WebSocket hacia
  Discord; no desactives la verificación TLS.

El bot respeta `https_proxy` / `HTTPS_PROXY` si tu alojamiento usa un proxy;
esa conexión también debe permitir el Gateway WebSocket de Discord.
