Weather MCP Server
一个基于 MCP (Model Context Protocol) 协议的天气查询服务器，为 AI 助手提供实时天气查询、天气预报和生活建议能力。

📖 项目简介
本项目实现了一个 MCP 服务器，通过标准输入输出（stdio）与 AI 客户端通信，暴露以下能力：

工具（Tools）：可供 AI 调用的函数，如查询天气、获取预报

资源（Resources）：可供 AI 读取的静态内容，如天气生活小贴士

⚠️ 注意：当前天气数据为模拟数据，仅用于演示 MCP 协议的使用方式。实际生产环境请接入真实天气 API。

✨ 功能特性
工具（Tools）
工具名	描述	参数
get_weather	查询指定城市的实时天气信息，包括温度、湿度、风力以及穿衣和运动建议	city (string, 必填)
get_forecast	获取指定城市未来天气预报	city (string, 必填)
days (number, 可选, 1-7, 默认 3)
支持的城市：北京、上海、广州、深圳、杭州

资源（Resources）
URI	描述
weather://tips	天气相关生活提示（穿衣指数、运动建议、出行建议、健康提示）
🛠️ 环境要求
Python >= 3.10

依赖：

mcp==1.29.0

requests==2.34.2

📦 安装
方式一：使用 pip 安装
bash
pip install .
安装后可使用命令行入口：

bash
weather-server
方式二：开发模式安装
bash
pip install -e .
方式三：使用 uv（推荐）
bash
uv sync
🚀 使用方法
直接运行
bash
python weather_server.py
或使用安装后的脚本入口：

bash
weather-server
服务器将启动并通过 stdio 等待 MCP 客户端连接。

配置到 MCP 客户端
以 Claude Desktop 为例，在配置文件中添加：

json
{
  "mcpServers": {
    "weather-server": {
      "command": "python",
      "args": ["/path/to/weather_server.py"]
    }
  }
}
若已通过 pip install . 安装，也可以直接使用脚本入口：

json
{
  "mcpServers": {
    "weather-server": {
      "command": "weather-server"
    }
  }
}
调用示例
查询天气：

json
{
  "name": "get_weather",
  "arguments": {
    "city": "深圳"
  }
}
返回结果：

text
🌤️  深圳当前天气
━━━━━━━━━━━━━━
🌡️ 温度：27°C
💧 湿度：80%
☁️ 天气：雷阵雨
🌬️ 风力：东南风4级
━━━━━━━━━━━━━━
👔 穿衣建议：建议穿短袖、薄衫等夏季服装
🏃 运动建议：天气不佳，建议室内运动
查询预报：

json
{
  "name": "get_forecast",
  "arguments": {
    "city": "北京",
    "days": 5
  }
}
📁 项目结构
text
.
├── weather_server.py    # MCP 服务器主程序
├── pyproject.toml       # 项目配置文件
└── README.md            # 项目说明文档
🔧 核心实现说明
1. 创建服务器
python
server = Server("weather-server")
2. 注册工具列表
使用 @server.list_tools() 装饰器声明可用工具，包含工具的 name、description 和 inputSchema。

3. 处理工具调用
使用 @server.call_tool() 装饰器处理调用请求，根据 name 分发到不同逻辑。

4. 注册资源
使用 @server.list_resources() 和 @server.read_resource() 提供资源访问能力。

5. 启动服务器
通过 stdio_server() 建立标准输入输出通道并运行：

python
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )
🧪 扩展方向
接入真实天气 API（如和风天气、OpenWeatherMap）

支持更多城市（当前为模拟数据，需替换为动态查询）

添加更多工具，如空气质量查询、紫外线指数

支持更多资源，如城市列表、天气预警

📄 License
本项目仅用于学习和演示 MCP 协议的使用方式。

