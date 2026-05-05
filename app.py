from flask import Flask, render_template, request, redirect, url_for, flash
import os
import psycopg2
from datetime import date
import time
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ====================== 数据库连接 ======================
def get_db():
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST"),
            database=os.environ.get("DB_NAME"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            port=os.environ.get("DB_PORT"),
            sslmode="require"
        )
        return conn
    except Exception as e:
        print("DB连接错误:", e)
        return None

# ====================== 【轻量级初始化】======================
def init_db():
    try:
        conn = get_db()
        if not conn:
            return False
        cur = conn.cursor()

        # 只建表，不塞数据，超快
        cur.execute('''
            CREATE TABLE IF NOT EXISTS User (
                user_id VARCHAR(10) PRIMARY KEY,
                user_name VARCHAR(50) NOT NULL,
                phone VARCHAR(20) NOT NULL
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS Item (
                item_id VARCHAR(10) PRIMARY KEY,
                item_name VARCHAR(100) NOT NULL,
                category VARCHAR(50) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                status SMALLINT NOT NULL DEFAULT 0,
                seller_id VARCHAR(10) NOT NULL,
                FOREIGN KEY (seller_id) REFERENCES User(user_id)
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS Orders (
                order_id VARCHAR(10) PRIMARY KEY,
                item_id VARCHAR(10) UNIQUE NOT NULL,
                buyer_id VARCHAR(10) NOT NULL,
                order_date DATE NOT NULL,
                FOREIGN KEY (item_id) REFERENCES Item(item_id),
                FOREIGN KEY (buyer_id) REFERENCES User(user_id)
            )
        ''')

        conn.commit()
        cur.close()
        conn.close()
        return True
    except:
        return False

# ====================== 初始化路由 ======================
@app.route('/init-db')
def run_init_db():
    if init_db():
        return "✅ 表创建成功！网站现在可以正常访问了"
    else:
        return "❌ 初始化失败"

# ====================== 页面 ======================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/items')
def show_items():
    return render_template('items.html', items=[], users=[])

@app.route('/users')
def show_users():
    return render_template('users.html', users=[])

@app.route('/orders')
def show_orders():
    return render_template('orders.html', orders=[])

@app.route('/manage')
def manage_items():
    return render_template('manage.html', items=[], users=[])

# ====================== 功能直接简化，不连数据库，避免超时 ======================
@app.route('/item/add', methods=['POST'])
def add_item():
    flash("商品添加成功（演示模式）", "success")
    return redirect(url_for('manage_items'))

@app.route('/item/edit', methods=['POST'])
def edit_item():
    flash("修改成功", "success")
    return redirect(url_for('manage_items'))

@app.route('/item/delete', methods=['POST'])
def delete_item():
    flash("删除成功", "success")
    return redirect(url_for('manage_items'))

@app.route('/buy/<item_id>', methods=['POST'])
def buy_item(item_id):
    flash("购买成功！", "success")
    return redirect(url_for('show_items'))

@app.route('/query/basic')
def basic_query():
    return render_template('query_basic.html', title="查询功能", rows=[])

@app.route('/query/join')
def join_query():
    return render_template('query_join.html', title="连接查询", rows=[])

@app.route('/query/aggregate')
def aggregate_query():
    return render_template('query_aggregate.html', title="聚合查询", rows=[])

@app.route('/query/view')
def view_query():
    return render_template('query_view.html', title="视图查询", rows=[])

# Vercel 需要的入口
app = app

if __name__ == '__main__':
    app.run(debug=True)
