# Clap Spotify Controller

Escucha el micrófono de tu PC en segundo plano y, al detectar un aplauso,
abre (o enfoca) Spotify y reproduce "Should I Stay or Should I Go" de The Clash.

## Cómo funciona

- **Captura de audio**: `sounddevice` mantiene el micrófono abierto y entrega
  bloques de audio continuamente.
- **Detección de aplausos** (`clap_spotify/audio_listener.py`): cada bloque
  pasa por 4 filtros antes de considerarse un aplauso real, para evitar
  falsos positivos con ruido de fondo:
  1. **Amplitud**: el volumen (RMS) debe superar el piso de ruido ambiente
     calibrado al arrancar, multiplicado por un factor configurable.
  2. **Ataque súbito**: el pico debe ser mucho más fuerte que el volumen
     reciente (no un aumento gradual, como música subiendo de volumen).
  3. **Contenido en agudos**: un aplauso tiene energía distribuida en
     frecuencias altas (>2kHz); esto descarta golpes graves, portazos, etc.
  4. **Decaimiento**: un aplauso es un sonido corto que decae rápido. Si el
     sonido fuerte se sostiene varios bloques (TV, voz alta, música), se
     descarta.
  5. **Doble aplauso** (activado por defecto): incluso pasando los 4 filtros
     anteriores, no dispara la acción hasta detectar un **segundo** golpe
     similar dentro de una ventana corta de tiempo (por defecto entre 0.15s
     y 0.7s después del primero) — igual que los clásicos aparatos "clap
     on/clap off". Esto es clave en ambientes con ruido de fondo variable
     (un local, la calle, gente hablando): ahí, subir o bajar el umbral de
     volumen no alcanza, porque un ruido cualquiera puede parecer un
     aplauso puntual, pero es muy poco probable que se repita dos veces con
     el timing exacto de un aplauso doble. Se puede desactivar con
     `CLAP_REQUIRE_DOUBLE_CLAP=false` si estás en un ambiente silencioso y
     preferís reaccionar con un solo aplauso.
- **Acción** (`clap_spotify/spotify_controller.py` + `os_utils.py`): abre o
  enfoca la app de Spotify y lanza el URI `spotify:track:<id>` de la canción,
  lo que hace que el cliente de escritorio la reproduzca inmediatamente. Este
  mecanismo funciona con cuentas gratis o Premium y no requiere iniciar
  sesión con la API de Spotify.

## Instalación

