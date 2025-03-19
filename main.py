import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, \
    ReplyKeyboardRemove, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ApplicationBuilder
import aiohttp
from datetime import datetime
import json
import os
from keep_alive import keep_alive

keep_alive()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY')

if not TELEGRAM_TOKEN:
    TELEGRAM_TOKEN = '7646541759:AAFKfG_4K8KwaOIaWfG6qybPqcM_KmaG9UE'
if not WEATHER_API_KEY:
    WEATHER_API_KEY = '177a10354e99d3951963b89608edbe16'

WEATHER_API_URL = 'https://api.openweathermap.org/data/2.5/weather'
FORECAST_API_URL = 'https://api.openweathermap.org/data/2.5/forecast'
GEOCODING_API_URL = 'http://api.openweathermap.org/geo/1.0/direct'

MAX_LOCATIONS = 10

user_locations = {}
user_settings = {}

# Language dictionaries
LANGUAGES = {
    'en': {
        'weather': '🌤 Weather',
        'forecast': '📅 Forecast',
        'locations': '📍 Locations',
        'settings': '⚙️ Settings',
        'delete_location': '🗑 Delete location',
        'delete_all': '♨️ Delete all locations',
        'detect_location': '📌 Detect location',
        'back': '🔙 Back',
        'units': '🌡 Units',
        'web_app': '🌍 Web App',
        'celsius': '🌡️ Celsius',
        'fahrenheit': '🌡️ Fahrenheit',
        'back_settings': '🔙 Back to settings',
        'no_locations': 'ℹ️ You have no saved locations.',
        'all_locations_deleted': '🗑 All locations deleted.',
        'select_location_to_delete': '🔍 Select location to delete:',
        'location_deleted': '✅ Location deleted.',
        'choose_option': '🔍 Choose an option:',
        'send_location': '📍 Send location',
        'max_locations_reached': '⚠️ You have reached the maximum number of saved locations (10). Please delete some locations before adding new ones.',
        'location_added': '✅ Location successfully added to the list.',
        'location_exists': 'ℹ️ This location is already in your list.',
        'failed_to_get_weather': '❌ Failed to get weather data for this location.',
        'enter_city_name': '🌆 Enter city or village name:',
        'select_exact_location': '🔍 Select exact location:',
        'city_not_found': '❌ City not found. Please try again.',
        'weather_in': '🌍 Weather in',
        'temperature': '🌡️ Temperature',
        'feels_like': '🌡️ Feels like',
        'pressure': '📊 Pressure',
        'humidity': '💧 Humidity',
        'wind_speed': '💨 Wind speed',
        'precipitation_probability': '🌧️ Precipitation probability',
        'forecast_for': '🌍 5-day weather forecast for',
        'geo_location': '📍 Geolocation',
        'main_menu': "📱 Main menu:",
        'settings_menu': "⚙️ Settings:",
        'current_unit': "🌡 Current unit",
        'choose_unit': "📊 Choose measurement unit:",
        'units_updated_celsius': "✅ Units updated to Celsius",
        'units_updated_fahrenheit': "✅ Units updated to Fahrenheit",
        'locations_menu': "📍 Locations menu",
        'saved_locations': "📍 Saved locations",
        'choose_location_or_add_new': "🔍 Select a location or add new one:",
        'new_location': "➕ New location",
        'sunrise': '🌅 Sunrise',
        'sunset': '🌇 Sunset',
        'wind_speed_units': '💨 Wind speed units',
        'current_wind_unit': '💨 Current wind speed unit',
        'choose_wind_unit': '📊 Choose wind speed unit:',
        'units_updated_kmh': "✅ Wind speed units updated to km/h",
        'units_updated_ms': "✅ Wind speed units updated to m/s",
        'back_wind_settings': '🔙 Back to wind speed settings',
        'kmh': '🚀 km/h',
        'ms': '📏 m/s'
    }
}


def get_text(user_id: int, key: str) -> str:
    # Always use English ('en')
    return LANGUAGES['en'][key]


def get_main_keyboard(user_id: int):
    return ReplyKeyboardMarkup([
        [get_text(user_id, 'weather'), get_text(user_id, 'forecast')],
        [get_text(user_id, 'locations'), get_text(user_id, 'settings')]
    ], resize_keyboard=True)


