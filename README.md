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
- **Asistente de voz** (`clap_spotify/assistant.py`): la PRIMERA vez que
  aplaudís en el día, además de la música, una voz te saluda por encima de
  la canción (que se baja de volumen mientras habla y vuelve a subir al
  terminar) diciéndote la hora, el día, el clima y tus tareas pendientes.
  Los aplausos siguientes ese mismo día solo controlan la música, sin
  repetir el saludo. Ver la sección **"Asistente de voz"** más abajo para
  configurarlo.

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

## Asistente de voz (saludo del primer aplauso del día)

Esto es opcional — si no configurás nada, el asistente igual va a saludarte
con la hora y el día (usando la voz por defecto de Windows), solo que sin
clima ni tareas. Para tener todo completo:

### 1. Clima (opcional)

1. Creá una cuenta gratis en [OpenWeatherMap](https://home.openweathermap.org/users/sign_up)
   (no pide tarjeta).
2. Una vez adentro, andá a la sección **"API keys"** y copiá la clave que te dan.
3. En tu `.env`, completá:
   ```
   WEATHER_CITY=Buenos Aires,AR
   WEATHER_API_KEY=la_clave_que_copiaste
   ```
4. **Importante**: las claves nuevas pueden tardar hasta 2 horas en
   activarse. Si al principio no dice el clima, no es un error tuyo — esperá
   un rato y probá de nuevo con `--simulate-clap --force-greeting` (ver más
   abajo).

### 2. Tareas pendientes (opcional)

El asistente lee en voz alta lo que tengas anotado en un archivo de texto.
Por defecto vive fuera de la carpeta del proyecto (para que no se pierda
si volvés a descargar el ZIP), en:
```
%APPDATA%\ClapSpotify\tasks.txt
```
Para crearlo/editarlo, con el proyecto activado (`venv\Scripts\activate`),
corré en PowerShell:
```
New-Item -ItemType Directory -Force "$env:APPDATA\ClapSpotify" | Out-Null
notepad "$env:APPDATA\ClapSpotify\tasks.txt"
```
Escribí una tarea por línea, guardá y cerrá. El asistente lee como máximo
`ASSISTANT_MAX_TASKS` (5 por defecto) para no hacer un discurso eterno.

### 3. Voz en español (recomendado)

Windows solo trae por defecto las voces del idioma con el que instalaste el
sistema. Si tu Windows está en español seguramente ya tenés una voz en
español instalada; si no, andá a **Configuración → Hora e idioma → Voz →
Agregar voces** y agregá "Español". Para ver qué voces tenés disponibles:
```
python -m clap_spotify.main --list-voices
```
Si no hay ninguna voz en español instalada, el asistente va a hablar con la
voz por defecto (probablemente en inglés) — sigue funcionando, solo que con
peor pronunciación del texto en español.

Por defecto el programa elige automáticamente una voz en español sin
importar si es masculina o femenina. Si querés elegir una voz específica
(por ejemplo, una masculina si tenés una instalada), corré
`--list-voices`, copiá el ID de la que te guste (la parte después de la
flecha `->`) y pegalo en tu `.env`:
```
ASSISTANT_VOICE_ID=el_id_que_copiaste
```

### Ajustar el volumen de la voz vs. la música

Si la voz se escucha muy baja comparada con la música, tenés dos perillas
en tu `.env` para ajustar esto (podés combinarlas):
- `ASSISTANT_SPEECH_VOLUME` (0.0 a 1.0): volumen de la voz en sí. Subilo a
  `1.0` (el máximo) si no está ya así.
- `ASSISTANT_DUCK_VOLUME_PERCENT` (0 a 100): a qué volumen baja Spotify
  mientras habla. Viene en `15` por defecto; bajalo a algo como `5` para
  que la música quede bien de fondo mientras se escucha el saludo.

Después de cambiar cualquiera de las dos, probá de nuevo con:
```
python -m clap_spotify.main --simulate-clap --force-greeting
```

### Probar el saludo sin esperar al día siguiente

El saludo completo (con clima y tareas) solo suena la primera vez que
aplaudís en el día. Para probarlo las veces que quieras mientras ajustás la
configuración:
```
python -m clap_spotify.main --simulate-clap --force-greeting
```

### Desactivarlo

Si no lo querés, poné `ASSISTANT_ENABLED=false` en tu `.env` — los aplausos
van a seguir controlando la música normalmente, sin ningún saludo.

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
python -m clap_spotify.main --list-voices          # ver voces de texto-a-voz instaladas
python -m clap_spotify.main --simulate-clap         # dispara la acción una vez, sin usar el micrófono
python -m clap_spotify.main --simulate-clap --dry-run  # igual, pero solo loggea qué haría (no abre nada)
python -m clap_spotify.main --simulate-clap --force-greeting  # prueba el saludo completo (hora/clima/tareas)
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
- **El asistente no dice nada, o habla en inglés** → correté
  `python -m clap_spotify.main --list-voices` para ver qué voces tenés
  instaladas; si no hay ninguna en español, instalá una (ver sección
  "Asistente de voz" más arriba). Si la lista da error, puede que falte el
  motor de texto-a-voz de Windows (poco común, reinstalar/actualizar
  Windows suele arreglarlo).
- **El asistente no dice el clima** → confirmá `WEATHER_CITY` y
  `WEATHER_API_KEY` en `.env`; si la clave es nueva, esperá hasta 2 horas a
  que se active. Podés ver el motivo exacto corriendo con
  `--log-level DEBUG`.
- **No repite el saludo aunque quiero probarlo de nuevo** → es esperado,
  solo saluda una vez por día. Usá `--simulate-clap --force-greeting` para
  forzarlo cuantas veces quieras mientras probás.

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
- Bajar el volumen de Spotify mientras habla el asistente ("ducking") solo
  funciona en Windows y requiere `pycaw` (ya incluido en `requirements.txt`
  para Windows). Si falla por lo que sea, el asistente igual habla, solo
  que se puede escuchar mezclado con la música a volumen normal.
