# MySQL MCP Server

这是一个基于FastMCP的MySQL数据库查询服务器，提供了以下功能：

- 执行SQL查询（仅支持SELECT语句）
- 获取表结构信息
- 列出数据库中的所有表


## MCP 配置

本项目支持通过多种客户端配置 MCP 服务器，以便与各种 IDE 或工具集成。以下是一些常见客户端的配置示例：

### Windsurf / Cursor / Claude

对于基于 Windsurf 框架的客户端（如 Cursor 和 Claude），您可以在 `~/.codeium/windsurf/mcp_config.json` 文件中配置 MCP 服务器。以下是一个示例配置：

```json
{
  "mcpServers": {
    "jewei-mysql": {
      "disabled": false,
      "command": "uvx",
      "args": [
        "jewei-mysql-mcp-server"
      ],
      "env": {
        "DB_HOST": "your_db_host",
        "DB_USER": "your_db_user",
        "DB_PASSWORD": "your_db_password",
        "DB_NAME": "your_db_name",
        "DB_PORT": "your_db_port"
      }
    }
  }
}
```

请将 `your_db_host`, `your_db_user`, `your_db_password`, 和 `your_db_name` 替换为您的实际数据库连接信息。

### Cline

对于 Cline 客户端，您可以在其配置文件中添加类似的 MCP 服务器配置。具体的配置方式请参考 Cline 的官方文档。通常，您需要指定服务器的名称、命令、参数和环境变量。

```json
// Cline 配置文件示例 (具体格式请参考 Cline 文档)
{
  "mcpServers": {
    "jewei-mysql": {
      "command": "uvx",
      "args": [
        "jewei-mysql-mcp-server"
      ],
      "env": {
        "DB_HOST": "your_db_host",
        "DB_USER": "your_db_user",
        "DB_PASSWORD": "your_db_password",
        "DB_NAME": "your_db_name",
        "DB_PORT": "your_db_port"
      }
    }
  }
}
```

请将示例中的占位符替换为您的实际数据库连接信息，并根据 Cline 的具体配置格式进行调整。

## 安装

1. 克隆仓库
2. 安装依赖：`pip install -r requirements.txt`
3. 配置环境变量（参见下文）

## 配置

在项目根目录创建`.env`文件，包含以下环境变量：

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=your_database
```

## 运行

### 使用uvx安装并运行（推荐）

```bash
uvx --from jewei-mysql-mcp-server jewei-mysql-mcp-server
```

### 或者从源码运行

```bash
python -m jewei_mysql_mcp_server.server
```

## 功能

### 执行SQL查询

执行SQL查询并返回结果集（仅支持SELECT语句）。

### 获取表结构信息

获取指定表的结构信息，包括列信息、主键、外键和索引。

### 列出数据库中的所有表

列出指定数据库中的所有表。