def get_settings_keyboard(user_id: int):
    return ReplyKeyboardMarkup([
        [get_text(user_id, 'units')],
        [get_text(user_id, 'wind_speed_units')],
        [KeyboardButton(get_text(user_id, 'web_app'), web_app=WebAppInfo('https://meteovision.netlify.app'))],
        [get_text(user_id, 'back')]
    ], resize_keyboard=True)


def get_units_keyboard(user_id: int):
    return ReplyKeyboardMarkup([
        [get_text(user_id, 'celsius'), get_text(user_id, 'fahrenheit')],
        [get_text(user_id, 'back_settings')]
    ], resize_keyboard=True)


def get_wind_units_keyboard(user_id: int):
    return ReplyKeyboardMarkup([
        [get_text(user_id, 'kmh'), get_text(user_id, 'ms')],
        [get_text(user_id, 'back_settings')]
    ], resize_keyboard=True)


def get_locations_keyboard(user_id: int):
    return ReplyKeyboardMarkup([
        [get_text(user_id, 'delete_location'), get_text(user_id, 'delete_all')],
        [get_text(user_id, 'detect_location')],
        [get_text(user_id, 'back')]
    ], resize_keyboard=True)


def format_location_list(locations, user_id: int):
    if not locations:
        return get_text(user_id, 'no_locations')

    result = f"{get_text(user_id, 'saved_locations')}:\n"
    for i, loc in enumerate(locations, 1):
        result += f"{i}. 📌 {loc['display_name']}\n"
    return result


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_settings:
        user_settings[user_id] = {
            'units': 'metric',
            'wind_units': 'ms'  # Default wind speed unit
        }

    welcome_text = "👋 Welcome! I'm a weather bot.\n🔍 Choose an option:"

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(user_id)
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    # Remove emojis from text for comparison
    clean_text = text.replace('🌤 ', '').replace('📅 ', '').replace('📍 ', '') \
        .replace('⚙️ ', '').replace('🗑 ', '').replace('♨️ ', '').replace('📌 ', '') \
        .replace('🔙 ', '').replace('🌡 ', '').replace('🌡️ ', '').replace('🌐 ', '') \
        .replace('🇺🇦 ', '').replace('🇬🇧 ', '').replace('🌍 ', '').replace('💨 ', '') \
        .replace('🚀 ', '').replace('📏 ', '')

    if clean_text in ['Back', 'Back to wind speed settings']:
        context.user_data.clear()
        await update.message.reply_text(get_text(user_id, 'main_menu'), reply_markup=get_main_keyboard(user_id))
        return

    if clean_text == 'Back to settings':
        await update.message.reply_text(get_text(user_id, 'settings_menu'),
                                        reply_markup=get_settings_keyboard(user_id))
        return

    if clean_text == 'Settings':
        await update.message.reply_text(get_text(user_id, 'settings_menu'), reply_markup=get_settings_keyboard(user_id))
        return

    if clean_text == 'Units':
        unit_system = user_settings[user_id]['units']
        current_unit = get_text(user_id, 'celsius').replace('🌡️ ', '') if unit_system == 'metric' else get_text(user_id,
                                                                                                                'fahrenheit').replace(
            '🌡️ ', '')

        units_text = f"{get_text(user_id, 'current_unit')}: {current_unit}\n{get_text(user_id, 'choose_unit')}:"

        await update.message.reply_text(units_text, reply_markup=get_units_keyboard(user_id))
        return

    if clean_text == 'Celsius':
        user_settings[user_id]['units'] = 'metric'
        await update.message.reply_text(get_text(user_id, 'units_updated_celsius'),
                                        reply_markup=get_settings_keyboard(user_id))
        return

    if clean_text == 'Fahrenheit':
        user_settings[user_id]['units'] = 'imperial'
        await update.message.reply_text(get_text(user_id, 'units_updated_fahrenheit'),
                                        reply_markup=get_settings_keyboard(user_id))
        return

    if clean_text == 'Wind speed units':
        wind_unit_system = user_settings[user_id]['wind_units']
        # Remove emojis here for correct display
        current_wind_unit = get_text(user_id, 'kmh').replace('🚀 ', '') if wind_unit_system == 'kmh' else get_text(
            user_id, 'ms').replace('📏 ', '')

        wind_units_text = f"{get_text(user_id, 'current_wind_unit')}: {current_wind_unit}\n{get_text(user_id, 'choose_wind_unit')}:"
        await update.message.reply_text(wind_units_text, reply_markup=get_wind_units_keyboard(user_id))
        return

    # Fix for km/h and m/s options
    if clean_text == 'km/h':
        user_settings[user_id]['wind_units'] = 'kmh'
        await update.message.reply_text(get_text(user_id, 'units_updated_kmh'),
                                        reply_markup=get_settings_keyboard(user_id))
        return

    if clean_text == 'm/s':
        user_settings[user_id]['wind_units'] = 'ms'
        await update.message.reply_text(get_text(user_id, 'units_updated_ms'),
                                        reply_markup=get_settings_keyboard(user_id))
        return

    if clean_text == 'Locations':
        locations = user_locations.get(user_id, [])
        locations_text = format_location_list(locations, user_id)
        await update.message.reply_text(
            f"{get_text(user_id, 'locations_menu')}:\n\n{locations_text}",
            reply_markup=get_locations_keyboard(user_id)
        )
        return

    if clean_text in ['Weather', 'Forecast']:
        if user_id in user_locations and user_locations[user_id]:
            keyboard = []
            for loc in user_locations[user_id]:
                action = 'forecast' if clean_text == 'Forecast' else 'weather'
                display_name = loc['display_name']
                callback_data = f"{action}_{loc['lat']}_{loc['lon']}_{display_name}"  # Use  name
                keyboard.append([InlineKeyboardButton(f"📍 {display_name}", callback_data=callback_data)])

            keyboard.append(
                [InlineKeyboardButton(get_text(user_id, 'new_location'), callback_data=f"new_{clean_text}")])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(get_text(user_id, 'choose_location_or_add_new'), reply_markup=reply_markup)
        else:
            context.user_data['action'] = clean_text
            await update.message.reply_text(get_text(user_id, 'enter_city_name'))
        return

    if clean_text == 'Delete all locations':
        if user_id in user_locations:
            user_locations[user_id] = []
            await update.message.reply_text(
                get_text(user_id, 'all_locations_deleted'),
                reply_markup=get_locations_keyboard(user_id)
            )
        else:
            await update.message.reply_text(get_text(user_id, 'no_locations'))
        return

    if clean_text == 'Delete location':
        if user_id in user_locations and user_locations[user_id]:
            keyboard = []
            for loc in user_locations[user_id]:
                display_name = loc['display_name']
                callback_data = f"delete_{loc['lat']}_{loc['lon']}_{display_name}"  # display name
                keyboard.append([InlineKeyboardButton(f"🗑 {display_name}", callback_data=callback_data)])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(get_text(user_id, 'select_location_to_delete'), reply_markup=reply_markup)
        else:
            await update.message.reply_text(get_text(user_id, 'no_locations'))
        return

    if clean_text == 'Detect location':
        keyboard = [
            [KeyboardButton(
                get_text(user_id, 'send_location'),
                request_location=True
            )],
            [KeyboardButton(get_text(user_id, 'back'))]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(get_text(user_id, 'choose_option'), reply_markup=reply_markup)
        return

    # Обробка введеного міста
    if 'action' in context.user_data:
        action = context.user_data['action']
        input_city = clean_text
        context.user_data['input_city'] = input_city  # Assign it separately
        locations = await get_city_locations(clean_text)  # No language parameter

        if locations:
            keyboard = []
            for loc in locations:
                name = f"{loc['name']}, {loc.get('state', '')}, {loc['country']}"  # Full name (English)
                if action in ['Weather']:
                    callback_data = f"weather_{loc['lat']}_{loc['lon']}_{name}"
                else:  # Forecast
                    callback_data = f"forecast_{loc['lat']}_{loc['lon']}_{name}"
                keyboard.append([InlineKeyboardButton(f"📍 {name}", callback_data=callback_data)])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(get_text(user_id, 'select_exact_location'), reply_markup=reply_markup)
        else:
            await update.message.reply_text(get_text(user_id, 'city_not_found'))


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Initialize user settings if not exists
    if user_id not in user_settings:
        user_settings[user_id] = {
            'units': 'metric',
            'wind_units': 'ms'
        }
    
    data = query.data.split('_')
    action = data[0]

    if action == "new":
        context.user_data['action'] = data[1]
        await query.message.reply_text(get_text(user_id, 'enter_city_name'))
        await query.message.delete()
        return

    if action == "delete":
        lat, lon = float(data[1]), float(data[2])
        user_locations[user_id] = [
            loc for loc in user_locations[user_id]
            if loc['lat'] != lat or loc['lon'] != lon
        ]
        locations_text = format_location_list(user_locations.get(user_id, []), user_id)

        await query.message.edit_text(f"{get_text(user_id, 'location_deleted')}\n\n{locations_text}")
        return

    if action in ['weather', 'forecast']:
        lat, lon = float(data[1]), float(data[2])
        display_name = '_'.join(data[3:])  # Combine the rest of the data to get the full display name

        if user_id not in user_locations or not any(
                abs(loc['lat'] - lat) < 0.0001 and abs(loc['lon'] - lon) < 0.0001 for loc in
                user_locations.get(user_id, [])
        ):
            # Only save location if it doesn't already exist
            if user_id in user_locations and len(user_locations[user_id]) >= MAX_LOCATIONS:
                await query.message.edit_text(get_text(user_id, 'max_locations_reached'))
                return

            # Save location using the provided display_name
            await save_location(user_id, lat, lon, display_name)

        units = user_settings[user_id]['units']
        wind_units = user_settings[user_id]['wind_units']

        if action == 'weather':
            weather_data = await get_weather_by_coords(lat, lon, units, wind_units)
            if weather_data:
                # Use the user's input city/village for weather_data['name']
                weather_data['name'] = context.user_data.get('input_city', display_name) if context.user_data.get(
                    'input_city') else display_name

                await query.message.edit_text(format_weather(weather_data, units, wind_units, user_id))
            else:
                await query.message.edit_text(get_text(user_id, 'failed_to_get_weather'))
        else:  # forecast
            forecast_data = await get_forecast_by_coords(lat, lon, units, wind_units)
            if forecast_data:
                # Use the user's input city/village name
                forecast_data['city']['name'] = context.user_data.get('input_city',
                                                                      display_name) if context.user_data.get(
                    'input_city') else display_name

                await query.message.edit_text(format_forecast(forecast_data, units, wind_units, user_id))
            else:
                await query.message.edit_text(get_text(user_id, 'failed_to_get_weather'))


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    location = update.message.location

    if location:
        if user_id in user_locations and len(user_locations[user_id]) >= MAX_LOCATIONS:
            await update.message.reply_text(
                get_text(user_id, 'max_locations_reached'),
                reply_markup=get_locations_keyboard(user_id)
            )
            return

        units = user_settings[user_id]['units']
        wind_units = user_settings[user_id]['wind_units']
        weather_data = await get_weather_by_coords(location.latitude, location.longitude, units, wind_units)

        if weather_data:
            geo_name = get_text(user_id, "geo_location")
            display_name = f"{geo_name} {weather_data.get('name', '')}"  # Keep original weather_data name
            saved = await save_location(user_id, location.latitude, location.longitude, display_name)

            locations_text = format_location_list(user_locations.get(user_id, []), user_id)
            if saved:
                await update.message.reply_text(
                    f"{get_text(user_id, 'location_added')}\n\n{locations_text}",
                    reply_markup=get_locations_keyboard(user_id)
                )
            else:
                await update.message.reply_text(
                    f"{get_text(user_id, 'location_exists')}\n\n{locations_text}",
                    reply_markup=get_locations_keyboard(user_id)
                )
        else:
            await update.message.reply_text(get_text(user_id, 'failed_to_get_weather'))


async def save_location(user_id: int, lat: float, lon: float, display_name: str):
    if user_id not in user_locations:
        user_locations[user_id] = []

    if len(user_locations[user_id]) >= MAX_LOCATIONS:
        return False

    new_location = {
        'lat': lat,
        'lon': lon,
        'display_name': display_name
    }

    for loc in user_locations[user_id]:
        if abs(loc['lat'] - lat) < 0.0001 and abs(loc['lon'] - lon) < 0.0001:
            return False

    user_locations[user_id].append(new_location)
    return True


async def get_city_locations(city: str) -> list:  # Removed lang parameter
    async with aiohttp.ClientSession() as session:
        params = {
            'q': city,
            'limit': 5,
            'appid': WEATHER_API_KEY
        }
        async with session.get(GEOCODING_API_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data  # Return the raw data (English names)
    return []


async def get_weather_by_coords(lat: float, lon: float, units: str = 'metric', wind_units: str = 'ms') -> dict:
    async with aiohttp.ClientSession() as session:
        params = {
            'lat': lat,
            'lon': lon,
            'appid': WEATHER_API_KEY,
            'units': units,
            'lang': 'en'  # Always use English for weather description
        }
        async with session.get(WEATHER_API_URL, params=params) as response:
            if response.status == 200:
                return await response.json()
    return None


async def get_forecast_by_coords(lat: float, lon: float, units: str = 'metric', wind_units: str = 'ms') -> dict:
    async with aiohttp.ClientSession() as session:
        params = {
            'lat': lat,
            'lon': lon,
            'appid': WEATHER_API_KEY,
            'units': units,
            'lang': 'en'  # Always use English for weather description
        }
        async with session.get(FORECAST_API_URL, params=params) as response:
            if response.status == 200:
                return await response.json()
    return None


def format_weather(weather_data: dict, units: str, wind_units: str, user_id: int) -> str:
    temp = weather_data['main']['temp']
    feels_like = weather_data['main']['feels_like']
    pressure = round(weather_data['main']['pressure'] * 0.750062)
    humidity = weather_data['main']['humidity']
    wind_speed = weather_data['wind']['speed']
    description = weather_data['weather'][0]['description']
    pop = weather_data.get('pop', 0) * 100 if 'pop' in weather_data else 0
    sunrise = datetime.fromtimestamp(weather_data['sys']['sunrise']).strftime('%H:%M')
    sunset = datetime.fromtimestamp(weather_data['sys']['sunset']).strftime('%H:%M')

    temp_unit = "°C" if units == 'metric' else "°F"
    if wind_units == 'kmh':
        wind_speed = wind_speed * 3.6  # Convert m/s to km/h
        wind_unit = "km/h"
    else:
        wind_unit = "m/s"

    return (
        f"{get_text(user_id, 'weather_in')} {weather_data['name']}:\n\n"
        f"{get_text(user_id, 'temperature')}: {temp:.1f}{temp_unit}\n"
        f"{get_text(user_id, 'feels_like')}: {feels_like:.1f}{temp_unit}\n"
        f"{get_text(user_id, 'pressure')}: {pressure} mmHg\n"
        f"{get_text(user_id, 'humidity')}: {humidity}%\n"
        f"{get_text(user_id, 'wind_speed')}: {wind_speed:.1f} {wind_unit}\n"
        f"{get_text(user_id, 'precipitation_probability')}: {pop:.0f}%\n"
        f"☁️ {description.capitalize()}\n"
        f"{get_text(user_id, 'sunrise')}: {sunrise}\n"
        f"{get_text(user_id, 'sunset')}: {sunset}"
    )


def format_forecast(forecast_data: dict, units: str, wind_units: str, user_id: int) -> str:
    city_name = forecast_data['city']['name']
    temp_unit = "°C" if units == 'metric' else "°F"
    if wind_units == 'kmh':
        wind_unit = "km/h"
    else:
        wind_unit = "m/s"

    result = f"{get_text(user_id, 'forecast_for')} {city_name}:\n\n"

    daily_forecasts = {}
    for item in forecast_data['list']:
        date = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
        if date not in daily_forecasts:
            daily_forecasts[date] = item

    for date, data in list(daily_forecasts.items())[:5]:
        day = datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m')
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        pressure = round(data['main']['pressure'] * 0.750062)
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']
        if wind_units == 'kmh':
            wind_speed = wind_speed * 3.6  # Convert m/s to km/h
        description = data['weather'][0]['description']
        pop = data.get('pop', 0) * 100

        result += (
            f"📅 {day}:\n"
            f"{get_text(user_id, 'temperature')}: {temp:.1f}{temp_unit}\n"
            f"{get_text(user_id, 'feels_like')}: {feels_like:.1f}{temp_unit}\n"
            f"{get_text(user_id, 'pressure')}: {pressure} mmHg\n"
            f"{get_text(user_id, 'humidity')}: {humidity}%\n"
            f"{get_text(user_id, 'wind_speed')}: {wind_speed:.1f} {wind_unit}\n"
            f"{get_text(user_id, 'precipitation_probability')}: {pop:.0f}%\n"
            f"☁️ {description.capitalize()}\n\n"
        )

    return result

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the developer."""
    logging.error(f"Exception while handling an update: {context.error}")
    
    # Optional: notify yourself about errors
    if update:
        if isinstance(update, Update) and update.effective_message:
            text = f"An error occurred: {context.error}"
            await update.effective_message.reply_text("Sorry, something went wrong.")

def main():
    # Make sure Telegram knows we're the only instance
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add a more robust way to handle simultaneous instances
    # Set a higher allowed_updates timeout and add a dropout parameter
    application.bot.get_updates(offset=-1, timeout=1)  # Clear any pending updates
    
    # Add your handlers to the instance
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot with appropriate parameters
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
