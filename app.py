# -*- coding: utf-8 -*-
# @Time    : 2025/4/16 21:38
# @Author  : Junzhe Yi
# @File    : app.py
# @Software: PyCharm
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import pymysql
from pymysql import Error
from pymysql.cursors import DictCursor
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

# 数据库连接配置
db_config = {
    'host': '121.43.96.214',
    'port': 3306,
    'user': 'final',
    'password': 'final',
    'database': 'final',
    'cursorclass': DictCursor,
    'charset': 'utf8mb4',
}


def get_db_connection():
    """创建数据库连接"""
    try:
        connection = pymysql.connect(**db_config)
        return connection
    except Error as e:
        print(f"数据库连接错误: {e}")
        return None


def db_required(f):
    """确保数据库连接可用的装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        connection = get_db_connection()
        if connection is None:
            flash("无法连接到数据库", "error")
            return redirect(url_for('index'))
        try:
            kwargs['connection'] = connection
            return f(*args, **kwargs)
        finally:
            connection.close()

    return decorated_function


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/table/<table_name>')
@db_required
def show_table(table_name, connection):
    """显示表数据"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()

            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            columns = [column['Field'] for column in cursor.fetchall()]

            cursor.execute(f"SHOW KEYS FROM {table_name} WHERE Key_name = 'PRIMARY'")
            pk_column = cursor.fetchone()['Column_name'] if cursor.rowcount > 0 else None

            return render_template('table.html', table_name=table_name,
                                   columns=columns, rows=rows, pk_column=pk_column)
    except Error as e:
        flash(f"查询表数据时出错: {e}", "error")
        return redirect(url_for('index'))


@app.route('/search/<table_name>')
@db_required
def search_table(table_name, connection):
    """搜索表数据"""
    search_text = request.args.get('q', '')
    if not search_text:
        return redirect(url_for('show_table', table_name=table_name))

    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            columns = [column['Field'] for column in cursor.fetchall()]

            # 构建搜索条件
            search_conditions = []
            search_values = []
            for col in columns:
                search_conditions.append(f"{col} LIKE %s")
                search_values.append(f"%{search_text}%")

            where_clause = " OR ".join(search_conditions)
            sql = f"SELECT * FROM {table_name} WHERE {where_clause}"

            cursor.execute(sql, search_values)
            rows = cursor.fetchall()

            return render_template('table.html', table_name=table_name,
                                   columns=columns, rows=rows, search_text=search_text)
    except Error as e:
        flash(f"搜索表数据时出错: {e}", "error")
        return redirect(url_for('show_table', table_name=table_name))


@app.route('/add/<table_name>', methods=['GET', 'POST'])
@db_required
def add_record(table_name, connection):
    """添加记录"""
    if request.method == 'GET':
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                columns = cursor.fetchall()
                return render_template('add_record.html', table_name=table_name, columns=columns)
        except Error as e:
            flash(f"获取表结构时出错: {e}", "error")
            return redirect(url_for('show_table', table_name=table_name))

    elif request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                # 开始事务
                connection.begin()

                # 从表单获取数据
                columns = []
                values = []
                for key, value in request.form.items():
                    if key != 'csrf_token':  # 跳过CSRF令牌
                        columns.append(key)
                        values.append(value if value else None)

                # 构建SQL
                placeholders = ", ".join(["%s"] * len(values))
                columns_str = ", ".join(columns)
                sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"

                # 执行插入
                cursor.execute(sql, values)

                # 提交事务
                connection.commit()
                flash("记录添加成功", "success")
                return redirect(url_for('show_table', table_name=table_name))

        except Error as e:
            # 回滚事务
            connection.rollback()
            flash(f"添加记录时出错: {e}", "error")
            return redirect(url_for('add_record', table_name=table_name))


