import os
import sys
import requests
from mcp.server import MCPServer
from typing import Any

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import os, sys
print(f"[DEBUG] KEY exists: {bool(os.getenv('QWEATHER_API_KEY'))}", file=sys.stderr)
print(f"[DEBUG] HOST: {os.getenv('QWEATHER_API_HOST', '(none)')}", file=sys.stderr)

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


# ============================================================
# 服务器启动
# ============================================================

if __name__ == "__main__":
    print("🌤️ 天气 MCP 服务器启动中...", file=sys.stderr)
    print(f"✅ API 已配置，Host: {BASE_URL}", file=sys.stderr)
    print(f"💡 使用 mcp dev weather_server.py 进行调试", file=sys.stderr)

    # 使用 stdio 传输（适合本地开发调试）
    # 注：v2 中传输配置已移至 run() 方法，但 stdio 用法保持不变
    mcp.run(transport="stdio")