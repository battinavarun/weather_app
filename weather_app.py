import requests
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

API_KEY = "api_key_here"


def get_complete_weather(city_name):
    current_url = "http://api.openweathermap.org/data/2.5/weather"
    forecast_url = "http://api.openweathermap.org/data/2.5/forecast"
    air_url = "http://api.openweathermap.org/data/2.5/air_pollution"

    params = {"q": city_name, "appid": API_KEY, "units": "metric"}

    current_response = requests.get(current_url, params=params)
    forecast_response = requests.get(forecast_url, params=params)

    if current_response.status_code != 200 or forecast_response.status_code != 200:
        return None

    current_data = current_response.json()
    lat = current_data["coord"]["lat"]
    lon = current_data["coord"]["lon"]

    air_params = {"lat": lat, "lon": lon, "appid": API_KEY}
    air_response = requests.get(air_url, params=air_params)
    air_data = air_response.json() if air_response.status_code == 200 else None

    return {
        "current": current_data,
        "forecast": forecast_response.json(),
        "air": air_data,
    }


def format_unix_time(unix_timestamp, timezone_offset):
    utc_time = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    local_time = utc_time + timedelta(seconds=timezone_offset)
    return local_time.strftime("%I:%M %p")


def get_wind_direction(deg):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(deg / 45) % 8]


def get_aqi_label(aqi):
    labels = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}
    colors = {1: "#22c55e", 2: "#84cc16", 3: "#eab308", 4: "#f97316", 5: "#ef4444"}
    return labels.get(aqi, "—"), colors.get(aqi, "#94a3b8")


def get_weather_gradient(condition_id):
    if condition_id < 300:
        return "#1e1b4b, #312e81"  # thunderstorm — deep indigo
    elif condition_id < 500:
        return "#0c4a6e, #164e63"  # drizzle — steel teal
    elif condition_id < 600:
        return "#0f2942, #1e3a5f"  # rain — deep navy
    elif condition_id < 700:
        return "#e2e8f0, #94a3b8"  # snow — silver
    elif condition_id < 800:
        return "#374151, #4b5563"  # atmosphere — grey
    elif condition_id == 800:
        return "#0369a1, #075985"  # clear — vivid blue
    else:
        return "#1e3a5f, #0f2942"  # clouds — muted blue


def get_daily_forecasts(forecast_list, timezone_offset):
    """Group forecast by calendar day in local time, pick midday slot per day."""
    days = {}
    for item in forecast_list:
        utc_dt = datetime.fromtimestamp(item["dt"], tz=timezone.utc)
        local_dt = utc_dt + timedelta(seconds=timezone_offset)
        day_key = local_dt.strftime("%Y-%m-%d")
        hour = local_dt.hour
        if day_key not in days:
            days[day_key] = []
        days[day_key].append((abs(hour - 12), item, local_dt))

    result = []
    today_key = (
        datetime.fromtimestamp(
            forecast_list[0]["dt"], tz=timezone.utc
        ) + timedelta(seconds=timezone_offset)
    ).strftime("%Y-%m-%d")

    for day_key in sorted(days.keys()):
        if day_key == today_key:
            continue
        best = sorted(days[day_key], key=lambda x: x[0])[0]
        result.append((best[2], best[1]))
        if len(result) == 5:
            break
    return result


def get_hourly_forecast(forecast_list, timezone_offset, count=8):
    """Return next `count` 3-hour slots in local time."""
    result = []
    for item in forecast_list[:count]:
        utc_dt = datetime.fromtimestamp(item["dt"], tz=timezone.utc)
        local_dt = utc_dt + timedelta(seconds=timezone_offset)
        result.append((local_dt, item))
    return result


