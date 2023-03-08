# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from textwrap import dedent
from typing import List, Optional, Tuple

from util.jdbc_input_manager_interface import (
    JDBCInputManagerInterface,
    SPARK_PARTITION_COLUMN,
    SPARK_NUM_PARTITIONS,
    SPARK_LOWER_BOUND,
    SPARK_UPPER_BOUND,
)


class OracleInputManager(JDBCInputManagerInterface):

    # Private methods

    def _build_table_list(self, schema_filter: Optional[str] = None) -> Tuple[str, List[str]]:
        """
        Return a tuple containing schema and list of table names based on an optional schema filter.
        If schema_filter is not provided then the connected user is used for the schema.
        """
        with self._alchemy_db.connect() as conn:
            schema = self._normalise_schema_filter(schema_filter, conn)
            not_like_filter = "table_name NOT LIKE 'DR$SUP_TEXT_IDX%'"
            if schema_filter:
                sql = f'SELECT table_name FROM all_tables WHERE owner = :own AND {not_like_filter}'
                rows = conn.execute(sql, own=schema).fetchall()
            else:
                sql = f'SELECT table_name FROM user_tables WHERE {not_like_filter}'
                rows = conn.execute(sql).fetchall()
            return schema, [_[0] for _ in rows]

    def _define_read_partitioning(self, table: str, row_count_threshold: int, sa_connection) -> Optional[list]:
        """Return a dictionary defining how to partition the Spark SQL extraction."""
        # TODO In the future we may want to support checking DBA_SEGMENTS
        row_count = self._get_table_count(table, sa_connection=sa_connection)
        if row_count > int(row_count_threshold):
            # The table has enough rows to merit partitioning Spark SQL read.
            # TODO Prioritise partition keys over primary keys in the future.
            # TODO Add support for UKs alongside PKs.
            if self.get_primary_keys().get(table):
                column = self.get_primary_keys().get(table)
                column_datatype = self._get_column_data_type(self._schema, table, column)
                if column_datatype == 'NUMBER':
                    lowerbound = sa_connection.execute(self._get_min_sql(table, column)).fetchone()
                    upperbound = sa_connection.execute(self._get_max_sql(table, column)).fetchone()
                    if lowerbound and upperbound:
                        lowerbound = lowerbound[0]
                        upperbound = upperbound[0]
                        num_partitions = self._read_partitioning_num_partitions(lowerbound, upperbound, row_count_threshold)
                        return {
                             SPARK_PARTITION_COLUMN: column,
                             SPARK_NUM_PARTITIONS: num_partitions,
                             SPARK_LOWER_BOUND: lowerbound,
                             SPARK_UPPER_BOUND: upperbound,
                        }
        return None

    def _enclose_identifier(self, identifier, ch: Optional[str] = None):
        """Enclose an identifier in the standard way for the SQL engine."""
        ch = ch or '"'
        return f'{ch}{identifier}{ch}'

    def _get_column_data_type(self, schema: str, table: str, column: str, sa_connection=None) -> str:
        sql = dedent("""
        SELECT data_type
        FROM   all_tab_columns
        WHERE  owner = :own
        AND    table_name = :tab
        AND    column_name = :col
        """)
        if sa_connection:
            row = sa_connection.execute(sql, own=schema, tab=table, col=column).fetchone()
        else:
            with self._alchemy_db.connect() as conn:
                row = conn.execute(sql, own=schema, tab=table, col=column).fetchone()
        if row:
            # TODO we need to strip out any scale from TIMESTAMP types.
            return row[0]
        else:
            return row

    def _get_primary_keys(self) -> dict:
        """
        Return a dict of primary key information.
        The dict is keyed on the table name and maps to the column name.
        """
        pk_dict = {_: None for _ in self._table_list}
        sql = dedent("""
        SELECT cols.column_name
        FROM   all_constraints cons
        ,      all_cons_columns cols
        WHERE  cons.owner = :own
        AND    cons.table_name = :tab
        AND    cons.constraint_type = 'P'
        AND    cons.status = 'ENABLED'
        AND    cols.position = 1
        AND    cols.constraint_name = cons.constraint_name
        AND    cols.owner = cons.owner
        AND    cols.table_name = cons.table_name
        """)
        with self._alchemy_db.connect() as conn:
            for table in self._table_list:
                row = conn.execute(sql, own=self._schema, tab=table).fetchone()
                if row:
                    pk_dict[table] = row[0]
            return pk_dict

    def _normalise_schema_filter(self, schema_filter: str, sa_connection) -> str:
        """Return schema_filter normalised to the correct case, or sets to connected user if blank."""
        if schema_filter:
            # Assuming there will not be multiple schemas of the same name in different case.
            sql = 'SELECT username FROM all_users WHERE UPPER(username) = UPPER(:b1) ORDER BY username'
            row = sa_connection.execute(sql, b1=schema_filter).fetchone()
        else:
            sql = 'SELECT USER FROM dual'
            row = sa_connection.execute(sql).fetchone()
        return row[0] if row else row

    def _qualified_name(self, schema: str, table: str, enclosed=False) -> str:
        if enclosed:
            return self._enclose_identifier(schema, '"') + "." + self._enclose_identifier(table, '"')
        else:
            return schema + "." + table

    # Public methods