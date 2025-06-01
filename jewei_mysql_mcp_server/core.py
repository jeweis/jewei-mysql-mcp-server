# core.py
"""
核心模块，包含数据库连接和核心功能
"""

import json
from typing import Dict, List, Optional, Union, Any
from sqlalchemy import create_engine, text, MetaData, Table, Column
from sqlalchemy.exc import SQLAlchemyError

from .app_config import config

# 数据库连接管理
engine = None

def get_db_connection():
    """获取数据库连接，如果不存在则创建新连接"""
    global engine
    if engine is None:
        try:
            print("正在创建数据库连接...")
            print(f"连接到: {config.DB_HOST}:{config.DB_PORT}, 数据库: {config.DB_NAME}, 用户: {config.DB_USER}")
            print(f"连接字符串: {config.CONNECTION_STRING}")
            
            # 创建引擎时设置连接池选项
            engine = create_engine(
                config.CONNECTION_STRING,
                pool_pre_ping=True,  # 检查连接是否有效
                pool_recycle=3600,   # 每小时回收连接
                connect_args={
                    'connect_timeout': 30     # 连接超时时间（秒）
                }
            )
            
            # 测试连接
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()
                print(f"测试连接结果: {result}")
                
            print("数据库连接创建成功")
        except SQLAlchemyError as e:
            error_msg = f"数据库连接失败: {str(e)}"
            print(error_msg)
            
            # 尝试获取更详细的错误信息
            if hasattr(e, 'orig') and e.orig:
                print(f"原始错误: {e.orig}")
                if hasattr(e.orig, 'args') and e.orig.args:
                    print(f"错误参数: {e.orig.args}")
            
            raise Exception(error_msg)
    return engine

def execute_query(sql: str) -> Dict[str, Any]:
    """执行SQL查询并返回结果集
    
    Args:
        sql: SQL查询语句（必须是SELECT语句）
        
    Returns:
        包含查询结果的字典
    """
    try:
        print(f"执行SQL查询: {sql[:100]}{'...' if len(sql) > 100 else ''}")
        # 安全检查：确保只执行SELECT语句
        sql_lower = sql.lower().strip()
        if not sql_lower.startswith("select"):
            error_msg = "安全限制：只允许执行SELECT语句"
            print(f"{error_msg}, SQL: {sql}")
            return {
                "error": error_msg,
                "sql": sql
            }
            
        # 检查是否包含危险操作
        dangerous_keywords = ["insert", "update", "delete", "drop", "alter", "create", "truncate", "exec", "execute"]
        for keyword in dangerous_keywords:
            if f" {keyword} " in f" {sql_lower} ":
                error_msg = f"安全限制：查询中包含禁止的关键字 '{keyword}'"
                print(f"{error_msg}, SQL: {sql}")
                return {
                    "error": error_msg,
                    "sql": sql
                }
        
        engine = get_db_connection()
        
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            # 获取列名
            columns = list(result.keys())
            
            # 转换结果为字典列表
            result_rows = []
            for row in result:
                try:
                    # 尝试使用字典推导式创建字典
                    row_dict = {col: row[i] for i, col in enumerate(columns)}
                    result_rows.append(row_dict)
                except Exception as row_err:
                    print(f"处理行数据时出错: {row_err}")
                    # 如果出错，尝试使用其他方式
                    try:
                        # 尝试直接将行转换为字典
                        row_dict = {}
                        for i, col in enumerate(columns):
                            try:
                                row_dict[col] = row[i]
                            except:
                                row_dict[col] = None
                        result_rows.append(row_dict)
                    except Exception as e:
                        print(f"处理行数据的备选方法也失败: {e}")
                        # 最后的备选方案，只添加原始值
                        result_rows.append({"value": str(row)})
        
        print(f"查询成功，返回 {len(result_rows)} 条记录")
        return {
            "columns": columns,
            "rows": result_rows,
            "row_count": len(result_rows)
        }
    except Exception as e:
        error_msg = f"查询执行失败: {str(e)}"
        print(f"{error_msg}, SQL: {sql}")
        return {
            "error": str(e),
            "sql": sql
        }

