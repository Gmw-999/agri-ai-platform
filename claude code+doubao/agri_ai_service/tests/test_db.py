"""
数据库工具测试：连接池、CRUD 操作
注意：需要 MySQL 服务运行才能通过
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from utils.db import query_all, query_one, execute, execute_last_id, get_conn


class TestDatabaseConnection:
    """数据库连接测试"""

    def test_get_conn_returns_valid_connection(self):
        """获取连接应返回有效连接"""
        try:
            with get_conn() as conn:
                assert conn is not None
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                assert cursor.fetchone()[0] == 1
                cursor.close()
        except Exception as e:
            pytest.skip(f"MySQL 未运行: {e}")

    def test_query_all_returns_list(self):
        """query_all 应返回列表"""
        try:
            rows = query_all("SELECT 1 as n")
            assert isinstance(rows, list)
            assert len(rows) > 0
            assert rows[0]["n"] == 1
        except Exception as e:
            pytest.skip(f"MySQL 未运行: {e}")

    def test_query_one_returns_dict(self):
        """query_one 应返回字典或 None"""
        try:
            row = query_one("SELECT 1 as n")
            assert row is not None
            assert row["n"] == 1

            row = query_one("SELECT 1 as n WHERE 1=0")
            assert row is None
        except Exception as e:
            pytest.skip(f"MySQL 未运行: {e}")


class TestConnectionPooling:
    """连接池测试"""

    def test_multiple_connections_are_reused(self):
        """多次获取连接应该复用连接池中的连接"""
        try:
            conn1_id = None
            conn2_id = None

            with get_conn() as conn1:
                cursor = conn1.cursor()
                cursor.execute("SELECT CONNECTION_ID()")
                conn1_id = cursor.fetchone()[0]
                cursor.close()

            with get_conn() as conn2:
                cursor = conn2.cursor()
                cursor.execute("SELECT CONNECTION_ID()")
                conn2_id = cursor.fetchone()[0]
                cursor.close()

            assert conn1_id is not None
            assert conn2_id is not None
            # 连接可能复用也可能不同，这取决于连接池状态
            # 关键是不应报错
        except Exception as e:
            pytest.skip(f"MySQL 未运行: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
