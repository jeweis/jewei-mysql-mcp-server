# core.py
"""
核心模块，包含数据库连接和核心功能
"""

import json
from typing import Dict, List, Optional, Union, Any
from sqlalchemy import create_engine, text, MetaData, Table, Column
from sqlalchemy.exc import SQLAlchemyError
import pymysql  # 确保 PyMySQL 驱动可用

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
            
            # 创建引擎时设置连接池选项，但不立即测试连接
            engine = create_engine(
                config.CONNECTION_STRING,
                pool_pre_ping=True,  # 检查连接是否有效
                pool_recycle=3600,   # 每小时回收连接
                connect_args={
                    'connect_timeout': 30     # 连接超时时间（秒）
                }
            )
            
            print("数据库引擎创建成功（延迟连接）")
        except Exception as e:
            error_msg = f"数据库引擎创建失败: {str(e)}"
            print(error_msg)
            raise Exception(error_msg)
    
    return engine

def test_db_connection():
    """测试数据库连接是否正常"""
    try:
        engine = get_db_connection()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            print(f"数据库连接测试成功: {result}")
            return True
    except Exception as e:
        print(f"数据库连接测试失败: {str(e)}")
        return False

def execute_query(sql: str) -> Dict[str, Any]:
    """执行SQL查询并返回结果集
    
    Args:
        sql: SQL查询语句
        
    Returns:
        包含查询结果的字典，格式为：
        {
            "columns": [列名列表],
            "rows": [行数据列表],
            "row_count": 结果行数
        }
    """
    # 安全检查：只允许SELECT语句
    sql_lower = sql.strip().lower()
    if not sql_lower.startswith('select'):
        raise ValueError("只允许执行SELECT语句")
    
    # 检查是否包含危险关键字
    dangerous_keywords = ['insert', 'update', 'delete', 'drop', 'alter', 'create', 'truncate', 'exec', 'execute']
    for keyword in dangerous_keywords:
        if keyword in sql_lower:
            raise ValueError(f"不允许使用关键字: {keyword}")
    
    try:
        engine = get_db_connection()
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            
            # 获取列名
            columns = list(result.keys())
            
            # 获取所有行数据
            rows = []
            for row in result:
                # 将Row对象转换为列表，处理各种数据类型
                row_data = []
                for value in row:
                    if value is None:
                        row_data.append(None)
                    elif isinstance(value, (int, float, str, bool)):
                        row_data.append(value)
                    else:
                        # 对于其他类型（如datetime、decimal等），转换为字符串
                        row_data.append(str(value))
                rows.append(row_data)
            
            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows)
            }
            
    except SQLAlchemyError as e:
        error_msg = f"SQL执行错误: {str(e)}"
        print(error_msg)
        # 如果是连接错误，提供更友好的错误信息
        if "Can't connect" in str(e) or "Connection refused" in str(e):
            raise Exception("数据库连接失败，请检查数据库服务是否运行以及连接配置是否正确")
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"查询执行失败: {str(e)}"
        print(error_msg)
        raise Exception(error_msg)

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
        
        # 查询列信息 - 使用兼容性更好的字段
        columns_sql = f"""
        SELECT 
            COLUMN_NAME AS column_name,
            DATA_TYPE AS data_type,
            CHARACTER_MAXIMUM_LENGTH AS max_length,
            CASE 
                WHEN DATA_TYPE IN ('decimal', 'numeric', 'float', 'double') 
                THEN CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(COLUMN_TYPE, '(', -1), ',', 1) AS UNSIGNED)
                ELSE 0 
            END AS precision,
            CASE 
                WHEN DATA_TYPE IN ('decimal', 'numeric') AND COLUMN_TYPE LIKE '%,%' 
                THEN CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(COLUMN_TYPE, ',', -1), ')', 1) AS UNSIGNED)
                ELSE 0 
            END AS scale,
            IS_NULLABLE AS is_nullable,
            COALESCE(COLUMN_COMMENT, '') AS description
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
    except SQLAlchemyError as e:
        error_msg = f"获取表结构失败: {str(e)}"
        print(error_msg)
        # 如果是连接错误，提供更友好的错误信息
        if "Can't connect" in str(e) or "Connection refused" in str(e):
            raise Exception("数据库连接失败，请检查数据库服务是否运行以及连接配置是否正确")
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"获取表结构失败: {str(e)}"
        print(error_msg)
        raise Exception(error_msg)

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
    except SQLAlchemyError as e:
        error_msg = f"列出表失败: {str(e)}"
        print(f"{error_msg}, 数据库: {schema if schema else config.DB_NAME}")
        # 如果是连接错误，提供更友好的错误信息
        if "Can't connect" in str(e) or "Connection refused" in str(e):
            raise Exception("数据库连接失败，请检查数据库服务是否运行以及连接配置是否正确")
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"列出表失败: {str(e)}"
        print(f"{error_msg}, 数据库: {schema if schema else config.DB_NAME}")
        raise Exception(error_msg)

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
    except SQLAlchemyError as e:
        error_msg = f"获取数据库信息失败: {str(e)}"
        print(error_msg)
        # 如果是连接错误，提供更友好的错误信息
        if "Can't connect" in str(e) or "Connection refused" in str(e):
            raise Exception("数据库连接失败，请检查数据库服务是否运行以及连接配置是否正确")
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"获取数据库信息失败: {str(e)}"
        print(error_msg)
        raise Exception(error_msg)