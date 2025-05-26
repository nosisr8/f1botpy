import datetime
import os
import json
import logging
import tweepy
import pytz

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

def compose_tweet_message(race_info):
    """
    Composes the tweet message based on race information.
    """
    if not race_info:
        return None

    event_name = race_info["name"]
    race_date = race_info["date"]
    series = race_info["series"]

    # Calculate days remaining until the race, based on Paraguay time
    now_paraguay = datetime.datetime.now(PARAGUAY_TZ)
    time_until_race = race_date - now_paraguay
    days_remaining = time_until_race.days

    # Only compose message if the race is in the future or today
    if days_remaining >= 0:
        # Format the date and day name in Spanish
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

        # Extract a short event name (e.g., "Monaco") from the full name
        short_event_name = event_name.replace("Gran Premio de ", "").replace("F2 ", "").replace("F3 ", "").strip()
        short_event_name = short_event_name.split(' ')[0].capitalize() if short_event_name else "Evento"
        if days_remaining == 0:
            message = f"🚨 ¡Hoy es la carrera de {series} en {short_event_name}!\n"
        else:
            message = (
                f"🏁 Faltan {days_remaining} días para la siguiente carrera de {series} en {short_event_name}\n"
                f"Evento: {event_name}\n" # Use raw event_name as per example
                f"📅 Fecha: {formatted_day_name} {race_date.day} de {formatted_month_name}"
        )
        return message
    else:
        logger.info(f"Race {event_name} has already passed or is too close to compose 'days remaining' message.")
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