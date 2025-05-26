# F1 Bot PY 🏎️💨

Un bot automatizado que publica recordatorios de carreras de Fórmula 1, Fórmula 2 y Fórmula 3 en X.com (anteriormente Twitter). Utiliza AWS Lambda y Serverless Framework, ejecutándose diariamente a través de una tarea programada (cron).

---

## 📜 Descripción

Este proyecto tiene como objetivo mantener informados a los aficionados del automovilismo sobre las próximas carreras de F1, F2 y F3. Cada día, a las 10:00 AM UTC (configurable), una función AWS Lambda se activa para:
1.  Consultar un archivo JSON con el calendario de carreras.
2.  Determinar la próxima carrera para cada categoría (F1, F2, F3).
3.  Componer un mensaje amigable en español indicando si la carrera es hoy o cuántos días faltan.
4.  Publicar el mensaje en una cuenta de X.com configurada.

---

## ✨ Características

* **Notificaciones diarias**: Publica tweets sobre las próximas carreras de F1, F2 y F3.
* **Programación flexible**: Utiliza cron jobs de AWS EventBridge (anteriormente CloudWatch Events) para la ejecución programada.
* **Mensajes personalizados**: Formatea los tweets en español, indicando los días restantes o si la carrera es el mismo día.
* **Despliegue sencillo**: Configurado con Serverless Framework para un fácil despliegue en AWS.
* **Manejo de zona horaria**: Convierte las fechas de las carreras a la zona horaria de Paraguay (America/Asuncion) para los cálculos y mensajes.
* **Extensible**: Fácil de modificar para añadir más series de carreras o cambiar la lógica de los mensajes.

---

## 🛠️ Tecnologías Utilizadas

* **Python 3.10**: Lenguaje de programación para la lógica del bot.
* **AWS Lambda**: Servicio de cómputo serverless para ejecutar el código del bot.
* **AWS IAM**: Para gestionar los permisos de la función Lambda.
* **AWS EventBridge (CloudWatch Events)**: Para programar la ejecución de la función Lambda (cron job).
* **AWS CloudWatch Logs**: Para el registro y monitoreo de la función Lambda.
* **Serverless Framework**: Herramienta para desarrollar, desplegar y gestionar aplicaciones serverless en AWS.
* **Tweepy**: Biblioteca de Python para interactuar con la API de X.com (Twitter).
* **Pytz**: Biblioteca para el manejo avanzado de zonas horarias.
* **X.com API (v2)**: Para la publicación de los tweets.

---

## ⚙️ Configuración y Despliegue

### Prerrequisitos

* Cuenta de AWS configurada con credenciales de acceso.
* Node.js y npm instalados (para Serverless Framework).
* Serverless Framework CLI instalado: `npm install -g serverless`.
* Python 3.10 instalado.
* Credenciales de la API de X.com (Consumer Key, Consumer Secret, Access Token, Access Token Secret) con permisos de escritura.
* Git.

### Pasos para la Configuración

1.  **Clonar el repositorio (si aplica):**
    ```bash
    git clone https://github.com/nosisr8/f1botpy.git
    cd f1-race-bot
    ```

2.  **Instalar dependencias del proyecto:**
    El plugin `serverless-python-requirements` se encargará de empaquetar las dependencias de Python durante el despliegue. Asegúrate de tener un archivo `requirements.txt` con el siguiente contenido (o similar):
    ```txt
    tweepy
    pytz
    ```

3.  **Configurar variables de entorno:**
    El proyecto utiliza un archivo `.env` para gestionar las credenciales de la API de X.com. Crea un archivo `.env` en la raíz del proyecto con el siguiente formato:
    ```env
    CONSUMER_KEY="TU_CONSUMER_KEY"
    CONSUMER_SECRET="TU_CONSUMER_SECRET"
    ACCESS_TOKEN="TU_ACCESS_TOKEN"
    ACCESS_TOKEN_SECRET="TU_ACCESS_TOKEN_SECRET"
    ```
    **Importante**: Asegúrate de que este archivo `.env` esté listado en tu `.gitignore` para no subir tus credenciales al repositorio. El archivo `serverless.yml` está configurado con `useDotenv: true` para cargar estas variables durante el despliegue y en el entorno de la Lambda.

4.  **Preparar el calendario de carreras (`f1_schedule.json`):**
    La función Lambda lee el calendario de carreras desde un archivo llamado `f1_schedule.json` ubicado en el mismo directorio que `lambda_function.py`. Debes crear y mantener este archivo.
    La estructura esperada para el JSON es la siguiente:

    ```json
    {
      "F1": [
        {
          "event_name": "Gran Premio de Bahrein",
          "event_date_utc": "2024-03-02T15:00:00Z"
        },
        {
          "event_name": "Gran Premio de Arabia Saudita",
          "event_date_utc": "2024-03-09T17:00:00Z"
        }
        // ... más carreras de F1
      ],
      "F2": [
        {
          "event_name": "F2 Ronda de Bahrein - Carrera Principal",
          "event_date_utc": "2024-03-02T10:15:00Z"
        }
        // ... más carreras de F2
      ],
      "F3": [
        {
          "event_name": "F3 Ronda de Bahrein - Carrera Principal",
          "event_date_utc": "2024-03-02T08:50:00Z"
        }
        // ... más carreras de F3
      ]
    }
    ```
    * `event_name`: Nombre descriptivo del evento.
    * `event_date_utc`: Fecha y hora del evento en formato ISO 8601 UTC (finalizando con `Z`).

    Este archivo debe ser empaquetado junto con tu función Lambda durante el despliegue.

