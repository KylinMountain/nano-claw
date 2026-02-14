"""
通用工具实现 - 展示如何扩展到非编程领域
"""
import os
import json
import asyncio
import aiohttp
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .base import ToolBuilder, ToolInvocation, ToolKind, ToolResult


class WebSearchInvocation(ToolInvocation):
    """网络搜索工具调用"""
    
    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            query = self.params.get("query", "")
            max_results = self.params.get("max_results", 5)
            
            # 这里使用DuckDuckGo的即时答案API作为示例
            # 实际使用中可以集成Google Search API、Bing API等
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 提取搜索结果
                        results = []
                        
                        # 即时答案
                        if data.get("AbstractText"):
                            results.append({
                                "type": "instant_answer",
                                "title": data.get("AbstractSource", ""),
                                "content": data.get("AbstractText", ""),
                                "url": data.get("AbstractURL", "")
                            })
                        
                        # 相关主题
                        for topic in data.get("RelatedTopics", [])[:max_results]:
                            if isinstance(topic, dict) and topic.get("Text"):
                                results.append({
                                    "type": "related_topic",
                                    "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                                    "content": topic.get("Text", ""),
                                    "url": topic.get("FirstURL", "")
                                })
                        
                        if results:
                            content = f"搜索结果: {query}\n\n"
                            for i, result in enumerate(results, 1):
                                content += f"{i}. **{result['title']}**\n"
                                content += f"   {result['content']}\n"
                                if result['url']:
                                    content += f"   链接: {result['url']}\n"
                                content += "\n"
                        else:
                            content = f"未找到关于 '{query}' 的相关信息"
                        
                        return ToolResult(
                            call_id=self.call_id,
                            success=True,
                            content=content
                        )
                    else:
                        return ToolResult(
                            call_id=self.call_id,
                            success=False,
                            content="",
                            error=f"搜索请求失败: HTTP {response.status}"
                        )
            
        except Exception as e:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error=str(e)
            )


class WebSearchTool(ToolBuilder):
    """网络搜索工具"""
    
    def __init__(self):
        super().__init__(
            name="web_search",
            display_name="Web Search",
            description="Search the web for information on any topic",
            kind=ToolKind.FETCH,
            parameter_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["query"]
            }
        )
    
    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return WebSearchInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id
        )


class WeatherQueryInvocation(ToolInvocation):
    """天气查询工具调用"""
    
    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            location = self.params.get("location", "")
            days = self.params.get("days", 1)
            
            # 使用免费的天气API (示例)
            # 实际使用中可以集成OpenWeatherMap、AccuWeather等
            api_key = os.getenv("WEATHER_API_KEY")
            if not api_key:
                return ToolResult(
                    call_id=self.call_id,
                    success=False,
                    content="",
                    error="Weather API key not configured"
                )
            
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": location,
                "appid": api_key,
                "units": "metric",
                "lang": "zh_cn"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        weather = data["weather"][0]
                        main = data["main"]
                        wind = data.get("wind", {})
                        
                        content = f"📍 {data['name']} 天气情况\n\n"
                        content += f"🌤️  天气: {weather['description']}\n"
                        content += f"🌡️  温度: {main['temp']}°C (体感 {main['feels_like']}°C)\n"
                        content += f"💧 湿度: {main['humidity']}%\n"
                        content += f"🌬️  风速: {wind.get('speed', 0)} m/s\n"
                        content += f"📊 气压: {main['pressure']} hPa\n"
                        
                        return ToolResult(
                            call_id=self.call_id,
                            success=True,
                            content=content
                        )
                    else:
                        return ToolResult(
                            call_id=self.call_id,
                            success=False,
                            content="",
                            error=f"天气查询失败: {location} 未找到"
                        )
            
        except Exception as e:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error=str(e)
            )


class WeatherQueryTool(ToolBuilder):
    """天气查询工具"""
    
    def __init__(self):
        super().__init__(
            name="weather_query",
            display_name="Weather Query",
            description="Get current weather information for any location",
            kind=ToolKind.FETCH,
            parameter_schema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or location (e.g., 'Beijing', 'New York')"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days for forecast (1-5)",
                        "default": 1,
                        "minimum": 1,
                        "maximum": 5
                    }
                },
                "required": ["location"]
            }
        )
    
    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return WeatherQueryInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id
        )


class EmailSendInvocation(ToolInvocation):
    """邮件发送工具调用"""
    
    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            to_email = self.params.get("to", "")
            subject = self.params.get("subject", "")
            body = self.params.get("body", "")
            
            # 从环境变量获取邮件配置
            smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            email_user = os.getenv("EMAIL_USER")
            email_password = os.getenv("EMAIL_PASSWORD")
            
            if not email_user or not email_password:
                return ToolResult(
                    call_id=self.call_id,
                    success=False,
                    content="",
                    error="Email credentials not configured"
                )
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = email_user
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 发送邮件
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_user, email_password)
            text = msg.as_string()
            server.sendmail(email_user, to_email, text)
            server.quit()
            
            return ToolResult(
                call_id=self.call_id,
                success=True,
                content=f"邮件已成功发送到 {to_email}"
            )
            
        except Exception as e:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error=f"邮件发送失败: {str(e)}"
            )


class EmailSendTool(ToolBuilder):
    """邮件发送工具"""
    
    def __init__(self):
        super().__init__(
            name="email_send",
            display_name="Send Email",
            description="Send an email to specified recipient",
            kind=ToolKind.COMMUNICATE,
            parameter_schema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body content"
                    }
                },
                "required": ["to", "subject", "body"]
            }
        )
    
    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return EmailSendInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id
        )


