#!/usr/bin/env python3
"""
测试 MCP 集成
"""
import asyncio
import logging
from mcp_client.client import MCPManager, MCPServerConfig

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_mcp():
    """测试 MCP 功能"""
    manager = MCPManager()
    
    # 配置一个简单的文件系统服务器
    config = MCPServerConfig(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        env={}
    )
    
    try:
        # 连接服务器
        logger.info("正在连接 MCP 服务器...")
        success = await manager.add_server(config)
        
        if success:
            logger.info("✅ MCP 服务器连接成功!")
            
            # 列出可用工具
            adapters = manager.get_adapters()
            logger.info(f"发现 {len(adapters)} 个工具:")
            
            for adapter in adapters:
                logger.info(f"  - {adapter.display_name}: {adapter.description}")
            
            # 测试一个简单的工具调用（如果有的话）
            if adapters:
                test_adapter = adapters[0]
                logger.info(f"测试工具: {test_adapter.display_name}")
                
                # 这里可以添加具体的工具测试
                # 但需要根据实际工具的参数来调整
                
        else:
            logger.error("❌ MCP 服务器连接失败")
            
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        
    finally:
        # 清理连接
        await manager.disconnect_all()
        logger.info("MCP 连接已清理")


if __name__ == "__main__":
    asyncio.run(test_mcp())
