import os
import sys
import requests
from mcp.server import MCPServer
from typing import Any

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ============================================================
# 配置
# ============================================================

API_KEY = os.getenv("QWEATHER_API_KEY", "")
BASE_URL = os.getenv("QWEATHER_API_HOST", "https://m46r738ubk.re.qweatherapi.com")

if not API_KEY:
    print("❌ 错误：未设置 QWEATHER_API_KEY 环境变量", file=sys.stderr)
    print("💡 请设置：export QWEATHER_API_KEY='你的密钥'", file=sys.stderr)
    sys.exit(1)

# 常用城市 LocationID 缓存
CITY_ID_MAP = {
    "北京": "101010100", "上海": "101020100",
    "广州": "101280101", "深圳": "101280601",
    "杭州": "101210101", "成都": "101270101",
    "重庆": "101040100", "武汉": "101200101",
    "西安": "101110101", "南京": "101190101",
}

# ============================================================
# MCP 服务器实例
# ============================================================

mcp = MCPServer("weather-api-server")

# ============================================================
# 内部辅助函数（无变更）
# ============================================================

def _get_location_id(city: str) -> str | None:
    """根据城市名返回 LocationID（先查本地表，再用 GeoAPI 兜底）"""
    if city in CITY_ID_MAP:
        return CITY_ID_MAP[city]

    url = f"{BASE_URL}/geo/v2/city/lookup"
    headers = {"X-QW-Api-Key": API_KEY}
    try:
        r = requests.get(url, headers=headers, params={"location": city}, timeout=10)
        if r.status_code != 200:
            print(f"GeoAPI 请求失败: {r.status_code}", file=sys.stderr)
            return None
        locs = r.json().get("location", [])
        return locs[0]["id"] if locs else None
    except Exception as e:
        print(f"GeoAPI 异常: {e}", file=sys.stderr)
        return None


def _fetch_weather(city: str) -> dict[str, Any] | None:
    """调用和风天气 API 获取当前天气"""
    location_id = _get_location_id(city)
    if not location_id:
        print(f"未找到城市 '{city}' 的 LocationID", file=sys.stderr)
        return None

    url = f"{BASE_URL}/v7/weather/now"
    headers = {"X-QW-Api-Key": API_KEY}

    print("call _fetch_weather()", file=sys.stderr)

    try:
        r = requests.get(url, headers=headers, params={"location": location_id}, timeout=15)
        if r.status_code == 401:
            print("QWeather API Key 无效", file=sys.stderr)
            return None
        if r.status_code == 403:
            print("QWeather Host 或 Key 不匹配", file=sys.stderr)
            return None
        if r.status_code != 200:
            print(f"API 请求失败: {r.status_code}", file=sys.stderr)
            return None

        data = r.json()
        if data.get("code") != "200":
            print(f"接口返回错误码: {data.get('code')}", file=sys.stderr)
            return None

        now = data["now"]
        return {
            "city": city,
            "temp": float(now["temp"]),
            "feels_like": float(now["feelsLike"]),
            "humidity": int(now["humidity"]),
            "weather": now["text"],
            "wind_speed": float(now["windSpeed"]),
            "wind_deg": int(now["wind360"]),
            "pressure": int(now["pressure"]),
            "visibility": int(now["vis"]),
        }
    except requests.exceptions.Timeout:
        print("API 请求超时", file=sys.stderr)
        return None
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        return None

