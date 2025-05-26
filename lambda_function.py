import datetime
import os
import json
import logging
import tweepy
import pytz
import google.generativeai as genai
import random

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add a StreamHandler for local execution if not already configured
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# --- X.com API Credentials from Environment Variables ---
CONSUMER_KEY = os.environ.get("CONSUMER_KEY")
CONSUMER_SECRET = os.environ.get("CONSUMER_SECRET")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET")
# --- Google Gemini API Key from Environment Variables ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- Timezone for Paraguay ---
# Using pytz for robust timezone handling, as datetime.timezone can be limited
try:
    PARAGUAY_TZ = pytz.timezone('America/Asuncion') # Use a specific timezone name
    UTC_TZ = pytz.utc
except Exception as e:
    logger.warning(f"pytz not available or timezone error: {e}. Falling back to fixed offset.")
    PARAGUAY_TZ = datetime.timezone(datetime.timedelta(hours=-3))
    UTC_TZ = datetime.timezone.utc


# --- Race Schedule Data ---
RACE_SCHEDULE_FILE = 'f1_schedule.json'
RACE_SCHEDULE_DATA = {}
try:
    with open(RACE_SCHEDULE_FILE, 'r') as f:
        RACE_SCHEDULE_DATA = json.load(f)
    logger.info(f"Successfully loaded race schedule from {RACE_SCHEDULE_FILE}")
except FileNotFoundError:
    logger.error(f"Race schedule file '{RACE_SCHEDULE_FILE}' not found. Please create it.")
except json.JSONDecodeError as e:
    logger.error(f"Error decoding JSON from '{RACE_SCHEDULE_FILE}': {e}")
except Exception as e:
    logger.error(f"An unexpected error occurred loading schedule: {e}")

def get_next_race_info(series="F1"):
    """
    Finds the next upcoming race for a given series from the loaded JSON data.
    """
    if series not in RACE_SCHEDULE_DATA:
        logger.warning(f"No schedule data found for series: {series}")
        return None

    now_utc = datetime.datetime.now(UTC_TZ)
    upcoming_races = []

    for race in RACE_SCHEDULE_DATA[series]:
        try:
            event_datetime_utc = datetime.datetime.fromisoformat(race['event_date_utc'].replace('Z', '+00:00'))
            event_datetime_utc = event_datetime_utc.astimezone(UTC_TZ)

            if event_datetime_utc > now_utc:
                upcoming_races.append({
                    "name": race['event_name'],
                    "date": event_datetime_utc.astimezone(PARAGUAY_TZ),
                    "series": series
                })
        except ValueError as e:
            logger.error(f"Error parsing date for race '{race.get('event_name', 'Unknown')}': {e}. Date string: {race.get('event_date_utc')}")
            continue

    if upcoming_races:
        # Sort by date to get the very next one
        upcoming_races.sort(key=lambda x: x['date'])
        return upcoming_races[0]
    else:
        logger.info(f"No upcoming {series} event found in the schedule data.")
        return None