### Despliegue en AWS

Una vez configurados los prerrequisitos y las variables de entorno:

1.  **Autenticar Serverless con AWS:**
    Asegúrate de tener tus credenciales de AWS configuradas localmente (por ejemplo, a través de AWS CLI con `aws configure`).

2.  **Desplegar el servicio:**
    ```bash
    serverless deploy
    ```
    Este comando empaquetará tu código Python, las dependencias, el archivo `f1_schedule.json` y el `serverless.yml` para crear o actualizar la pila de CloudFormation en AWS. Esto incluye la función Lambda, el rol IAM necesario y la regla de EventBridge para la ejecución programada.

---

## 🔩 Funcionamiento

1.  **Disparador Programado (Cron Job)**:
    AWS EventBridge (configurado en `serverless.yml` con `cron(0 10 * * ? *)`) activa la función Lambda `raceReminderBot` todos los días a las 10:00 AM UTC.

2.  **Ejecución de la Lambda (`lambda_function.py`)**:
    * **Carga de configuración**: Se cargan las credenciales de la API de X.com desde las variables de entorno.
    * **Carga del calendario**: Se lee el archivo `f1_schedule.json`.
    * **Iteración por series**: El script itera sobre una lista de series de carreras (`["F1", "F2", "F3"]`).
    * **Búsqueda de la próxima carrera (`get_next_race_info`)**: Para cada serie, busca la próxima carrera basándose en la fecha y hora actual (UTC) y las fechas del calendario. Convierte la fecha del evento a la zona horaria de Paraguay.
    * **Composición del Tweet (`compose_tweet_message`)**: Si se encuentra una próxima carrera, se genera un mensaje.
        * Si la carrera es hoy: "🚨 ¡Hoy es la carrera de {serie} en {nombre_corto_evento}!"
        * Si la carrera es en el futuro: "🏁 Faltan {dias_restantes} días para la siguiente carrera de {serie} en {nombre_corto_evento}\nEvento: {nombre_completo_evento}\n📅 Fecha: {dia_semana} {dia_mes} de {mes_nombre}"
        * El nombre del día y mes se formatean en español.
    * **Publicación del Tweet (`post_tweet`)**: Utilizando la biblioteca `tweepy` y las credenciales cargadas, el mensaje compuesto se publica en X.com.
    * **Registro (Logging)**: Se registran varios eventos y errores en AWS CloudWatch Logs para monitoreo y depuración.

---

## 📝 `serverless.yml`

El archivo `serverless.yml` define la infraestructura como código para este servicio:

* **`service`**: `f1-race-bot` - Nombre del servicio.
* **`useDotenv: true`**: Permite cargar variables desde un archivo `.env`.
* **`provider`**: Define la configuración de AWS:
    * `runtime`: `python3.10`.
    * `region`: `sa-east-1`.
    * `timeout` y `memorySize`: Configuración de recursos para la Lambda.
    * `environment`: Mapea las variables de entorno necesarias para la Lambda desde el archivo `.env`.
    * `iam.role.statements`: Define los permisos necesarios para que la Lambda escriba logs en CloudWatch.
* **`functions.raceReminderBot`**: Define la función Lambda:
    * `handler`: `lambda_function.lambda_handler` (el archivo `lambda_function.py` y la función `lambda_handler` dentro de él).
    * `description`: Descripción de la función.
    * `events.schedule`: Configura el cron job para ejecutar la Lambda diariamente a las `0 10 * * ? *` (10:00 AM UTC).
* **`plugins`**: Lista `serverless-python-requirements` para gestionar las dependencias de Python.
* **`custom.pythonRequirements`**: Configuración adicional para el plugin, como `dockerizePip: true` para compilar dependencias en un entorno similar a Lambda.

---

## 🧪 Pruebas Locales

El script `lambda_function.py` incluye un bloque `if __name__ == "__main__":` que permite ejecutar la lógica principal localmente para pruebas.
Para ello:
1.  Asegúrate de tener las variables de entorno de X.com (`CONSUMER_KEY`, `CONSUMER_SECRET`, `ACCESS_TOKEN`, `ACCESS_TOKEN_SECRET`) exportadas en tu terminal.
2.  Crea el archivo `f1_schedule.json` en el mismo directorio.
3.  Ejecuta el script:
    ```bash
    python lambda_function.py
    ```
    **Nota**: La línea `post_tweet(tweet_message)` en `lambda_handler` podría estar comentada en el script original para evitar publicaciones accidentales durante pruebas. Descoméntala si deseas probar la funcionalidad de publicación real (asegúrate de que las credenciales sean válidas y, preferiblemente, de una cuenta de prueba).

---

## 🚀 Posibles Mejoras Futuras

* Obtener el calendario de carreras dinámicamente desde una API pública en lugar de un archivo JSON manual.
* Añadir más opciones de personalización para los mensajes.
* Integrar un acortador de URLs si los nombres de los eventos son muy largos.
* Mejorar el manejo de errores y reintentos para la publicación de tweets.
* Añadir pruebas unitarias.

---