@app.get("/", response_class=HTMLResponse)
def home(city: str = None):
    if not city:
        weather_html = """
        <div class="empty-state">
            <div class="empty-icon">
                <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="32" cy="24" r="10" stroke="currentColor" stroke-width="2.5"/>
                    <path d="M16 44c0-8.837 7.163-16 16-16s16 7.163 16 16" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
                    <path d="M8 52h48" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.4"/>
                </svg>
            </div>
            <h3>Search any city worldwide</h3>
            <p>Get real-time weather, hourly trends, a 5-day outlook, and air quality — all in one place.</p>
        </div>
        """
        gradient = "#0f172a, #1e293b"
        page_class = "page-default"
    else:
        all_data = get_complete_weather(city)

        if all_data is None:
            weather_html = f"""
            <div class="error-state">
                <div class="error-icon">⚠</div>
                <h3>City not found</h3>
                <p>We couldn't find "<strong>{city}</strong>". Check the spelling and try again.</p>
            </div>
            """
            gradient = "#0f172a, #1e293b"
            page_class = "page-default"
        else:
            current = all_data["current"]
            forecast_list = all_data["forecast"]["list"]
            air_data = all_data["air"]
            tz_offset = current["timezone"]

            condition_id = current["weather"][0]["id"]
            gradient = get_weather_gradient(condition_id)
            page_class = "page-weather"

            city_name = current["name"]
            country = current["sys"]["country"]
            temp = round(current["main"]["temp"])
            feels_like = round(current["main"]["feels_like"])
            temp_min = round(current["main"]["temp_min"])
            temp_max = round(current["main"]["temp_max"])
            humidity = current["main"]["humidity"]
            pressure = current["main"]["pressure"]
            wind_speed = round(current["wind"]["speed"] * 3.6, 1)
            wind_deg = current["wind"].get("deg", 0)
            wind_dir = get_wind_direction(wind_deg)
            visibility = round(current.get("visibility", 0) / 1000, 1)
            description = current["weather"][0]["description"].title()
            icon_code = current["weather"][0]["icon"]
            icon_url = f"https://openweathermap.org/img/wn/{icon_code}@4x.png"
            clouds = current.get("clouds", {}).get("all", 0)
            rain_1h = current.get("rain", {}).get("1h", 0)
            dew_point = round(
                current["main"]["temp"]
                - ((100 - current["main"]["humidity"]) / 5)
            )

            lat = current["coord"]["lat"]
            lon = current["coord"]["lon"]
            sunrise = format_unix_time(current["sys"]["sunrise"], tz_offset)
            sunset = format_unix_time(current["sys"]["sunset"], tz_offset)

            local_now = datetime.fromtimestamp(
                current["dt"], tz=timezone.utc
            ) + timedelta(seconds=tz_offset)
            local_time_str = local_now.strftime("%A, %d %b %Y · %I:%M %p")

            # AQI
            aqi_html = ""
            if air_data and air_data.get("list"):
                aqi_val = air_data["list"][0]["main"]["aqi"]
                aqi_label, aqi_color = get_aqi_label(aqi_val)
                pm25 = air_data["list"][0]["components"].get("pm2_5", 0)
                pm10 = air_data["list"][0]["components"].get("pm10", 0)
                aqi_html = f"""
                <div class="aqi-badge" style="--aqi-color:{aqi_color}">
                    <span class="aqi-dot"></span>
                    <span>Air Quality: <strong>{aqi_label}</strong></span>
                    <span class="aqi-detail">PM2.5 · {pm25:.1f} µg/m³</span>
                </div>
                """

            # Hourly forecast
            hourly = get_hourly_forecast(forecast_list, tz_offset)
            hourly_html = ""
            for local_dt, item in hourly:
                h_time = local_dt.strftime("%I %p").lstrip("0")
                h_temp = round(item["main"]["temp"])
                h_icon = f"https://openweathermap.org/img/wn/{item['weather'][0]['icon']}.png"
                h_pop = round(item.get("pop", 0) * 100)
                hourly_html += f"""
                <div class="hour-card">
                    <span class="h-time">{h_time}</span>
                    <img src="{h_icon}" alt="" class="h-icon">
                    <span class="h-temp">{h_temp}°</span>
                    <span class="h-pop">{'💧 ' + str(h_pop) + '%' if h_pop > 20 else ''}</span>
                </div>
                """

            # 5-day forecast
            daily = get_daily_forecasts(forecast_list, tz_offset)
            daily_html = ""
            for local_dt, f_data in daily:
                f_day = local_dt.strftime("%a")
                f_date = local_dt.strftime("%d %b")
                f_temp_max = round(f_data["main"]["temp_max"])
                f_temp_min = round(f_data["main"]["temp_min"])
                f_desc = f_data["weather"][0]["description"].title()
                f_icon = f"https://openweathermap.org/img/wn/{f_data['weather'][0]['icon']}@2x.png"
                f_pop = round(f_data.get("pop", 0) * 100)
                daily_html += f"""
                <div class="day-row">
                    <div class="day-info">
                        <span class="day-name">{f_day}</span>
                        <span class="day-date">{f_date}</span>
                    </div>
                    <div class="day-mid">
                        <img src="{f_icon}" alt="{f_desc}" class="day-icon">
                        <span class="day-desc">{f_desc}</span>
                    </div>
                    <div class="day-right">
                        {f'<span class="day-pop">💧{f_pop}%</span>' if f_pop > 20 else '<span></span>'}
                        <span class="day-temps"><b>{f_temp_max}°</b> / <span class="lo">{f_temp_min}°</span></span>
                    </div>
                </div>
                """

            weather_html = f"""
            <div class="hero-section">
                <div class="hero-left">
                    <div class="city-name">{city_name}</div>
                    <div class="country-row">
                        <span class="country">{country}</span>
                        <span class="local-time">{local_time_str}</span>
                    </div>
                    <div class="temp-hero">
                        <span class="temp-main">{temp}°</span>
                        <span class="temp-unit">C</span>
                    </div>
                    <div class="feels-row">
                        Feels like {feels_like}° &nbsp;·&nbsp; {temp_min}° / {temp_max}°
                    </div>
                    <div class="condition-tag">{description}</div>
                    {aqi_html}
                </div>
                <div class="hero-right">
                    <img src="{icon_url}" alt="{description}" class="main-icon">
                </div>
            </div>

            <div class="hourly-scroll-wrap">
                <div class="section-label">HOURLY FORECAST</div>
                <div class="hourly-scroll">
                    {hourly_html}
                </div>
            </div>

            <div class="metrics-section">
                <div class="section-label">CONDITIONS</div>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-icon">💧</div>
                        <div class="metric-body">
                            <span class="metric-label">Humidity</span>
                            <span class="metric-value">{humidity}%</span>
                        </div>
                        <div class="metric-bar"><div class="metric-fill" style="width:{humidity}%"></div></div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">💨</div>
                        <div class="metric-body">
                            <span class="metric-label">Wind</span>
                            <span class="metric-value">{wind_speed} km/h {wind_dir}</span>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">👁</div>
                        <div class="metric-body">
                            <span class="metric-label">Visibility</span>
                            <span class="metric-value">{visibility} km</span>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">🌡</div>
                        <div class="metric-body">
                            <span class="metric-label">Dew Point</span>
                            <span class="metric-value">{dew_point}°C</span>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">⬇</div>
                        <div class="metric-body">
                            <span class="metric-label">Pressure</span>
                            <span class="metric-value">{pressure} hPa</span>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">☁</div>
                        <div class="metric-body">
                            <span class="metric-label">Cloud Cover</span>
                            <span class="metric-value">{clouds}%</span>
                        </div>
                        <div class="metric-bar"><div class="metric-fill" style="width:{clouds}%"></div></div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">🌅</div>
                        <div class="metric-body">
                            <span class="metric-label">Sunrise</span>
                            <span class="metric-value">{sunrise}</span>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">🌇</div>
                        <div class="metric-body">
                            <span class="metric-label">Sunset</span>
                            <span class="metric-value">{sunset}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="forecast-section">
                <div class="section-label">5-DAY OUTLOOK</div>
                <div class="daily-list">
                    {daily_html}
                </div>
            </div>

            <div class="geo-footer">
                <span>📍 {lat:.4f}°N, {lon:.4f}°E</span>
                <span>Rain (1h): {rain_1h} mm</span>
            </div>
            """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nimbus — Weather</title>
    <style>
        *, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}

        :root {{
            --bg-grad: linear-gradient(160deg, {gradient.split(',')[0].strip()}, {gradient.split(',')[1].strip()});
            --glass: rgba(255,255,255,0.06);
            --glass-border: rgba(255,255,255,0.1);
            --glass-hover: rgba(255,255,255,0.09);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent: #38bdf8;
            --accent-glow: rgba(56,189,248,0.18);
            --radius-card: 20px;
            --radius-sm: 12px;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: var(--bg-grad);
            min-height: 100vh;
            color: var(--text-primary);
            padding: 20px;
            transition: background 0.8s ease;
        }}

        /* ── Page Layout ── */
        .page {{
            max-width: 640px;
            margin: 0 auto;
        }}

        /* ── Header / Search ── */
        header {{
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 24px;
        }}

        .brand {{
            font-size: 1.4rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: var(--text-primary);
            white-space: nowrap;
            flex-shrink: 0;
        }}

        .brand span {{ color: var(--accent); }}

        .search-form {{
            flex: 1;
            display: flex;
            gap: 10px;
        }}

        .search-input {{
            flex: 1;
            padding: 13px 18px;
            background: rgba(255,255,255,0.07);
            border: 1px solid var(--glass-border);
            border-radius: 14px;
            font-size: 0.95rem;
            color: var(--text-primary);
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
            backdrop-filter: blur(12px);
        }}

        .search-input::placeholder {{ color: var(--text-muted); }}
        .search-input:focus {{
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-glow);
        }}

        .search-btn {{
            padding: 13px 22px;
            background: var(--accent);
            color: #0f172a;
            border: none;
            border-radius: 14px;
            font-size: 0.95rem;
            font-weight: 700;
            cursor: pointer;
            transition: background 0.2s, transform 0.15s;
            white-space: nowrap;
        }}

        .search-btn:hover {{ background: #7dd3fc; transform: translateY(-1px); }}
        .search-btn:active {{ transform: translateY(0); }}

        /* ── Empty / Error States ── */
        .empty-state, .error-state {{
            text-align: center;
            padding: 60px 20px;
        }}

        .empty-icon {{
            width: 72px;
            height: 72px;
            margin: 0 auto 20px;
            color: var(--text-muted);
        }}

        .empty-icon svg {{ width: 100%; height: 100%; }}

        .empty-state h3, .error-state h3 {{
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 10px;
            color: var(--text-primary);
        }}

        .empty-state p, .error-state p {{
            color: var(--text-secondary);
            line-height: 1.6;
            font-size: 0.95rem;
        }}

        .error-icon {{
            font-size: 3rem;
            margin-bottom: 16px;
        }}

        /* ── Hero ── */
        .hero-section {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 24px;
            padding: 28px;
            background: var(--glass);
            border: 1px solid var(--glass-border);
            border-radius: 28px;
            backdrop-filter: blur(24px);
        }}

        .hero-left {{ flex: 1; }}

        .city-name {{
            font-size: 2.2rem;
            font-weight: 700;
            letter-spacing: -1px;
            line-height: 1.1;
            margin-bottom: 6px;
        }}

        .country-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
            margin-bottom: 16px;
        }}

        .country {{
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: var(--accent);
            background: var(--accent-glow);
            padding: 3px 10px;
            border-radius: 100px;
        }}

        .local-time {{
            font-size: 0.78rem;
            color: var(--text-muted);
        }}

        .temp-hero {{
            display: flex;
            align-items: flex-start;
            gap: 2px;
            line-height: 1;
            margin-bottom: 6px;
        }}

        .temp-main {{
            font-size: 5rem;
            font-weight: 200;
            letter-spacing: -4px;
        }}

        .temp-unit {{
            font-size: 1.6rem;
            font-weight: 300;
            margin-top: 12px;
            color: var(--text-secondary);
        }}

        .feels-row {{
            font-size: 0.82rem;
            color: var(--text-secondary);
            margin-bottom: 10px;
        }}

        .condition-tag {{
            display: inline-block;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.5px;
            color: var(--text-primary);
            background: rgba(255,255,255,0.08);
            padding: 5px 14px;
            border-radius: 100px;
            border: 1px solid var(--glass-border);
            margin-bottom: 12px;
        }}

        .hero-right {{
            flex-shrink: 0;
            padding-top: 8px;
        }}

        .main-icon {{
            width: 120px;
            height: 120px;
            filter: drop-shadow(0 8px 24px rgba(56,189,248,0.3));
            animation: float 5s ease-in-out infinite;
        }}

        @keyframes float {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-8px); }}
        }}

        /* ── AQI Badge ── */
        .aqi-badge {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.78rem;
            color: var(--text-secondary);
            flex-wrap: wrap;
        }}

        .aqi-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--aqi-color);
            flex-shrink: 0;
            box-shadow: 0 0 6px var(--aqi-color);
        }}

        .aqi-badge strong {{ color: var(--aqi-color); }}
        .aqi-detail {{ color: var(--text-muted); }}

        /* ── Section Labels ── */
        .section-label {{
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 1.5px;
            color: var(--text-muted);
            margin-bottom: 12px;
        }}

        /* ── Hourly Scroll ── */
        .hourly-scroll-wrap {{ margin-bottom: 24px; }}

        .hourly-scroll {{
            display: flex;
            gap: 10px;
            overflow-x: auto;
            padding-bottom: 8px;
            scrollbar-width: none;
        }}

        .hourly-scroll::-webkit-scrollbar {{ display: none; }}

        .hour-card {{
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            padding: 14px 12px;
            background: var(--glass);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-sm);
            backdrop-filter: blur(12px);
            min-width: 68px;
            transition: background 0.2s;
        }}

        .hour-card:hover {{ background: var(--glass-hover); }}

        .h-time {{
            font-size: 0.72rem;
            color: var(--text-muted);
            font-weight: 600;
        }}

        .h-icon {{ width: 36px; height: 36px; }}

        .h-temp {{
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-primary);
        }}

        .h-pop {{
            font-size: 0.65rem;
            color: #60a5fa;
            min-height: 12px;
        }}

        /* ── Metrics Grid ── */
        .metrics-section {{ margin-bottom: 24px; }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }}

        .metric-card {{
            background: var(--glass);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-card);
            padding: 18px 16px 14px;
            display: flex;
            flex-direction: column;
            gap: 2px;
            backdrop-filter: blur(12px);
            transition: background 0.2s;
        }}

        .metric-card:hover {{ background: var(--glass-hover); }}

        .metric-icon {{
            font-size: 1.1rem;
            margin-bottom: 6px;
        }}

        .metric-body {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}

        .metric-label {{
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 1px;
            color: var(--text-muted);
            text-transform: uppercase;
        }}

        .metric-value {{
            font-size: 1.15rem;
            font-weight: 500;
            color: var(--text-primary);
        }}

        .metric-bar {{
            margin-top: 10px;
            height: 3px;
            background: rgba(255,255,255,0.08);
            border-radius: 2px;
            overflow: hidden;
        }}

        .metric-fill {{
            height: 100%;
            background: var(--accent);
            border-radius: 2px;
            transition: width 1s ease;
        }}

        /* ── 5-Day Forecast ── */
        .forecast-section {{ margin-bottom: 24px; }}

        .daily-list {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .day-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 20px;
            background: var(--glass);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-card);
            backdrop-filter: blur(12px);
            gap: 12px;
            transition: background 0.2s;
        }}

        .day-row:hover {{ background: var(--glass-hover); }}

        .day-info {{
            display: flex;
            flex-direction: column;
            min-width: 44px;
        }}

        .day-name {{
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--text-primary);
        }}

        .day-date {{
            font-size: 0.72rem;
            color: var(--text-muted);
        }}

        .day-mid {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex: 1;
        }}

        .day-icon {{ width: 40px; height: 40px; }}

        .day-desc {{
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}

        .day-right {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .day-pop {{
            font-size: 0.75rem;
            color: #60a5fa;
        }}

        .day-temps {{
            font-size: 0.95rem;
            color: var(--text-primary);
            white-space: nowrap;
        }}

        .day-temps .lo {{ color: var(--text-muted); font-weight: 400; }}

        /* ── Geo Footer ── */
        .geo-footer {{
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 8px;
            font-size: 0.75rem;
            color: var(--text-muted);
            padding: 12px 4px;
        }}

        /* ── Responsive ── */
        @media (max-width: 480px) {{
            header {{
                flex-wrap: wrap;
            }}
            .brand {{ width: 100%; }}
            .search-form {{ width: 100%; }}
            .hero-section {{ flex-direction: column; }}
            .hero-right {{ display: flex; justify-content: center; width: 100%; padding: 0; }}
            .city-name {{ font-size: 1.8rem; }}
            .temp-main {{ font-size: 4rem; }}
            .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            .main-icon {{ animation: none; }}
            * {{ transition: none !important; }}
        }}
    </style>
</head>
<body>
<div class="page">
    <header>
        <div class="brand">nim<span>bus</span></div>
        <form method="get" action="/" class="search-form">
            <input
                class="search-input"
                type="text"
                name="city"
                placeholder="Search city..."
                value="{city or ''}"
                autocomplete="off"
                autofocus
            >
            <button type="submit" class="search-btn">Search</button>
        </form>
    </header>

    {weather_html}
</div>
</body>
</html>
"""
    return html_content