# 🌤 Nimbus — Weather App

A professional, full-featured weather dashboard built with **FastAPI** and **OpenWeatherMap APIs**. Displays real-time weather, hourly forecasts, a 5-day outlook, air quality index, and detailed atmospheric metrics — all in a dynamic, responsive UI that adapts its color theme to the current weather condition.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Current Weather** | Temperature, feels like, min/max, description |
| **Hourly Forecast** | Next 8 slots (3-hour intervals) with rain probability |
| **5-Day Outlook** | Daily high/low, condition, rain chance |
| **Air Quality Index** | AQI label (Good → Very Poor), PM2.5, PM10 |
| **Detailed Metrics** | Humidity, wind speed & direction, visibility, dew point, pressure, cloud cover, rain (last 1h) |
| **Sunrise & Sunset** | Accurate local times using the city's timezone offset |
| **Local Time Display** | Shows the city's current local date and time |
| **Dynamic Theming** | Background gradient changes based on weather condition |
| **Responsive UI** | Works on desktop, tablet, and mobile |

---

## 🗂 Project Structure

```
nimbus-weather/
├── weather_app.py       # Main FastAPI application (all logic + UI)
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

---

## ⚙️ Requirements

- Python 3.9 or higher
- An [OpenWeatherMap](https://openweathermap.org/api) API key (free tier works)

---

## 📦 Installation

**1. Clone or download the project**

```bash
git clone https://github.com/your-username/nimbus-weather.git
cd nimbus-weather
```

**2. Create and activate a virtual environment** *(recommended)*

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

---

## 🔑 Configuration

Open `weather_app.py` and replace the API key on line 8 with your own:

```python
API_KEY = "your_openweathermap_api_key_here"
```

> ⚠️ **Security note:** For production use, load the key from an environment variable instead of hardcoding it:
> ```python
> import os
> API_KEY = os.environ.get("OWM_API_KEY")
> ```
> Then set it in your shell: `export OWM_API_KEY=your_key_here`

---

## 🚀 Running the App

```bash
uvicorn weather_app:app --reload
```

Then open your browser and go to:

```
http://localhost:8000
```

To search for a city, either type in the search box or pass it as a query parameter:

```
http://localhost:8000/?city=London
http://localhost:8000/?city=Tokyo
http://localhost:8000/?city=Hyderabad
```

---

## 📋 requirements.txt

```
fastapi
uvicorn
requests
```

Install with:

```bash
pip install fastapi uvicorn requests
```

---

## 🌐 APIs Used

All data comes from [OpenWeatherMap](https://openweathermap.org). The app calls three endpoints:

| Endpoint | Purpose |
|---|---|
| `/data/2.5/weather` | Current weather conditions |
| `/data/2.5/forecast` | 5-day / 3-hour forecast data |
| `/data/2.5/air_pollution` | Air quality index and pollutant levels |

The free tier of OpenWeatherMap supports all three endpoints.

---

## 🎨 UI & Design

- **Dynamic background** — gradient shifts based on weather (clear blue for sunny, dark indigo for storms, silver for snow, etc.)
- **Floating weather icon** — subtle animation on the current condition icon
- **Glassmorphism cards** — frosted glass style metric and forecast cards
- **Horizontally scrollable hourly strip** — swipe through the next 24 hours
- **Color-coded AQI dot** — green for Good, red for Very Poor, with a glow effect
- **Reduced motion support** — animations are disabled if the user has `prefers-reduced-motion` set

---

## 🐛 Known Limitations

- City search is by name only. Duplicate city names (e.g. "Springfield") will return the most relevant result from OpenWeatherMap, which may not always be the intended city.
- The free OpenWeatherMap plan has a rate limit of **60 calls/minute**. Each page load makes up to 3 API calls.
- Forecast data is available in 3-hour intervals up to 5 days. The daily forecast picks the midday slot for each day.

---