def get_table_info(table_name: str, schema: str = None) -> Dict[str, Any]:
    """获取指定表的结构信息
    
    Args:
        table_name: 表名
        schema: 数据库名，默认为当前数据库
        
    Returns:
        包含表结构信息的字典
    """
    try:
        print(f"获取表结构信息: {schema}.{table_name}" if schema else f"获取表结构信息: {table_name}")
        engine = get_db_connection()
        
        # 使用当前数据库，如果未指定schema
        current_db = schema if schema else config.DB_NAME
        
        # 查询列信息
        columns_sql = f"""
        SELECT 
            COLUMN_NAME AS column_name,
            DATA_TYPE AS data_type,
            CHARACTER_MAXIMUM_LENGTH AS max_length,
            NUMERIC_PRECISION AS precision,
            NUMERIC_SCALE AS scale,
            IS_NULLABLE AS is_nullable,
            COLUMN_COMMENT AS description
        FROM 
            INFORMATION_SCHEMA.COLUMNS
        WHERE 
            TABLE_NAME = '{table_name}' AND TABLE_SCHEMA = '{current_db}'
        ORDER BY 
            ORDINAL_POSITION
        """

        # 查询主键信息
        primary_keys_sql = f"""
        SELECT 
            COLUMN_NAME AS column_name
        FROM 
            INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE 
            TABLE_NAME = '{table_name}' 
            AND TABLE_SCHEMA = '{current_db}'
            AND CONSTRAINT_NAME = 'PRIMARY'
        ORDER BY 
            ORDINAL_POSITION
        """

        # 查询外键信息
        foreign_keys_sql = f"""
        SELECT 
            CONSTRAINT_NAME AS fk_name,
            COLUMN_NAME AS column_name,
            REFERENCED_TABLE_NAME AS referenced_table,
            REFERENCED_COLUMN_NAME AS referenced_column
        FROM 
            INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE 
            TABLE_NAME = '{table_name}' 
            AND TABLE_SCHEMA = '{current_db}'
            AND REFERENCED_TABLE_NAME IS NOT NULL
        ORDER BY 
            CONSTRAINT_NAME, ORDINAL_POSITION
        """

        # 查询索引信息
        indexes_sql = f"""
        SELECT
            INDEX_NAME AS index_name,
            IF(NON_UNIQUE = 0, 'UNIQUE', 'NON_UNIQUE') AS index_type,
            NON_UNIQUE = 0 AS is_unique,
            INDEX_NAME = 'PRIMARY' AS is_primary_key,
            0 AS is_unique_constraint,
            GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columns
        FROM
            INFORMATION_SCHEMA.STATISTICS
        WHERE
            TABLE_NAME = '{table_name}' AND TABLE_SCHEMA = '{current_db}'
        GROUP BY
            INDEX_NAME, NON_UNIQUE
        ORDER BY
            INDEX_NAME
        """

        # Execute and process columns_sql
        columns = []
        with engine.connect() as conn:
            columns_result = conn.execute(text(columns_sql))
            # 处理列信息
            for row in columns_result:
                column = {
                    "name": row.column_name,
                    "type": row.data_type,
                    "max_length": row.max_length,
                    "precision": row.precision,
                    "scale": row.scale,
                    "is_nullable": row.is_nullable == "YES",
                    "description": row.description
                }
                columns.append(column)

        # Execute and process primary_keys_sql
        primary_keys = []
        with engine.connect() as conn:
            primary_keys_result = conn.execute(text(primary_keys_sql))
            # 处理主键信息
            primary_keys = [row.column_name for row in primary_keys_result]

        # Execute and process foreign_keys_sql
        foreign_keys = []
        with engine.connect() as conn:
            foreign_keys_result = conn.execute(text(foreign_keys_sql))
            # 处理外键信息
            for row in foreign_keys_result:
                fk = {
                    "name": row.fk_name,
                    "column": row.column_name,
                    "referenced_table": row.referenced_table,
                    "referenced_column": row.referenced_column
                }
                foreign_keys.append(fk)

        # Execute and process indexes_sql
        indexes = []
        with engine.connect() as conn:
            indexes_result = conn.execute(text(indexes_sql))
            # 处理索引信息
            for row in indexes_result:
                index = {
                    "name": row.index_name,
                    "type": row.index_type,
                    "is_unique": bool(row.is_unique),
                    "is_primary_key": bool(row.is_primary_key),
                    "is_unique_constraint": bool(row.is_unique_constraint),
                    "columns": row.columns.split(",") if row.columns else []
                }
                indexes.append(index)

        return {
            "columns": columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "indexes": indexes
        }
    except Exception as e:
        error_msg = f"获取表结构失败: {str(e)}"
        print(error_msg)
        return {
            "error": str(e)
        }

