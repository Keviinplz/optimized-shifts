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
        "data_type": "json"
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

