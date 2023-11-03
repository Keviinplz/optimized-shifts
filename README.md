# Optimized Shifts

Librería solución escrita en Python para prueba técnica de NeuralWorks.

Consta de un servicio tipo API REST, una cola de procesamiento en Celery y un websocket para notificar cuando el procesamiento se ha completado.

## Contexto

Se requiere apoyar con la creación de turnos entre personas con viajes similares. Se ha proporciado un archivo `.csv` con una muestra de los datos a considerar. Se ha requerido:

1. Procesos automatizados para ingerir y almacenar datos **bajo demanda**
    - Se requiere agrupar los viajes que son similares en terminos de origen, destino y hora del día.
2. Servicio que proporcione:
    - Promedio semanal de la cantidad de viajes para un área definida por un bounding box y la región.
    - Informe de la ingesta de datos **sin utilizar polling**.
3. Solución escalabre a **100 millones de entradas**.
4. Solución escrita en **Python** usando una base de datos **sql**.
5. **Incluir contenedores** en la solución, dibujar como configurar la aplicación en **GCP**

## Supuestos

Dada las instrucciones del challenge, se consideraron los siguientes supuestos:

1. Los datos pueden cargarse más de una vez (se puede inicializar con un `.csv` pero se espera poder almacenar más datos en el futuro).
    - Bajo este supuesto, se implementó dos formas de poder agregar nuevos datos: A través de archivos (`.csv` con el esquema propuesto en la muestra proporcionada), y vía `POST` a una `API`.  
2. Se asume como servicio una API REST:
    - Así la petición al promedio semanal se hace a través de la API, y las notificaciones respecto a la ingesta de datos se hacen a través de un websocket (así evitamos polling).

## Resumen General de los Hitos

- 🟡 Procesos automatizados para ingerir y almacenar datos bajo demanda:
    - El usuario debe gatillar el proceso mediante una petición `POST` con la ubicación del archivo, esto es intencional puesto que se busca imitar el comportamiento del programa ante un evento de procesar un archivo con su ubicación. Es fácilmente escalable a la nube usando `Pub/Sub Notifications` de `GCP`. Así gatillamos un `Cloud Function` con el procesado cuando se cree un nuevo archivo en el bucket.
    - No se realizó la agrupación. Esto fue en honor al tiempo debido a que no alcancé a pensar en una forma de almacenar la agrupación en la base de datos. Llegué a la siguiente consulta:

    ```sql
    -- Esta consulta retorna la agrupación solicitada, es decir, con esto puedo saber la cantidad de viajes similares agrupados por una cierta distancia a una cierta hora, pero pierdo la información de CUALES son los viajes agrupados.

    -- @Distance: Distancia máxima en la que los viajes deben estar para considerarse similares
    -- @Timelapse: Tiempo máximo en lo que los viajes pueden estar distanciados para considerarse similares

    -- Por ejemplo, podríamos considerar que un viaje es similar a otro si
    -- @Distance es 0.5 (KM) y @Timelapse son 300 (segundos)
    SELECT region, ST_ClusterWithin(v_trip::geometry, @Distance) 
    FROM (
        SELECT id, region, origin - destination AS v_trip, 'timestamp', source, SUM(nearest) OVER (ORDER BY t ASC) AS time_group
        FROM (
            SELECT dts.*, CASE WHEN dt > @Timelapse THEN 1 ELSE 0 END AS nearest
            FROM (
                    SELECT *, 'timestamp' AS t, lag('timestamp') OVER (ORDER BY 'timestamp' ASC) AS t_prev,
                        extract(epoch FROM 'timestamp' - lag('timestamp') OVER (ORDER BY 'timestamp' ASC)) AS dt
                    FROM travels
            ) dts
        ) AS nearest_group
    ) AS t_group
    GROUP BY region, time_group
    ORDER BY region
    ```
    Estuve manejando algunas soluciones como la creación de una vista materializada en postgres que se fuera actualizando cada vez que se insertara un viaje, pero hacer esto supone un costo muy alto y no soluciona el problema de saber cuales fueron los viajes agrupados.

    Por lo que decidí no implementarlo, sin embargo lo adjunto acá.
- 🟢 Servicio que proporcionen el promedio semanal de la cantidad de viajes para un área definida por un bounding box y la región, y un informe de la ingesta de datos **sin utilizar polling**.
    - Realizado con exito via solución tipo `API` en conjunto con `Websockets` para la notificación de la ingesta de datos.
- 🟢 Solución escalabre a **100 millones de entradas**.
    - El procesamiento de datos (ingesta de datos) puede ser colocada en una `Cloud Function`, a su vez que la `API`. Por lo que soluciona el problema del escalado.
- 🟢 Solución escrita en **Python** usando una base de datos **sql**.
- 🟢 **Incluir contenedores** en la solución, dibujar como configurar la aplicación en **GCP**
    - La descripción de los contenedores se encuentra más abajo, se adjunta a continuación diagrama de configuración en **GCP**:

## Levantamiento de la app

Se debe contar con `docker` y `docker compose` instalados en la máquina a ejecutar.

En este repositorio se encuentran todos los archivos para poder ejecutar la aplicación.

Solo se debe crear un archivo `.env` con la siguiente información:

```bash
BROKER_URL="redis://redis:6379/0"
POSTGRES_HOST="postgres"

POSTGRES_USER="cualquier_usuario"
POSTGRES_PASSWORD="cualquier_password"
POSTGRES_DB="cualquier_nombre_para_la_db"
```

Y guardarlo en la carpeta raiz del repositorio.

Finalmente levantar el proyecto con `docker compose up -d`

## Descripción de la solución

La solución contempla una API para consultar las estadisticas solicitadas, una cola de procesamiento (celery) para procesar los archivos y almacenarlos en la base de datos, y un websocket para el notificado del procesamiento.

Específicamente la solución emplea los siguientes servicios:

- API: Proporciona un endpoint para consultar el promedio semanal solicitado, a su vez que proporciona un endpoint para subir archivos via `.csv` (que delega al servicio de Celery retornando una ID para seguir el estado del procesamiento) y un websocket en el que recibiremos notificaciones del estado de los procesamientos (podemos seguirlo a través de la ID descrita anteriormente).
- Celery: Cola de procesamiento, recibe tareas desde la API para buscar, descargar y procesar los archivos requeridos, subiendo los datos a Postgres y enviando una notificación del estado del procesamiento a una cola Redis para su distribución.
- Redis: Base de datos key-value que es utilizada como sistema de publicador / subscriptor, en el que Celery publicará los estados de los procesamientos y el websocket se subscribirá para notificar a todos los usuarios conectados a el sobre el estado de procesamiento.
- Postgresql: Base de datos elegida para el desafío, dado que los datos a procesar son geométricos, Postgresql tiene una buena comunidad con Postgis para este tipo de datos.

A continuación se describen en detalle cada uno de ellos:

### API

Este servicio proporciona los siguientes endpoints:

- `[GET] /api/v1/trips/stats`: Obtiene el promedio semanal de la cantidad de viajes para un bounding box y región definidas. Tiene como parámetros obligatorios:
    - `region`: Nombre de la región (Ejemplo: `Paris`)
    - `nortest`: Esquina superior derecha del bounding box, en formato `x,y` (Ejemplo: `1.25,3.43`)
    - `southest`: Esquina inferior izquierda del bounding box, en formato `x,y` (Ejemplo: `2.34,3.45`)

    Ejemplo en python para petición:
    ```py
    import requests
    from urllib.parse import urlencode

    q = {
        "nortest": "3.5,0.5",
        "southest": "3,0",
        "region": "Paris",
    }

    response = requests.get("http://localhost:8000/api/v1/trips/stats?" + urlencode(q))
    response.json()
    >>> { "mean": 3 }
    ```
- `[POST] /api/v1/trips`: Creación de viajes, esto puede ser mediante JSON o la url de un archivo `.csv` con el formato de la muestra proporcionada. Este endpoint espera los siguientes datos:
    - `data_type`: Tipo de dato a enviar, puede ser `json` (insertará los datos proporcionados en el campo `data`), `gcp` (Ordenará a celery la busqueda de un archivo `.csv` en `Cloud Storage` usando la ruta proporcionada en `data`) o `mocked` (Simula ser `gcp` pero en vez de ir a la nube a buscar el archivo, lo busca en disco)
    - `data`: URL o JSON con formato de puntos especificados a continuación.
    
    Ejemplo de petición usando `mocked`
    ```py
    import requests
    
    q = {
        "data_type": "mocked",
        "data": "/app/files/trips.csv"
    }

    response = requests.post("http://localhost:8000/api/v1/trips", json=q)
    response.json()
    >>> { "message": "Task is processing: 877439ae-df3b-47e1-b2ff-ea00f70d9077", "metadata": "PENDING" }

    ```
    Ejemplo de petición usando `json`
    ```py
    import requests
    
    q = {
        "data_type": "json",
        "data": [
            {
                "region": "Paris",
                "origin": [
                    1.0,
                    1.0
                ],
                "destination": [
                    1.5,
                    1.0
                ],
                "timestamp": "2023-01-01 00:00:00",
                "source": "from_api_point"
            }
        ]
    }

    response = requests.post("http://localhost:8000/api/v1/trips", json=q)
    response.json()
    >>> { "message": "Points inserted" }
    ```