def list_show_tables(schema: str = None) -> Dict[str, Any]:
    """列出数据库中的所有表
    
    Args:
        schema: 数据库名，默认为当前数据库
        
    Returns:
        包含表列表的字典
    """
    try:
        # 使用当前数据库，如果未指定schema
        current_db = schema if schema else config.DB_NAME
        
        print(f"列出数据库 '{current_db}' 中的所有表")
        engine = get_db_connection()
        
        # MySQL查询表信息
        sql = f"""
        SELECT
            TABLE_NAME AS table_name,
            TABLE_COMMENT AS description,
            TABLE_SCHEMA AS schema_name
        FROM
            INFORMATION_SCHEMA.TABLES
        WHERE
            TABLE_SCHEMA = '{current_db}' AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY
            TABLE_NAME
        """
        
        # 如果上面的查询仍然不起作用，尝试使用更简单的查询
        simple_sql = f"""
        SHOW TABLES FROM `{current_db}`
        """
        
        try:
            with engine.connect() as conn:
                print("尝试执行带有表描述的查询...")
                result = conn.execute(text(sql))
                col_names = list(result.keys())
                tables = []
                for row in result:
                    try:
                        # 安全地将行转换为字典
                        row_dict = {}
                        for i, col in enumerate(col_names):
                            try:
                                # 尝试将每个值转换为字符串，避免类型问题
                                value = row[i]
                                if value is not None:
                                    row_dict[col] = str(value)
                                else:
                                    row_dict[col] = ""
                            except Exception as val_err:
                                print(f"处理列 {col} 的值时出错: {val_err}")
                                row_dict[col] = ""
                        tables.append(row_dict)
                    except Exception as e:
                        print(f"处理表信息时出错: {e}")
                        tables.append({"table_name": str(row[0]) if row and len(row) > 0 else "unknown"})
        except Exception as complex_query_error:
            print(f"复杂查询失败，尝试简单查询: {complex_query_error}")
            # 如果复杂查询失败，尝试简单查询
            with engine.connect() as conn:
                print("执行简化的表查询...")
                result = conn.execute(text(simple_sql))
                tables = []
                for row in result:
                    try:
                        table_name = row[0]
                        tables.append({
                            "table_name": table_name,
                            "description": "",
                            "schema_name": current_db
                        })
                    except Exception as e:
                        print(f"处理简化表信息时出错: {e}")
                        tables.append({"table_name": "unknown"})
        
        print(f"成功获取 {len(tables)} 个表")
        return {
            "tables": tables,
            "count": len(tables)
        }
    except Exception as e:
        error_msg = f"列出表失败: {str(e)}"
        print(f"{error_msg}, 数据库: {schema if schema else config.DB_NAME}")
        return {
            "error": str(e),
            "schema": schema if schema else config.DB_NAME
        }

def get_database_info() -> Dict[str, Any]:
    """获取数据库基本信息
    
    Returns:
        包含数据库信息的字典
    """
    try:
        print("获取数据库基本信息")
        engine = get_db_connection()
        
        # 获取数据库版本信息
        version_sql = "SELECT VERSION() AS version"
        # 获取数据库名称
        db_name_sql = "SELECT DATABASE() AS database_name"
        # 获取数据库列表
        schema_sql = "SHOW DATABASES"
        
        with engine.connect() as conn:
            # 获取版本信息
            version_result = conn.execute(text(version_sql)).fetchone()
            version_info = version_result[0] if version_result else None
            
            # 获取数据库名称
            db_name_result = conn.execute(text(db_name_sql)).fetchone()
            database_name = db_name_result[0] if db_name_result else None
            
            # 获取数据库列表
            schema_result = conn.execute(text(schema_sql))
            schemas = [row[0] for row in schema_result]
        
        print(f"成功获取数据库信息: {database_name}")
        return {
            "database_name": database_name,
            "version": version_info,
            "schemas": schemas,

            "connection": {
                "host": config.DB_HOST,
                "port": config.DB_PORT,
                "database": config.DB_NAME,
                "user": config.DB_USER
            }
        }
    except Exception as e:
        error_msg = f"获取数据库信息失败: {str(e)}"
        print(error_msg)
        return {
            "error": str(e)
        }