def _fetch_forecast(city: str, days: int = 7) -> dict[str, Any] | None:
    """调用和风天气 API 获取未来天气预报

    Args:
        city: 城市名称
        days: 预报天数，支持 3 / 7 / 10 / 15 / 30
    """
    # 和风天气每日预报仅支持固定档位
    valid_days = [3, 7, 10, 15, 30]
    if days not in valid_days:
        # 向上取最近的支持档位
        for d in valid_days:
            if days <= d:
                days = d
                break
        else:
            days = 30

    location_id = _get_location_id(city)
    if not location_id:
        print(f"未找到城市 '{city}' 的 LocationID", file=sys.stderr)
        return None

    url = f"{BASE_URL}/v7/weather/{days}d"
    headers = {"X-QW-Api-Key": API_KEY}

    print(f"call _fetch_forecast({days}d)", file=sys.stderr)

    try:
        r = requests.get(url, headers=headers, params={"location": location_id}, timeout=15)
        if r.status_code == 401:
            print("QWeather API Key 无效", file=sys.stderr)
            return None
        if r.status_code == 403:
            print("QWeather Host 或 Key 不匹配", file=sys.stderr)
            return None
        if r.status_code != 200:
            print(f"API 请求失败: {r.status_code}", file=sys.stderr)
            return None

        data = r.json()
        if data.get("code") != "200":
            print(f"接口返回错误码: {data.get('code')}", file=sys.stderr)
            return None

        daily_list = []
        for d in data.get("daily", []):
            daily_list.append({
                "date": d["fxDate"],
                "temp_max": float(d["tempMax"]),
                "temp_min": float(d["tempMin"]),
                "day_weather": d["textDay"],
                "night_weather": d["textNight"],
                "day_wind_dir": d["windDirDay"],
                "day_wind_scale": d["windScaleDay"],
                "day_wind_speed": float(d["windSpeedDay"]),
                "humidity": int(d["humidity"]),
                "precip": float(d["precip"]),
                "uv_index": int(d["uvIndex"]),
                "sunrise": d.get("sunrise", ""),
                "sunset": d.get("sunset", ""),
            })

        return {
            "city": city,
            "days": days,
            "update_time": data.get("updateTime", ""),
            "daily": daily_list,
        }
    except requests.exceptions.Timeout:
        print("API 请求超时", file=sys.stderr)
        return None
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        return None


def _fetch_astronomy_sun(city: str, date: str | None = None) -> dict[str, Any] | None:
    """调用和风天气 API 获取指定日期的日出日落时间

    Args:
        city: 城市名称或 LocationID
        date: 日期，格式 yyyyMMdd，默认今天，最多支持未来 60 天
    """
    from datetime import datetime, timedelta

    # 未指定日期则默认今天
    if not date:
        date = datetime.now().strftime("%Y%m%d")
    else:
        date = date.strip().replace("-", "").replace("/", "")
        # 简单校验日期格式
        try:
            dt = datetime.strptime(date, "%Y%m%d")
            # 限制范围：今天 ~ 未来 60 天
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            max_date = today + timedelta(days=60)
            if dt < today or dt > max_date:
                print(f"日期超出范围（需在今天~未来60天内）: {date}", file=sys.stderr)
                return None
        except ValueError:
            print(f"日期格式无效（应为 yyyyMMdd）: {date}", file=sys.stderr)
            return None

    location_id = _get_location_id(city)
    if not location_id:
        print(f"未找到城市 '{city}' 的 LocationID", file=sys.stderr)
        return None

    url = f"{BASE_URL}/v7/astronomy/sun"
    headers = {"X-QW-Api-Key": API_KEY}

    print(f"call _fetch_astronomy_sun({city}, {date})", file=sys.stderr)

    try:
        r = requests.get(
            url,
            headers=headers,
            params={"location": location_id, "date": date},
            timeout=15,
        )
        if r.status_code == 401:
            print("QWeather API Key 无效", file=sys.stderr)
            return None
        if r.status_code == 403:
            print("QWeather Host 或 Key 不匹配", file=sys.stderr)
            return None
        if r.status_code != 200:
            print(f"API 请求失败: {r.status_code}", file=sys.stderr)
            return None

        data = r.json()
        if data.get("code") != "200":
            print(f"接口返回错误码: {data.get('code')}", file=sys.stderr)
            return None

        return {
            "city": city,
            "date": date,
            "sunrise": data.get("sunrise", ""),
            "sunset": data.get("sunset", ""),
            "update_time": data.get("updateTime", ""),
        }
    except requests.exceptions.Timeout:
        print("API 请求超时", file=sys.stderr)
        return None
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        return None

    

def _temp_trend_advice(daily: list[dict]) -> str:
    """根据未来几天的温度变化给出趋势提示"""
    if not daily:
        return ""

    temps_max = [d["temp_max"] for d in daily]
    temps_min = [d["temp_min"] for d in daily]

    # 温差提醒
    total_range = max(temps_max) - min(temps_min)
    msg_parts = []

    if total_range > 15:
        msg_parts.append(f"📊 未来 {len(daily)} 天温差较大（{min(temps_min):.0f}~{max(temps_max):.0f}°C），注意增减衣物")

    # 降温提醒（对比首尾）
    if len(daily) >= 3:
        recent = sum(temps_max[:2]) / 2
        later = sum(temps_max[-2:]) / 2
        diff = later - recent
        if diff <= -5:
            msg_parts.append(f"❄️ 后期明显降温（约 {diff:.0f}°C），请提前准备保暖衣物")
        elif diff >= 5:
            msg_parts.append(f"🔥 后期明显升温（约 +{diff:.0f}°C），注意适时减衣")

    # 降水提醒
    rainy_days = [d for d in daily if d["precip"] > 0.1 or "雨" in d["day_weather"] or "雪" in d["day_weather"]]
    if rainy_days:
        dates = "、".join(d["date"][5:] for d in rainy_days[:3])
        suffix = " 等" if len(rainy_days) > 3 else ""
        msg_parts.append(f"🌧️ 预计 {dates}{suffix} 共 {len(rainy_days)} 天有降水，出行记得带伞")

    return "\n".join(msg_parts) if msg_parts else "📊 未来天气整体平稳，适合安排出行"