class CalendarEventInvocation(ToolInvocation):
    """日历事件工具调用"""
    
    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            title = self.params.get("title", "")
            date = self.params.get("date", "")
            time = self.params.get("time", "")
            duration = self.params.get("duration", 60)  # 分钟
            description = self.params.get("description", "")
            
            # 这里是一个简化的实现，实际中可以集成Google Calendar API
            # 或其他日历服务
            
            # 解析日期时间
            try:
                event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
                end_datetime = event_datetime + timedelta(minutes=duration)
            except ValueError:
                return ToolResult(
                    call_id=self.call_id,
                    success=False,
                    content="",
                    error="日期时间格式错误，请使用 YYYY-MM-DD HH:MM 格式"
                )
            
            # 创建事件信息
            event_info = {
                "title": title,
                "start": event_datetime.isoformat(),
                "end": end_datetime.isoformat(),
                "description": description
            }
            
            # 保存到本地文件（示例实现）
            events_file = os.path.expanduser("~/.nano_claw/calendar_events.json")
            os.makedirs(os.path.dirname(events_file), exist_ok=True)
            
            events = []
            if os.path.exists(events_file):
                with open(events_file, 'r', encoding='utf-8') as f:
                    events = json.load(f)
            
            events.append(event_info)
            
            with open(events_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, ensure_ascii=False, indent=2)
            
            content = f"📅 日历事件已创建\n\n"
            content += f"标题: {title}\n"
            content += f"时间: {event_datetime.strftime('%Y年%m月%d日 %H:%M')}\n"
            content += f"时长: {duration} 分钟\n"
            if description:
                content += f"描述: {description}\n"
            
            return ToolResult(
                call_id=self.call_id,
                success=True,
                content=content
            )
            
        except Exception as e:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error=str(e)
            )


class CalendarEventTool(ToolBuilder):
    """日历事件工具"""
    
    def __init__(self):
        super().__init__(
            name="calendar_event",
            display_name="Calendar Event",
            description="Create a calendar event with specified date and time",
            kind=ToolKind.OTHER,
            parameter_schema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Event title"
                    },
                    "date": {
                        "type": "string",
                        "description": "Event date in YYYY-MM-DD format"
                    },
                    "time": {
                        "type": "string",
                        "description": "Event time in HH:MM format (24-hour)"
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Event duration in minutes",
                        "default": 60
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description (optional)"
                    }
                },
                "required": ["title", "date", "time"]
            }
        )
    
    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return CalendarEventInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id
        )


class NoteInvocation(ToolInvocation):
    """笔记工具调用"""
    
    async def execute(self, cancellation_event: asyncio.Event) -> ToolResult:
        try:
            action = self.params.get("action", "create")
            title = self.params.get("title", "")
            content = self.params.get("content", "")
            category = self.params.get("category", "general")
            
            notes_dir = os.path.expanduser("~/.nano_claw/notes")
            os.makedirs(notes_dir, exist_ok=True)
            
            if action == "create":
                # 创建新笔记
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{title.replace(' ', '_')}.md"
                filepath = os.path.join(notes_dir, filename)
                
                note_content = f"# {title}\n\n"
                note_content += f"**分类**: {category}\n"
                note_content += f"**创建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                note_content += f"---\n\n{content}\n"
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(note_content)
                
                return ToolResult(
                    call_id=self.call_id,
                    success=True,
                    content=f"📝 笔记已创建: {title}\n文件: {filename}"
                )
            
            elif action == "list":
                # 列出所有笔记
                notes = []
                for filename in os.listdir(notes_dir):
                    if filename.endswith('.md'):
                        filepath = os.path.join(notes_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            first_line = f.readline().strip()
                            if first_line.startswith('# '):
                                title = first_line[2:]
                                notes.append({
                                    "filename": filename,
                                    "title": title,
                                    "modified": datetime.fromtimestamp(
                                        os.path.getmtime(filepath)
                                    ).strftime('%Y-%m-%d %H:%M')
                                })
                
                if notes:
                    content = "📚 笔记列表:\n\n"
                    for note in sorted(notes, key=lambda x: x['modified'], reverse=True):
                        content += f"- **{note['title']}** ({note['modified']})\n"
                else:
                    content = "暂无笔记"
                
                return ToolResult(
                    call_id=self.call_id,
                    success=True,
                    content=content
                )
            
            else:
                return ToolResult(
                    call_id=self.call_id,
                    success=False,
                    content="",
                    error=f"不支持的操作: {action}"
                )
            
        except Exception as e:
            return ToolResult(
                call_id=self.call_id,
                success=False,
                content="",
                error=str(e)
            )


class NoteTool(ToolBuilder):
    """笔记工具"""
    
    def __init__(self):
        super().__init__(
            name="note",
            display_name="Note Taking",
            description="Create and manage personal notes",
            kind=ToolKind.OTHER,
            parameter_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action to perform",
                        "enum": ["create", "list"],
                        "default": "create"
                    },
                    "title": {
                        "type": "string",
                        "description": "Note title (required for create action)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Note content (required for create action)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Note category",
                        "default": "general"
                    }
                }
            }
        )
    
    def build(self, call_id: str, params: Dict[str, Any]) -> ToolInvocation:
        return NoteInvocation(
            name=self.name,
            display_name=self.display_name,
            kind=self.kind,
            params=params,
            call_id=call_id
        )


def register_universal_tools(registry):
    """注册通用工具"""
    registry.register(WebSearchTool())
    registry.register(WeatherQueryTool())
    registry.register(EmailSendTool())
    registry.register(CalendarEventTool())
    registry.register(NoteTool())