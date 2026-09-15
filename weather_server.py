from mcp.server import Server
from mcp.types import Tool, TextContent, Resource
from mcp.server.stdio import stdio_server
import requests

# 创建服务器
server = Server("weather-server")

# 模拟天气数据（实际项目请用真实 API）
WEATHER_DATA = {
    "北京": {"temp": 15, "humidity": 45, "weather": "晴", "wind": "北风3级"},
    "上海": {"temp": 22, "humidity": 65, "weather": "多云", "wind": "东风2级"},
    "广州": {"temp": 28, "humidity": 75, "weather": "阵雨", "wind": "南风3级"},
    "深圳": {"temp": 27, "humidity": 80, "weather": "雷阵雨", "wind": "东南风4级"},
    "杭州": {"temp": 20, "humidity": 55, "weather": "阴", "wind": "东北风2级"},
}

# 获取穿衣指数
def get_dressing_tip(temp):
    if temp < 10:
        return "建议穿毛衣、羽绒服等保暖衣物"
    elif temp < 20:
        return "建议穿外套、衬衫等春秋装"
    else:
        return "建议穿短袖、薄衫等夏季服装"

# 获取运动建议
def get_sport_tip(weather):
    if weather in ["晴", "多云"]:
        return "适合户外运动"
    elif weather in ["小雨", "中雨"]:
        return "不建议户外运动，可以室内锻炼"
    else:
        return "天气不佳，建议室内运动"

# 列出所有工具
@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="get_weather",
            description="查询指定城市的实时天气信息，包括温度、湿度、风力、"
                        "以及穿衣和运动建议。支持北京、上海、深圳、杭州等城市。"
                        "当用户询问天气时，优先使用此工具，不要使用网络搜索。",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称（支持：北京、上海、广州、深圳、杭州等）"
                    }
                },
                "required": ["city"]
            }
        ),
        Tool(
            name="get_forecast",
            description="获取指定城市未来天气预报",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称"
                    },
                    "days": {
                        "type": "number",
                        "description": "预报天数（1-7天）",
                        "minimum": 1,
                        "maximum": 7,
                        "default": 3
                    }
                },
                "required": ["city"]
            }
        )
    ]

# 处理工具调用
@server.call_tool()
async def call_tool(name: str, arguments: dict):
    city = arguments.get("city", "")
    days = arguments.get("days", 3)
    
    # 标准化城市名称
    city = city.strip()
    
    if name == "get_weather":
        if city not in WEATHER_DATA:
            available = "、".join(WEATHER_DATA.keys())
            return [TextContent(
                type="text",
                text=f"抱歉，暂不支持查询「{city}」的天气。\n目前支持的城市有：{available}"
            )]
        
        weather = WEATHER_DATA[city]
        tip = get_dressing_tip(weather["temp"])
        sport = get_sport_tip(weather["weather"])
        
        result = f"""
🌤️  {city}当前天气
━━━━━━━━━━━━━━
🌡️ 温度：{weather['temp']}°C
💧 湿度：{weather['humidity']}%
☁️ 天气：{weather['weather']}
🌬️ 风力：{weather['wind']}
━━━━━━━━━━━━━━
👔 穿衣建议：{tip}
🏃 运动建议：{sport}
""".strip()
        
        return [TextContent(type="text", text=result)]
    
    elif name == "get_forecast":
        if city not in WEATHER_DATA:
            available = "、".join(WEATHER_DATA.keys())
            return [TextContent(
                type="text",
                text=f"抱歉，暂不支持查询「{city}」的天气。\n目前支持的城市有：{available}"
            )]
        
        # 生成模拟预报
        forecast = []
        weather_list = ["晴", "多云", "阴", "小雨", "晴"]
        temp_list = [18, 20, 15, 22, 25]
        
        result = f"📅 {city}未来{days}天天气预报\n━━━━━━━━━━━━━━\n"
        
        for i in range(min(days, 5)):
            day_name = f"第{i+1}天"
            w = weather_list[i % len(weather_list)]
            t = temp_list[i % len(temp_list)]
            result += f"{day_name}：{w}，{t}°C\n"
        
        result += "━━━━━━━━━━━━━━\n⚠️ 注：预报数据为模拟数据，仅供演示"
        
        return [TextContent(type="text", text=result)]
    
    raise ValueError(f"Unknown tool: {name}")

# 列出所有资源
@server.list_resources()
async def list_resources():
    return [
        Resource(
            uri="weather://tips",
            name="weather_tips",
            description="天气相关生活提示",
            mimeType="text/plain"
        )
    ]

# 读取资源
@server.read_resource()
async def read_resource(uri: str):
    if uri == "weather://tips":
        return """
🌤️ 天气生活小贴士

1️⃣ 穿衣指数
• 温度低于10°C：羽绒服、毛衣
• 温度10-20°C：外套、衬衫
• 温度20°C以上：短袖、薄衫

2️⃣ 运动建议
• 晴天/多云：适合户外运动
• 阴天/小雨：室内锻炼更合适
• 雨天/雪天：避免户外运动

3️⃣ 出行建议
• 雾霾天：戴口罩，减少户外活动
• 高温天：多喝水，避免中暑
• 雨天：带伞，注意路滑

4️⃣ 健康提示
• 换季时注意增减衣物
• 雨天湿气重，注意祛湿
• 晴天紫外线强，注意防晒
""".strip()
    
    raise ValueError(f"Unknown resource: {uri}")

# 启动服务器
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

def sync_main():
    import asyncio
    asyncio.run(main())

if __name__ == "__main__":
    sync_main()