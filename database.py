from flaskext.mysql import MySQL
import app

mysql = None


def init():
    global mysql
    mysql = MySQL()
    mysql.init_app(app.get_app())


class Value:
    def __init__(self, column, value):
        self.column = column
        self.value = value


def call_proc(proc: str, values):
    if not mysql:
        init()

    conn = mysql.connect()
    cursor = conn.cursor()

    cursor.callproc('sp_createUser', values)

    data = cursor.fetchall()
    conn.close()

    return data


def exec_sql(query: str, fetch_one: bool = False, fetch_all: bool = False, commit: bool = False):
    if not mysql:
        init()

    conn = mysql.connect()
    cursor = conn.cursor()

    cursor.execute(query)

    if commit:
        conn.commit()

    if fetch_one:
        return cursor.fetchone()
    if fetch_all:
        return cursor.fetchall()

    conn.close()


def get_one(table: str, columns: list = None, conditions: list = None):
    return exec_sql("SELECT %s FROM %s" % (','.join(col for col in columns) if columns else '*', table)
                    + " WHERE %s" % ' AND '.join("%s='%s'" % (condition.column, condition.value)
                                                 for condition in conditions) if conditions else '', fetch_one=True)


def get_all(table: str, columns: list = None, conditions: list = None):
    return exec_sql("SELECT %s FROM %s" % (','.join(col for col in columns) if columns else '*', table)
                    + " WHERE %s" % ' AND '.join("%s='%s'" % (condition.column, condition.value)
                                                 for condition in conditions) if conditions else '', fetch_all=True)


def insert_direct(table: str, values: list, overwrite=False):
    exec_sql("%s INTO %s VALUES (%s)" % ('REPLACE' if overwrite else 'INSERT', table,
                                         ','.join("'%s'" % value.value for value in values)), commit=True)


def insert_specific(table: str, values: list, overwrite=False):
    exec_sql("%s INTO %s (%s) VALUES (%s)" % ('REPLACE' if overwrite else 'INSERT', table,
                                              ','.join(value.column for value in values),
                                              ','.join('%s' % value.value for value in values)), commit=True)


def update(table: str, values: list, condition: Value = None):
    exec_sql("UPDATE %s SET %s" % (table, ','.join("%s='%s'" % (value.column, value.value) for value in values))
             + " WHERE %s=%s" % (condition.column, condition.value) if condition else '', commit=True)


def delete(table: str, condition: Value = None):
    exec_sql("DELETE FROM %s" % table
             + " WHERE %s='%s'" % (condition.column, condition.value) if condition else '', commit=True)