def _format_time(iso_time: str) -> str:
    """将 ISO 8601 时间字符串格式化为 HH:MM"""
    if not iso_time:
        return "—"
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso_time)
        return dt.strftime("%H:%M")
    except Exception:
        # 如果已经是 HH:MM 格式，直接返回
        return iso_time
    

def _dressing_advice(temp: float) -> str:
    """根据温度给出穿衣建议"""
    if temp < 0:
        return "极寒，建议穿羽绒服、棉服等极保暖衣物，帽子围巾手套缺一不可"
    elif temp < 10:
        return "寒冷，建议穿毛衣、厚外套、羽绒服等保暖衣物"
    elif temp < 15:
        return "较凉，建议穿外套、薄毛衣、卫衣等春秋装"
    elif temp < 20:
        return "凉爽，建议穿长袖衬衫、薄外套、牛仔裤等"
    elif temp < 25:
        return "舒适，建议穿短袖、长裤、薄外套等春秋装"
    elif temp < 30:
        return "温暖，建议穿短袖、薄裤、防晒衣等夏季服装"
    else:
        return "炎热，建议穿短袖短裤，注意防暑降温"


def _exercise_advice(weather: str, wind_speed: float) -> str:
    """根据天气给出运动建议"""
    if weather in ["雷阵雨", "雷雨", "暴风雨"]:
        return "⚠️ 不建议户外运动，建议室内锻炼"
    elif "雨" in weather:
        return "🌧️ 不适合户外运动，可以在家做室内运动"
    elif "雪" in weather:
        return "❄️ 注意路滑，可以室内运动或玩雪"
    elif wind_speed > 10:
        return "💨 风力较大，不建议户外运动"
    elif weather in ["晴", "多云", "阴"]:
        return "✅ 适合户外运动，但请注意防晒和补水"
    else:
        return "✅ 天气适宜，可以适当户外运动"


# ============================================================
# MCP 工具定义（装饰器 API 在 v2 中完全兼容）
# ============================================================

@mcp.tool()
def get_current_weather(city: str, units: str = "metric") -> str:
    """
    获取指定城市的当前天气信息，包括温度、湿度、风力等详细数据。

    Args:
        city: 城市名称（支持中文或英文，例如：北京、Shanghai）
        units: 温度单位，metric（摄氏度，默认）或 imperial（华氏度）

    Returns:
        格式化的天气报告文本
    """
    city = city.strip()
    if not city:
        return "❌ 错误：请提供城市名称"

    weather = _fetch_weather(city)
    if not weather:
        return (
            f"❌ 无法获取「{city}」的天气数据。\n\n"
            f"请确认：\n"
            f"• 城市名称是否正确\n"
            f"• API Key 是否有效\n"
            f"• 网络连接是否正常"
        )

    temp_unit = "°C" if units == "metric" else "°F"
    dressing = _dressing_advice(weather.get("temp", 20))
    exercise = _exercise_advice(
        weather.get("weather", "未知"),
        weather.get("wind_speed", 0)
    )

    return f"""
🌤️ 【{city}】实时天气
━━━━━━━━━━━━━━━━━━━━━━━━━
🌡️ 温度：{weather['temp']}{temp_unit}（体感 {weather['feels_like']}{temp_unit}）
💧 湿度：{weather['humidity']}%
🌬️ 风力：{weather['wind_speed']} km/h
☁️ 天气：{weather['weather']}
🌅 能见度：{weather['visibility']} km
━━━━━━━━━━━━━━━━━━━━━━━━━
👔 {dressing}
🏃 {exercise}
""".strip()


