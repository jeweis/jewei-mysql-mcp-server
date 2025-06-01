# server.py
"""
MCP服务器主模块，提供MySQL查询和表结构查询功能
"""

from typing import Dict, Any
from fastmcp import FastMCP

from typing import Dict, Any
from fastmcp import FastMCP
from sqlalchemy import text
from pydantic import Field

from .app_config import config
from .core import execute_query, get_table_info, get_db_connection, list_show_tables, get_database_info

# 创建MCP服务器实例
mcp = FastMCP(name=config.SERVER_NAME)

@mcp.tool()
def query_sql(sql: str) -> Dict[str, Any]:
    """执行SQL查询并返回结果集（仅支持SELECT语句）
    
    Args:
        sql: SQL查询语句（必须是SELECT语句）
        
    Returns:
        包含查询结果的字典，格式为：
        {
            "columns": [列名列表],
            "rows": [行数据列表],
            "row_count": 结果行数
        }
    """
    return execute_query(sql)

@mcp.tool()
def get_table_structure(table_name: str, schema: str = None) -> Dict[str, Any]:
    """获取指定表的结构信息
    
    Args:
        table_name: 表名
        schema: 数据库名，默认为当前数据库
        
    Returns:
        包含表结构信息的字典，格式为：
        {
            "columns": [列信息列表],
            "primary_keys": [主键列表],
            "foreign_keys": [外键信息列表],
            "indexes": [索引信息列表]
        }
    """
    return get_table_info(table_name, schema)

@mcp.tool()
def list_tables(schema: str = None) -> Dict[str, Any]:
    """列出数据库中的所有表
    
    Args:
        schema: 数据库名，默认为当前数据库
        
    Returns:
        包含表列表的字典，格式为：
        {
            "tables": [表信息列表],
            "count": 表数量
        }
    """
    return list_show_tables(schema)

@mcp.tool()
def get_db_info() -> Dict[str, Any]:
    """获取数据库基本信息
    
    Returns:
        包含数据库信息的字典，格式为：
        {
            "database_name": 当前数据库名,
            "version": 数据库版本,
            "schemas": [数据库列表],
            "connection": {
                "host": 主机名,
                "port": 端口,
                "database": 数据库名,
                "user": 用户名
            }
        }
    """
    return get_database_info()

@mcp.resource(
    uri="data://sql_describe",      # Explicit URI (required)
    name="sql语句编写规范",     # Custom name
    description="sql语句编写规范和说明（在编写sql语句前必看）", # Custom description
    mime_type="text/plain", # Explicit MIME type
    tags={"必看", "规范"} # Categorization tags
)
def sql_describe() -> str:
    """sql语句编写规范和说明（在编写sql语句前必看）"""
    ret = f'''
    SQL语句编写规范：
    
    1. 安全限制：只允许执行SELECT语句
    2. 不允许使用以下关键字：insert, update, delete, drop, alter, create, truncate, exec, execute
    3. 查询语句应尽量简洁，避免复杂的子查询和连接
    4. 查询结果行数应控制在合理范围内，避免返回过多数据
    5. 使用参数化查询，避免SQL注入风险
    6. 表名和列名应使用反引号(``)包裹，避免与MySQL关键字冲突
    7. 使用适当的WHERE条件限制查询范围
    8. 避免使用SELECT *，应明确指定需要的列
    '''
    return ret

@mcp.prompt(
    name="introduction",  # Custom prompt name
    description="当用户问好时",  # Custom description
    tags={"hello", "你好"}  # Optional categorization tags
)
def introduction_prompt(
    user_name: str = Field(description="用户姓名，非必填")
) -> str:
    """当用户问好时，需要生成的用户消息."""
    return f"用户名叫 '{user_name}' ，你需要友好的回复对方的问好，需要有Emoji表情，且要使用中文 ."

def main():
    """主函数，用于启动MCP服务器"""
    print("启动 MySQL MCP 服务器...")
    mcp.run()
    # To use a different transport, e.g., HTTP:
    # mcp.run(transport="streamable-http", host="127.0.0.1", port=9000)

if __name__ == "__main__":
    main()