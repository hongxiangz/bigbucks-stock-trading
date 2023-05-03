import pymysql
import sys


db = pymysql.connect(host='localhost',
                    user='root',
                    password='pudong0414',
                    database='stock')

class Entity:

    def __init__(self) -> None:
        self.pk = None

    def exe_sql(self, sql):
        # print(f'exe_sql: {sql}')
        cursor = db.cursor()
        cursor.execute(sql)
        db.commit()
        cursor.close()

    def save(self) -> None:
        def escape(raw_value):
            if (isinstance(raw_value, str)):
                return raw_value.replace('\'', '\\\'')

            return raw_value

        if self.pk is None:
            field_list = []
            value_list = []
            for index, (field, value) in enumerate(self.__dict__.items()):
                if field == 'pk':
                    continue
                
                field_list.append(f'`{field}`')
                value_list.append(f'\'{escape(value)}\'')
            
            field_list_str = ','.join(field_list)
            value_list_str = ','.join(value_list)
            value_list_str = value_list_str.replace("'nan'", "NULL")
            sql = f'INSERT INTO {self.table}({field_list_str}) VALUES ({value_list_str});'

        else:
            sql = f"UPDATE {self.table} SET "
            for index, (field, value) in enumerate(self.__dict__.items()):
                sql += f'`{field}` = \'{escape(value)}\''
                if index != len(self.__dict__) - 1:
                    sql += ','

                sql += ' '
            
            pk = self.__dict__['pk']
            sql += f'WHERE pk = {pk};'

        self.exe_sql(sql)


    def delete(self) -> None:
        sql = f'DELETE FROM {self.table} WHERE id = {self.id}'
        self.exe_sql(sql)

    @staticmethod   
    def filter(Cls, where_cause=None, order_cause=None, full_sql=None):
        if full_sql is not None:
            sql = full_sql
        elif where_cause is None:
            sql = f'SELECT * from {Cls.table}'
        else:
            sql = f'SELECT * from {Cls.table} WHERE {where_cause}'

        if order_cause is not None:
            sql += " " + order_cause

        # print(f"filter: {sql}")
        cursor = db.cursor()
        cursor.execute(sql)
        objs = []
        for row in cursor.fetchall():
            obj = Cls()
            obj.from_row(row)
            objs.append(obj)

        cursor.close()
        return objs


class User(Entity):
    table = 'Users'

    def from_row(self, row) -> None:
        self.pk = row[0]
        self.username = row[1]
        self.password = row[2]
        self.balance = row[3]
        self.current_date = row[4]
        self.role = row[5]

    def __str__(self) -> str:
        return f'{self.pk}-{self.username}-{self.password}'


class Stock(Entity):
    table = 'Stocks'

    def from_row(self, row) -> None:
        self.pk = row[0]
        self.name = row[1]
        self.price = row[2]
        self.date = row[3]

    def __str__(self) -> str:
        return f'{self.pk}-{self.name}-{self.date}'


class Transaction(Entity):
    table = 'Transactions'

    def from_row(self, row) -> None:
        self.pk = row[0]
        self.username = row[1]
        self.stock = row[2]
        self.date = row[3]
        self.type = row[4]
        self.shares = row[5]
        self.price = row[6]
        self.cost = row[7]
        self.balance = row[8]

    def __str__(self) -> str:
        return f'{self.pk}-{self.stock}-{self.date}-{self.type}'


class Holding(Entity):
    table = 'Holdings'

    def from_row(self, row) -> None:
        self.pk = row[0]
        self.username = row[1]
        self.stock = row[2]
        self.shares = row[3]
        self.cost = row[4]
        self.date = row[5]
        self.price = row[6]

    def __str__(self) -> str:
        return f'{self.pk}-{self.username}-{self.stock}-{self.shares}'