def generar_tweet_f1(tipo_tweet, piloto="", equipo="", carrera="", evento_especifico="", estilo="emocionante", longitud="corta", series="F1"):
    """
    Genera un tweet de Fórmula 1 utilizando el modelo Gemini.

    Args:
        tipo_tweet (str): Define el tipo de tweet a generar (ej. "previo_carrera", "resultado_carrera", etc.).
        piloto (str): Nombre del piloto involucrado (opcional).
        equipo (str): Nombre del equipo involucrado (opcional).
        carrera (str): Nombre de la carrera o Gran Premio (opcional).
        evento_especifico (str): Detalles adicionales del evento (ej. "pit stop", "adelantamiento", "accidente").
        estilo (str): El estilo del tweet (ej. "emocionante", "analítico", "humorístico", "inspirador", "fanático").
        longitud (str): La longitud deseada del tweet ("corta", "media", "larga").

    Returns:
        str: El tweet de F1 generado.
    """
    # Asegúrate de que la clave API esté configurada antes de usar el modelo
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY no está configurada. No se puede generar tweet con Gemini.")
        return "¡La F1 está en marcha! Próximamente más detalles."

    genai.configure(api_key=GEMINI_API_KEY)

    model = genai.GenerativeModel('gemini-1.5-flash') # O 'gemini-1.5-flash' para un modelo más rápido y rentable

    prompt = f"Genera un tweet sobre {series}. "
    prompt += f"El estilo debe ser {estilo}. "
    prompt += f"La longitud debe ser {longitud} y no debe exceder los 240 caracteres. "
    prompt += "Incluye emojis y hashtags relevantes para F1, el piloto, el equipo y la carrera. "
    prompt += "Escribe en español de Paraguay si es posible, o español latino."

    hashtags_base = ["#" + series]
    if piloto:
        hashtags_base.append(f"#{piloto.replace(' ', '')}")
    if equipo:
        hashtags_base.append(f"#{equipo.replace(' ', '')}")
    if carrera:
        # Intenta extraer un hashtag más limpio del nombre de la carrera
        short_carrera_tag = carrera.replace("Gran Premio de ", "").replace("GP", "").replace(" de ", "").replace(" ", "")
        if short_carrera_tag:
            hashtags_base.append(f"#{short_carrera_tag}")
        else:
            hashtags_base.append(f"#{carrera.replace(' ', '')}")

    # Lógica para construir el prompt basado en el tipo de tweet
    if tipo_tweet == "previo_carrera":
        prompt += f"Tema: La expectativa y emoción antes del {carrera} en el ."
        if piloto:
            prompt += f" Enfocado en la actuación de {piloto}."
        if equipo:
            prompt += f" Con un énfasis en el rendimiento de {equipo}."
        if evento_especifico:
            prompt += f" Específicamente sobre {evento_especifico}."
        hashtags_base.extend(["#F1esta", "#RaceWeekend", "#CuentaAtrás"])

    elif tipo_tweet == "resultado_carrera":
        prompt += f"Tema: El resultado y los momentos clave del {carrera}."
        if piloto:
            prompt += f" Destacando la victoria o el podio de {piloto}."
        if equipo:
            prompt += f" Celebrando el éxito de {equipo}."
        hashtags_base.extend(["#Winner", "#Podium", "#RaceResults", "#F1resultados"])

    elif tipo_tweet == "noticia_piloto":
        prompt += f"Tema: Noticias o rumores sobre el piloto {piloto}."
        if evento_especifico:
            prompt += f" Específicamente sobre {evento_especifico}."
        hashtags_base.extend(["#F1News", "#DriverUpdate", "#ÚltimaHoraF1"])

    elif tipo_tweet == "noticia_equipo":
        prompt += f"Tema: Noticias o desarrollos sobre el equipo {equipo}."
        if evento_especifico:
            prompt += f" Específicamente sobre {evento_especifico}."
        hashtags_base.extend(["#F1Team", "#TeamNews", "#DesarrolloF1"])

    elif tipo_tweet == "momento_clasificacion":
        prompt += f"Tema: Un momento emocionante de la clasificación del {carrera}."
        if piloto:
            prompt += f" Con {piloto} siendo el protagonista."
        if evento_especifico:
            prompt += f" Específicamente sobre {evento_especifico}."
        hashtags_base.extend(["#Qualifying", "#PolePosition", "#Q3", "#F1Clasificación"])

    elif tipo_tweet == "analisis_general":
        prompt += f"Tema: Análisis general o comentario sobre un aspecto de la F1."
        if evento_especifico:
            prompt += f" Enfocado en {evento_especifico}."
        hashtags_base.extend(["#F1Insights", "#AnálisisF1", "#EstrategiaF1"])

    elif tipo_tweet == "humor_f1":
        prompt += f"Tema: Un tweet humorístico sobre un cliché o situación común en la F1. "
        if evento_especifico:
            prompt += f" Relacionado con: {evento_especifico}."
        hashtags_base.extend(["#F1Humor", "#F1Memes", "#F1Risas"])
        prompt += " Usa un tono ligero y divertido."

    # Añadir hashtags aleatorios para mayor variedad, limitando a 5-7 para no saturar
    random.shuffle(hashtags_base)
    # Seleccionamos un número de hashtags entre 3 y 7, o el total si es menor
    num_hashtags = random.randint(3, min(5, len(hashtags_base)))
    prompt += " " + " ".join(random.sample(hashtags_base, num_hashtags))

    try:
        response = model.generate_content(prompt)
        tweet_generado = response.text
        return tweet_generado[:240] # Asegurarse de no exceder los 280 caracteres
    except Exception as e:
        logger.error(f"Error al generar el tweet de F1 con Gemini: {e}")
        return f"¡Error en la IA! Pero la F1 sigue siendo increíble. #F1"

