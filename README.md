# MySQL MCP Server

这是一个基于FastMCP的MySQL数据库查询服务器，提供了以下功能：

- 执行SQL查询（仅支持SELECT语句）
- 获取表结构信息
- 列出数据库中的所有表

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

```
python run_server.py
```

## 功能

### 执行SQL查询

执行SQL查询并返回结果集（仅支持SELECT语句）。

### 获取表结构信息

获取指定表的结构信息，包括列信息、主键、外键和索引。

### 列出数据库中的所有表

列出指定数据库中的所有表。