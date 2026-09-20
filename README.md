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
gget_current_weather	查询指定城市的实时天气信息，包括温度、湿度、风力以及穿衣和运动建议	city (string, 必填)

pip freeze > requirements.txt

验证步骤：
1 本机验证
npx @modelcontextprotocol/inspector --config inspector.json


2 traecode验证
{
  "mcpServers": {
    "mimo_weather": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/linwu54050/mimo_weather_server.git",
        "weather-server"
      ]
    }
  }
}