- `[WS] /api/v1/trips/live`: Websocket que emite mensajes cuando la cola de procesamiento ha terminado de procesar.
    - Un cliente conectado recibirá mensajes cada vez que un procesado de archivos gatillado por una petición `POST` a la API ha terminado.
    
    Ejemplo para escuchar el websocket usando python
    ```py
    import json
    import asyncio
    import websockets

    async def hello():
        uri = "ws://localhost:8000/api/v1/trips/live"
        async with websockets.connect(uri) as websocket:
            while True:
                message = json.loads(await websocket.recv())
                if message["type"] == "ping":
                    # Para detectar si seguimos conectados
                    await websocket.send(json.dumps({"type": "pong"}))
                    continue
                elif message["type"] == "notification":
                    print(message["data"])

    if __name__ == "__main__":
        asyncio.run(hello())
    ```

    Si hacemos una petición `POST` de tipo `mocked` o `gcp` como en el ejemplo del punto anterior, recibiremos un mensaje con la ID de la tarea de procesamiento (`877439ae-df3b-47e1-b2ff-ea00f70d9077` en el ejemplo anterior), por lo que una vez que esté listo, recibiremos en el websocket el siguiente mensaje:

    ```json
    {
        "task_id": "877439ae-df3b-47e1-b2ff-ea00f70d9077",
        "status": "DONE",
        "message": "Succesfully inserted data to postgis"
    }
    ```

### Celery

Servicio que descarga, lee y procesa un archivo `.csv`.

Para esto:
- Descarga el archivo solicitado: 
    - Si la petición fue de tipo `mocked`, buscará en disco el archivo, usando como ruta lo proporcionado en `data`
    - Si la petición fue de tipo `gcp`, buscará en el bucket de GCP en función de la ruta proporcionada en `data` **(Este no está implementado, se utiliza `mocked` en su lugar para mostrar un propotipo de lo que se puede hacer)**
    - Notese que es facil agregar más tipos de procesamiento, como puede ser Amazon S3 u otros.
- Lee el CSV y lo procesa:
    - Para esto convierte las columnas geométricas (`origin_coord`, `destination_coord`) a floats y parsea la columna `datetime` a, en efecto, un `datetime`
    - Luego queda propuesto una agrupación para almacenar los clusteres en Postgres, en honor al tiempo no se efectuó dicha agrupación y solo se insertan los datos en una tabla similar al formato de la muestra.
- Inserta los datos en Postgres.
- Publica en `Redis` el resultado del procesamiento.

### Redis

Base de datos key-value en memoria, escogida para implementar sistema pub/sub, en el que `Celery` publicará los resultados de los procesamientos, y un `websocket` actuará como subscriptor para notificar a los usuarios sobre el estado del procesamiento.

### Resumen

Lo anterior se puede resumir en el siguiente diagrama:

![image](https://github.com/Keviinplz/optimized-shifts/assets/41240999/e189e3e8-68ef-4fbb-bfd2-24856e617066)

## Ok, quiero probar todo lo anterior...

Para esto debes levantar la aplicación como está descrito en el apartado de `Levantamiento de la app`, se expondrá la `API` en el puerto `8000`, por lo que puedes hacer consultas en `http://localhost:8000/api/v1`

### Para probar la ingesta de datos via archivos

Guarda un archivo `.csv` con el mismo formato que contenía el archivo de muestra en `fileupload`, esto hará que el archivo esté ubicado dentro del contenedor en `/app/files`, por ejemplo, si guardaste un archivo `prueba.csv` (es decir `/fileupload/prueba.csv`) entonces la ruta dentro del contenedor será `/app/files/prueba.csv`

Ahora envía una petición `POST` a `http://localhost:8000/api/v1/trips` con los siguientes datos:
```json
{
    "data_type": "mocked",
    "data": "/app/data/prueba.csv"
}
```

Recibirás una respuesta con la `id` de la tarea de procesamiento (es decir, tu archivo ahora se está procesando y guardando en postgres)

Si estás conectado al websocket como fue descrito anteriormente, recibirás una notificación en cuanto el procesamiento haya finalizado `:)`

### Para probar la ingesta de datos via JSON

Basta enviar una petición `POST` a `http://localhost:8000/api/v1/trips` con los siguientes datos:
```json
{
        "data_type": "json",
        "data": [
            {
                "region": "nombre de la región",
                "origin": [
                    1.0, 
                    1.0
                ],
                "destination": [
                    1.5,
                    1.0
                ],
                "timestamp": "YYYY-mm-dd HH:MM:SS",
                "source": "similar a datasource"
            }
        ]
    }
```

Donde `origin` y `destination` es una tupla de dos floats (x, y). Notese que se está enviando un arreglo, por lo que podemos mandar más de un viaje si se quisiera

Recibiras una respuesta con la confirmación de que los datos fueron almacenados en la base de datos.

### Para probar el promedio semanal

Basta enviar una petición `GET` a `http://localhost:8000/api/v1/trips/stats` con los parámetros definidos anteriormente, recibirás una respuesta con el promedio si es que existe, o `None` en el caso de que no hayan datos.