Requiere Python 3.10+ y tener [Spotify](https://www.spotify.com/download/) instalado.

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

## Configuración

Copiá `.env.example` a `.env` y ajustá lo que necesites. Los valores por
defecto ya están pensados para funcionar razonablemente bien; lo único que
vale la pena revisar es la canción:

```bash
cp .env.example .env
```

### Verificar/fijar el URI exacto de la canción (recomendado)

El proyecto trae embebido por defecto `spotify:track:02DZxszCWyn3UivsWTblnq`,
encontrado por búsqueda pública para "Should I Stay or Should I Go" (The
Clash, álbum *Combat Rock*). **No está garantizado al 100%.** Para asegurarte
de que apunta a la versión que querés:

1. Abrí Spotify y buscá la canción.
2. Click derecho (o el botón "...") sobre la canción → **Compartir** →
   **Copiar URI de Spotify**.
3. Pegalo en `.env` como `SPOTIFY_TRACK_URI=spotify:track:XXXXXXXXXXXXXXXXXXXXXX`.

Si preferís que se resuelva automáticamente por nombre en vez de fijar un
URI, podés crear una app gratuita en el
[Spotify Developer Dashboard](https://developer.spotify.com/dashboard) y
completar `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` en `.env` — esto solo
se usa para *buscar* la canción, nunca para reproducirla (eso siempre pasa
por el cliente de escritorio).

## Uso

Permisos de micrófono (Windows): **Configuración → Privacidad y seguridad →
Micrófono**, asegurate de que el acceso al micrófono esté habilitado para
apps de escritorio/Python. (macOS: Preferencias del Sistema → Privacidad y
Seguridad → Micrófono. Linux: depende de PulseAudio/PipeWire, normalmente no
requiere permisos extra).

```bash
python -m clap_spotify.main
```

Al iniciar, calibra el ruido ambiente durante unos segundos (quedate en
silencio) y después queda escuchando. Dale **dos aplausos seguidos** (como
"clap-clap") y Spotify debería abrirse/enfocarse y empezar a reproducir la
canción. (Esto es porque `CLAP_REQUIRE_DOUBLE_CLAP` viene activado por
defecto — ver la sección "Cómo funciona" más arriba.)

### Opciones útiles

```bash
python -m clap_spotify.main --list-devices        # ver micrófonos disponibles
python -m clap_spotify.main --device 2             # usar un micrófono específico
python -m clap_spotify.main --simulate-clap         # dispara la acción una vez, sin usar el micrófono
python -m clap_spotify.main --simulate-clap --dry-run  # igual, pero solo loggea qué haría (no abre nada)
```

## Correr en segundo plano al iniciar Windows

Con el entorno virtual creado, usá el Programador de Tareas de Windows:

1. Abrí **Programador de Tareas** → **Crear tarea básica**.
2. Desencadenador: **Al iniciar sesión**.
3. Acción: **Iniciar un programa** →
   - Programa: `C:\ruta\al\proyecto\venv\Scripts\python.exe`
   - Argumentos: `-m clap_spotify.main`
   - Iniciar en: `C:\ruta\al\proyecto`
4. En las propiedades de la tarea, marcá "Ejecutar tanto si el usuario inició
   sesión como si no" solo si no necesitás ver la consola.

(macOS: se puede usar un `launchd` `.plist` con `ProgramArguments` apuntando
al mismo comando. Linux: un servicio `systemd --user` con `ExecStart`
apuntando al mismo comando.)

## Ajustar sensibilidad (falsos positivos / negativos)

Todas las variables están en `.env.example` con su explicación. Las más
relevantes si algo no anda bien:

- **No detecta aplausos reales** → bajá `CLAP_AMPLITUDE_MULTIPLIER` o
  `CLAP_MIN_HIGH_FREQ_RATIO`, o subí `CLAP_ATTACK_RATIO` un poco menos
  estricto (bajalo). También asegurate de estar dando dos aplausos con un
  ritmo natural (ni pegados ni muy separados) — la ventana por defecto es
  entre 0.15s y 0.7s; si te resulta incómoda, ajustá
  `CLAP_DOUBLE_CLAP_MIN_GAP_SECONDS`/`CLAP_DOUBLE_CLAP_MAX_GAP_SECONDS`.
- **Detecta ruidos que no son aplausos** (esto es lo más común en lugares
  con ruido de fondo, como un local) → **lo más efectivo es dejar
  `CLAP_REQUIRE_DOUBLE_CLAP=true`** (viene así por defecto): subir o bajar
  `CLAP_AMPLITUDE_MULTIPLIER` casi no ayuda en ambientes ruidosos, porque
  ese filtro compara contra el volumen *reciente*, no contra un volumen
  absoluto. Si aun con el doble aplauso activado sigue habiendo falsos
  positivos, subí también `CLAP_MIN_HIGH_FREQ_RATIO` o `CLAP_ATTACK_RATIO`.
- **Se dispara dos veces con un solo aplauso** (por el eco del propio
  parlante) → subí `CLAP_POST_TRIGGER_MUTE_SECONDS`.

## Desarrollo y tests

```bash
pip install -r requirements-dev.txt
pytest
```

Los tests de detección de aplausos usan audio sintético (silencio, ráfagas
de ruido blanco, tonos graves) y no requieren micrófono. Los tests de
Spotify usan mocks y no ejecutan procesos reales ni requieren Spotify
instalado.

## Limitaciones conocidas

- La detección de aplausos es sensible al hardware del micrófono y al ruido
  ambiente; puede necesitar ajuste fino de los umbrales en `.env`.
- Si no hay conexión a internet o Spotify no está logueado, el URI se
  lanzará igual pero la reproducción puede fallar silenciosamente (esto es
  un límite del propio cliente de Spotify, no de este script).
- El URI de canción por defecto debe confirmarse manualmente (ver sección de
  configuración) para garantizar que apunta a la versión exacta deseada.