@app.route('/edit/<table_name>/<pk_value>', methods=['GET', 'POST'])
@db_required
def edit_record(table_name, pk_value, connection):
    """编辑记录"""
    try:
        with connection.cursor() as cursor:
            # 获取主键列名
            cursor.execute(f"SHOW KEYS FROM {table_name} WHERE Key_name = 'PRIMARY'")
            pk_column = cursor.fetchone()['Column_name']

            if request.method == 'GET':
                # 获取记录数据
                cursor.execute(f"SELECT * FROM {table_name} WHERE {pk_column} = %s", (pk_value,))
                record = cursor.fetchone()

                if not record:
                    flash("未找到记录", "error")
                    return redirect(url_for('show_table', table_name=table_name))

                # 获取列信息
                cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                columns = cursor.fetchall()

                return render_template('edit_record.html', table_name=table_name,
                                       columns=columns, record=record, pk_column=pk_column)

            elif request.method == 'POST':
                # 开始事务
                connection.begin()

                # 使用行锁
                cursor.execute(f"SELECT * FROM {table_name} WHERE {pk_column} = %s FOR UPDATE", (pk_value,))

                # 添加一个人为延迟，模拟长时间运行的事务，便于测试行锁
                if request.args.get('simulate_lock') == '1':
                    import time
                    flash("正在验证并发操作，锁定数据20秒...", "info")
                    time.sleep(20)  # 锁定20秒

                # 从表单获取数据
                set_clause = []
                values = []
                for key, value in request.form.items():
                    if key != 'csrf_token' and key != pk_column:  # 跳过CSRF令牌和主键
                        set_clause.append(f"{key} = %s")
                        values.append(value if value else None)

                # 添加主键值
                values.append(pk_value)

                # 构建SQL
                sql = f"UPDATE {table_name} SET {', '.join(set_clause)} WHERE {pk_column} = %s"

                # 执行更新
                cursor.execute(sql, values)

                # 提交事务
                connection.commit()
                flash("记录更新成功", "success")
                return redirect(url_for('show_table', table_name=table_name))

    except Error as e:
        # 回滚事务
        if connection.open:
            connection.rollback()
        flash(f"编辑记录时出错: {e}", "error")
        return redirect(url_for('show_table', table_name=table_name))


@app.route('/delete/<table_name>/<pk_value>', methods=['POST'])
@db_required
def delete_record(table_name, pk_value, connection):
    """删除记录"""
    try:
        with connection.cursor() as cursor:
            # 开始事务
            connection.begin()

            # 获取主键列名
            cursor.execute(f"SHOW KEYS FROM {table_name} WHERE Key_name = 'PRIMARY'")
            pk_column = cursor.fetchone()['Column_name']

            # 使用行锁
            cursor.execute(f"SELECT * FROM {table_name} WHERE {pk_column} = %s FOR UPDATE", (pk_value,))

            # 删除记录
            sql = f"DELETE FROM {table_name} WHERE {pk_column} = %s"
            cursor.execute(sql, (pk_value,))

            # 提交事务
            connection.commit()
            flash("记录删除成功", "success")
    except Error as e:
        # 回滚事务
        connection.rollback()
        flash(f"删除记录时出错: {e}", "error")

    return redirect(url_for('show_table', table_name=table_name))


# 添加计算功能的路由
@app.route('/calculate/purchase_total', methods=['GET', 'POST'])
@db_required
def calculate_purchase_total(connection):
    """计算采购总额"""
    if request.method == 'GET':
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT purchase_id FROM PurchaseRecords")
                purchase_ids = [row['purchase_id'] for row in cursor.fetchall()]
                return render_template('calculate_purchase_total.html', purchase_ids=purchase_ids)
        except Error as e:
            flash(f"获取采购记录时出错: {e}", "error")
            return redirect(url_for('index'))

    elif request.method == 'POST':
        purchase_id = request.form.get('purchase_id')
        if not purchase_id:
            flash("请选择采购记录ID", "warning")
            return redirect(url_for('calculate_purchase_total'))

        try:
            with connection.cursor() as cursor:
                # 调用存储过程
                cursor.callproc("CalculatePurchaseTotal", (purchase_id, 0))

                # 获取结果
                cursor.execute("SELECT @_CalculatePurchaseTotal_1")
                total = cursor.fetchone()['@_CalculatePurchaseTotal_1']

                return render_template('calculate_purchase_total.html',
                                       purchase_id=purchase_id, total=total)
        except Error as e:
            flash(f"计算采购总额时出错: {e}", "error")
            return redirect(url_for('calculate_purchase_total'))