def compose_tweet_message(race_info):
    """
    Composes the tweet message using Gemini based on race information.
    """
    if not race_info:
        logger.warning("No race info provided to compose tweet.")
        return None

    event_name = race_info["name"]
    race_date = race_info["date"]
    series = race_info["series"]

    # Calculate days remaining until the race, based on Paraguay time
    now_paraguay = datetime.datetime.now(PARAGUAY_TZ)
    time_until_race = race_date - now_paraguay
    days_remaining = time_until_race.days

    # Define the core logic for when to tweet
    if days_remaining == 0:
        # Hoy es la carrera
        logger.info(f"Generating 'today is race' tweet for {event_name}...")
        message = generar_tweet_f1(
            tipo_tweet="previo_carrera",
            carrera=event_name,
            estilo="emocionante",
            longitud="corta",
            evento_especifico="¡hoy es el día de la carrera!",
            series=series
        )
        # Asegurarse de que el tweet generado por Gemini empiece con "🚨 ¡Hoy es la carrera..."
        if not message.lower().startswith("🚨 ¡hoy es la carrera"):
            message = "🚨 ¡Hoy es la carrera! " + message # Forzamos el inicio si Gemini no lo hace
        return message

    elif 0 < days_remaining <= 7:
        # La carrera es en menos de una semana
        logger.info(f"Generating 'countdown' tweet for {event_name} (days remaining: {days_remaining})...")
        message = generar_tweet_f1(
            tipo_tweet="previo_carrera",
            carrera=event_name,
            estilo="emocionante",
            longitud="corta",
            evento_especifico=f"faltan {days_remaining} días",
            series=series
        )
        # Añade la fecha y el día si Gemini no lo incluyó explícitamente y si es relevante
        if f"faltan {days_remaining} días" not in message and "día de la carrera" not in message:
            # Formatear la fecha y el día de la semana en español
            day_names_map = {
                'Monday': 'lunes', 'Tuesday': 'martes', 'Wednesday': 'miércoles',
                'Thursday': 'jueves', 'Friday': 'viernes', 'Saturday': 'sábado', 'Sunday': 'domingo'
            }
            month_names_map = {
                'January': 'enero', 'February': 'febrero', 'March': 'marzo',
                'April': 'abril', 'May': 'mayo', 'June': 'junio',
                'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
                'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
            }
            formatted_day_name = day_names_map.get(race_date.strftime('%A'), race_date.strftime('%A'))
            formatted_month_name = month_names_map.get(race_date.strftime('%B'), race_date.strftime('%B'))
            message += f"\n📅 Fecha: {formatted_day_name} {race_date.day} de {formatted_month_name}."
        return message
    else:
        logger.info(f"Race {event_name} is too far (days remaining: {days_remaining}) or has passed. No tweet will be composed.")
        return None

def post_tweet(message):
    """
    Posts a tweet to X.com using API keys from environment variables.
    """
    if not all([CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
        logger.error("One or more X.com API keys are missing from environment variables. Cannot post tweet.")
        return
    try:
        # Initialize the API v2 Client with OAuth 1.0a user context
        client = tweepy.Client(
            consumer_key=CONSUMER_KEY,
            consumer_secret=CONSUMER_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )

        response = client.create_tweet(text=message)
        logger.info(f"Tweet posted successfully! ID: {response.data['id']}, Text: {response.data['text']}")
    except tweepy.TweepyException as e:
        logger.error(f"Error posting tweet to X.com: {e}")
        # Log the specific error from X.com if available in e.response.text
        if e.response is not None:
            logger.error(f"X.com API Response: {e.response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while posting tweet: {e}")

# --- AWS Lambda Handler ---
def lambda_handler(event, context):
    logger.info("Lambda function triggered.")
    logger.info(f"Current time in Paraguay: {datetime.datetime.now(PARAGUAY_TZ).strftime('%Y-%m-%d %H:%M:%S %Z%z')}")

    series_to_check = ["F1", "F2", "F3"]

    for series in series_to_check:
        logger.info(f"Checking for {series} next race...")
        race_info = get_next_race_info(series)
        if race_info:
            tweet_message = compose_tweet_message(race_info)
            if tweet_message:
                logger.info(f"\n--- {series} Race Update ---")
                logger.info(tweet_message)
                # Uncomment the line below to actually post the tweet
                post_tweet(tweet_message)
            else:
                logger.info(f"No suitable tweet message composed for {series} (race might be too close/passed).")
        else:
            logger.warning(f"Could not retrieve valid race information for {series} from JSON data.")

    logger.info("F1/F2/F3 Race Bot execution complete.")

    return {
        'statusCode': 200,
        'body': json.dumps('F1/F2/F3 Race Bot execution complete!')
    }

# --- Local Testing Entry Point ---
if __name__ == "__main__":
    print("Running lambda_handler locally for testing...")
    # For local testing, ensure X.com environment variables are set in your shell:
    # export CONSUMER_KEY="your_dev_consumer_key"
    # export CONSUMER_SECRET="your_dev_consumer_secret"
    # export ACCESS_TOKEN="your_dev_access_token"
    # export ACCESS_TOKEN_SECRET="your_dev_access_token_secret"

    lambda_handler(None, None)
    print("Local execution finished.")