@mcp.tool()
def get_weather_forecast(city: str, days: int = 7, units: str = "metric") -> str:
    """
    获取指定城市未来几天的天气预报，包括每日温度范围、天气状况、风力、降水等。

    Args:
        city: 城市名称（支持中文或英文，例如：北京、Shanghai）
        days: 预报天数，支持 3、7、10、15、30（默认 7），传入其他值会自动向上取最近档位
        units: 温度单位，metric（摄氏度，默认）或 imperial（华氏度）

    Returns:
        格式化的多日天气预报文本
    """
    city = city.strip()
    if not city:
        return "❌ 错误：请提供城市名称"

    forecast = _fetch_forecast(city, days)
    if not forecast:
        return (
            f"❌ 无法获取「{city}」的天气预报数据。\n\n"
            f"请确认：\n"
            f"• 城市名称是否正确\n"
            f"• API Key 是否有效\n"
            f"• 网络连接是否正常"
        )

    temp_unit = "°C" if units == "metric" else "°F"
    daily = forecast["daily"]

    # 逐日明细
    lines = []
    for d in daily:
        # 日期格式化为 MM-DD 周X
        date_str = d["date"]
        try:
            from datetime import datetime
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][dt.weekday()]
            date_display = f"{dt.strftime('%m-%d')} {weekday}"
        except Exception:
            date_display = date_str

        # 天气图标
        w = d["day_weather"]
        if "雪" in w:
            icon = "❄️"
        elif "雨" in w:
            icon = "🌧️"
        elif "阴" in w:
            icon = "☁️"
        elif "多云" in w:
            icon = "⛅"
        elif "晴" in w:
            icon = "☀️"
        else:
            icon = "🌤️"

        lines.append(
            f"{date_display}  {icon} {d['day_weather']} / {d['night_weather']}  "
            f"{d['temp_min']:.0f}~{d['temp_max']:.0f}{temp_unit}  "
            f"{d['day_wind_dir']}{d['day_wind_scale']}级"
        )

    forecast_block = "\n".join(lines)
    trend = _temp_trend_advice(daily)

    return f"""
📅 【{city}】未来 {forecast['days']} 天天气预报
━━━━━━━━━━━━━━━━━━━━━━━━━
{forecast_block}
━━━━━━━━━━━━━━━━━━━━━━━━━
{trend}
""".strip()

@mcp.tool()
def get_astronomy_sun(city: str, date: str = "") -> str:
    """
    获取指定城市在指定日期的日出日落时间。

    Args:
        city: 城市名称（支持中文或英文，例如：北京、Shanghai）
        date: 日期，格式 yyyyMMdd（如 20260920）或 yyyy-MM-dd，默认为今天。
              最多可查询未来 60 天（含今天）的数据。

    Returns:
        格式化的日出日落信息文本
    """
    city = city.strip()
    if not city:
        return "❌ 错误：请提供城市名称"

    result = _fetch_astronomy_sun(city, date if date else None)
    if not result:
        return (
            f"❌ 无法获取「{city}」的天文数据。\n\n"
            f"请确认：\n"
            f"• 城市名称是否正确\n"
            f"• 日期格式是否为 yyyyMMdd 且在 60 天内\n"
            f"• API Key 是否有效\n"
            f"• 网络连接是否正常"
        )

    # 格式化日期显示
    from datetime import datetime
    try:
        dt = datetime.strptime(result["date"], "%Y%m%d")
        date_display = dt.strftime("%Y-%m-%d")
        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][dt.weekday()]
        date_display = f"{date_display} {weekday}"
    except Exception:
        date_display = result["date"]

    sunrise = _format_time(result["sunrise"])
    sunset = _format_time(result["sunset"])

    # 计算日照时长（若两个时间都有效）
    daylight = ""
    if sunrise != "—" and sunset != "—":
        try:
            from datetime import datetime
            sr = datetime.strptime(sunrise, "%H:%M")
            ss = datetime.strptime(sunset, "%H:%M")
            delta = ss - sr
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            daylight = f"\n☀️ 日照时长：约 {hours} 小时 {minutes} 分钟"
        except Exception:
            pass

    return f"""
🌅 【{city}】天文数据
━━━━━━━━━━━━━━━━━━━━━━━━━
📅 日期：{date_display}
🌄 日出：{sunrise}
🌇 日落：{sunset}{daylight}
━━━━━━━━━━━━━━━━━━━━━━━━━
💡 数据来源：和风天气天文 API
""".strip()


# ============================================================
# 服务器启动
# ============================================================

def sync_main() -> None:
    """同步入口，供 pyproject.toml 的 [project.scripts] 调用。"""
    print("🌤️ 天气 MCP 服务器启动中...", file=sys.stderr)
    print(f"✅ API 已配置，Host: {BASE_URL}", file=sys.stderr)
    print(
        "🛠️ 已注册工具：get_current_weather、get_weather_forecast、get_astronomy_sun",
        file=sys.stderr,
    )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    sync_main()