@app.route('/calculate/daily_sales')
@db_required
def calculate_daily_sales(connection):
    """计算每日销售总额"""
    try:
        with connection.cursor() as cursor:
            # 调用存储过程
            cursor.callproc("CalculateDailySalesTotals")

            # 获取所有结果集
            results = []
            while True:
                try:
                    # 获取当前结果集
                    current_results = cursor.fetchall()
                    if current_results:
                        results.append(current_results)

                    # 检查是否有更多结果集
                    if not cursor.nextset():
                        break
                except pymysql.err.InterfaceError:
                    # 没有更多结果集
                    break

            # 查找包含销售数据的结果集
            sales_data = None
            for result_set in results:
                if result_set and 'sale_date' in result_set[0] and 'total_sales' in result_set[0]:
                    sales_data = result_set
                    break

            if not sales_data:
                flash("没有找到销售记录", "info")
                return redirect(url_for('index'))

            return render_template('daily_sales.html', sales_data=sales_data)

    except Error as e:
        flash(f"计算每日销售总额时出错: {e}", "error")
        return redirect(url_for('index'))


@app.route('/calculate/monthly_sales', methods=['GET', 'POST'])
@db_required
def calculate_monthly_sales(connection):
    """计算月度商品销售额"""
    if request.method == 'GET':
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT good_id, good_name FROM Goods")
                goods = cursor.fetchall()
                return render_template('monthly_sales.html', goods=goods)
        except Error as e:
            flash(f"获取商品列表时出错: {e}", "error")
            return redirect(url_for('index'))

    elif request.method == 'POST':
        good_id = request.form.get('good_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        if not good_id or not start_date or not end_date:
            flash("请填写所有字段", "warning")
            return redirect(url_for('calculate_monthly_sales'))

        try:
            with connection.cursor() as cursor:
                # 调用函数
                cursor.execute("SELECT CalculateMonthlySalesTotal_good(%s, %s, %s) AS total",
                               (good_id, start_date, end_date))
                total = cursor.fetchone()['total']

                # 获取商品信息用于显示
                cursor.execute("SELECT good_name FROM Goods WHERE good_id = %s", (good_id,))
                good_name = cursor.fetchone()['good_name']

                with connection.cursor() as cursor:
                    cursor.execute("SELECT good_id, good_name FROM Goods")
                    goods = cursor.fetchall()

                return render_template('monthly_sales.html', goods=goods,
                                       selected_good_id=good_id, good_name=good_name,
                                       start_date=start_date, end_date=end_date, total=total)

        except Error as e:
            flash(f"计算月度商品销售额时出错: {e}", "error")
            return redirect(url_for('calculate_monthly_sales'))


@app.route('/calculate/period_sales', methods=['GET', 'POST'])
@db_required
def calculate_period_sales(connection):
    """计算期间销售总额"""
    if request.method == 'GET':
        return render_template('period_sales.html')

    elif request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        if not start_date or not end_date:
            flash("请输入开始和结束日期", "warning")
            return redirect(url_for('calculate_period_sales'))

        try:
            with connection.cursor() as cursor:
                # 调用存储过程
                cursor.callproc("CalculateSalesTotalForPeriod", (start_date, end_date, 0))

                # 获取结果
                cursor.execute("SELECT @_CalculateSalesTotalForPeriod_2")
                total = cursor.fetchone()['@_CalculateSalesTotalForPeriod_2']

                return render_template('period_sales.html',
                                       start_date=start_date, end_date=end_date, total=total)

        except Error as e:
            flash(f"计算期间销售总额时出错: {e}", "error")
            return redirect(url_for('calculate_period_sales'))


@app.route('/calculate/period_profit', methods=['GET', 'POST'])
@db_required
def calculate_period_profit(connection):
    """计算期间销售利润"""
    if request.method == 'GET':
        return render_template('period_profit.html')

    elif request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        if not start_date or not end_date:
            flash("请输入开始和结束日期", "warning")
            return redirect(url_for('calculate_period_profit'))

        try:
            with connection.cursor() as cursor:
                # 调用存储过程
                cursor.callproc("CalculateSalesProfitForPeriod", (start_date, end_date, 0))

                # 获取结果
                cursor.execute("SELECT @_CalculateSalesProfitForPeriod_2")
                profit = cursor.fetchone()['@_CalculateSalesProfitForPeriod_2']

                return render_template('period_profit.html',
                                       start_date=start_date, end_date=end_date, profit=profit)

        except Error as e:
            flash(f"计算期间销售利润时出错: {e}", "error")
            return redirect(url_for('calculate_period_profit'))


if __name__ == '__main__':
    app.run(debug=False)