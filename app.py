from flask import Flask, render_template, request, redirect, url_for, flash
import os
import psycopg2
from psycopg2 import sql
from datetime import date
import time
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ====================== 数据库配置（自动读取 Vercel 环境变量）======================
def get_db():
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT"),
        sslmode="require"
    )
    return conn

# ====================== 初始化数据库（自动创建表 + 插入数据）======================
def init_db():
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST"),
            database=os.environ.get("DB_NAME"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            port=os.environ.get("DB_PORT"),
            sslmode="require"
        )
        cur = conn.cursor()

        # 用户表
        cur.execute('''
            CREATE TABLE IF NOT EXISTS User (
                user_id VARCHAR(10) PRIMARY KEY,
                user_name VARCHAR(50) NOT NULL,
                phone VARCHAR(20) NOT NULL
            )
        ''')

        # 商品表
        cur.execute('''
            CREATE TABLE IF NOT EXISTS Item (
                item_id VARCHAR(10) PRIMARY KEY,
                item_name VARCHAR(100) NOT NULL,
                category VARCHAR(50) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                status SMALLINT NOT NULL DEFAULT 0 CHECK (status IN (0,1)),
                seller_id VARCHAR(10) NOT NULL,
                FOREIGN KEY (seller_id) REFERENCES User(user_id)
            )
        ''')

        # 订单表
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

        # 插入用户数据（已存在则跳过）
        users = [
            ('u001','ZhangSan','13800000001'),
            ('u002','LiSi','13800000002'),
            ('u003','WangWu','13800000003'),
            ('u004','ZhaoLiu','13800000004')
        ]
        for user in users:
            cur.execute('''
                INSERT INTO User (user_id, user_name, phone)
                SELECT %s, %s, %s
                WHERE NOT EXISTS (SELECT 1 FROM User WHERE user_id = %s)
            ''', (user[0], user[1], user[2], user[0]))

        # 插入商品
        items = [
            ('i001','CalculusBook','Book',20.00,0,'u001'),
            ('i002','DeskLamp','DailyGoods',35.00,1,'u002'),
            ('i003','Microcontroller','Electronics',80.00,0,'u001'),
            ('i004','Chair','Furniture',50.00,1,'u003'),
            ('i005','WaterBottle','DailyGoods',15.00,0,'u004')
        ]
        for item in items:
            cur.execute('''
                INSERT INTO Item (item_id, item_name, category, price, status, seller_id)
                SELECT %s, %s, %s, %s, %s, %s
                WHERE NOT EXISTS (SELECT 1 FROM Item WHERE item_id = %s)
            ''', (item[0], item[1], item[2], item[3], item[4], item[5], item[0]))

        # 插入订单
        orders = [
            ('o001','i002','u001','2024-05-01'),
            ('o002','i004','u002','2024-05-03')
        ]
        for order in orders:
            cur.execute('''
                INSERT INTO Orders (order_id, item_id, buyer_id, order_date)
                SELECT %s, %s, %s, %s
                WHERE NOT EXISTS (SELECT 1 FROM Orders WHERE order_id = %s)
            ''', (order[0], order[1], order[2], order[3], order[0]))

        # 创建视图
        cur.execute('''
            CREATE OR REPLACE VIEW v_sold_item AS
            SELECT i.item_name, o.buyer_id FROM Item i
            JOIN Orders o ON i.item_id = o.item_id
            WHERE i.status = 1
        ''')

        cur.execute('''
            CREATE OR REPLACE VIEW v_unsold_item AS
            SELECT * FROM Item WHERE status = 0
        ''')

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("初始化数据库错误:", e)

# 启动时自动初始化
try:
    init_db()
except Exception as e:
    print(f"数据库初始化出错：{e}")

# ====================== 页面路由（完全不变）======================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/items')
def show_items():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Item ORDER BY item_id")
    items = cur.fetchall()
    cur.execute("SELECT user_id, user_name FROM User")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('items.html', items=items, users=users)

@app.route('/users')
def show_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM User")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('users.html', users=users)

@app.route('/orders')
def show_orders():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Orders ORDER BY order_date")
    orders = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('orders.html', orders=orders)

@app.route('/manage')
def manage_items():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Item ORDER BY item_id")
    items = cur.fetchall()
    cur.execute("SELECT user_id, user_name FROM User")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('manage.html', items=items, users=users)

# ====================== 数据操作（完全不变）======================
@app.route('/item/add', methods=['POST'])
def add_item():
    item_id = request.form['item_id']
    item_name = request.form['item_name']
    category = request.form['category']
    price = request.form['price']
    seller_id = request.form['seller_id']
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO Item (item_id, item_name, category, price, status, seller_id) "
                    "VALUES (%s,%s,%s,%s,0,%s)", (item_id, item_name, category, price, seller_id))
        conn.commit()
        flash("商品添加成功！", "success")
    except Exception as e:
        flash(f"添加失败：{e}", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('manage_items'))

@app.route('/item/edit', methods=['POST'])
def edit_item():
    item_id = request.form['item_id']
    new_price = request.form['new_price']
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE Item SET price = %s WHERE item_id = %s", (new_price, item_id))
        conn.commit()
        flash("价格修改成功！", "success")
    except Exception as e:
        flash(f"修改失败：{e}", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('manage_items'))

@app.route('/item/delete', methods=['POST'])
def delete_item():
    item_id = request.form['item_id']
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM Item WHERE item_id = %s AND status = 0", (item_id,))
        if cur.rowcount == 0:
            flash("删除失败：商品不存在或已售出，无法删除。", "warning")
        else:
            conn.commit()
            flash("删除成功！", "success")
    except Exception as e:
        flash(f"删除失败：{e}", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('manage_items'))

# ====================== 购买逻辑（完全不变）======================
@app.route('/buy/<item_id>', methods=['POST'])
def buy_item(item_id):
    buyer_id = request.form.get('buyer_id')
    if not buyer_id:
        flash("请选择买家！", "warning")
        return redirect(url_for('show_items'))

    conn = get_db()
    cur = conn.cursor()
    try:
        conn.autocommit = False
        cur.execute("SELECT status FROM Item WHERE item_id = %s FOR UPDATE", (item_id,))
        row = cur.fetchone()
        if row is None:
            conn.rollback()
            flash("商品不存在！", "danger")
            return redirect(url_for('show_items'))
        if row[0] == 1:
            conn.rollback()
            flash("该商品已售出，无法再次购买！", "danger")
            return redirect(url_for('show_items'))

        order_id = "ord" + str(int(time.time()))[-6:] + str(random.randint(10,99))
        cur.execute("INSERT INTO Orders (order_id, item_id, buyer_id, order_date) "
                    "VALUES (%s, %s, %s, CURRENT_DATE)", (order_id, item_id, buyer_id))
        cur.execute("UPDATE Item SET status = 1 WHERE item_id = %s", (item_id,))
        conn.commit()
        flash(f"购买成功！订单号：{order_id}", "success")
    except Exception as e:
        conn.rollback()
        flash(f"购买失败：{e}", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('show_items'))

# ====================== 查询页面（完全不变）======================
@app.route('/query/basic')
def basic_query():
    q = request.args.get('q')
    if not q:
        return render_template('query_basic.html')
    conn = get_db()
    cur = conn.cursor()
    sqls = {
        '1': ("所有未售出的商品", "SELECT * FROM Item WHERE status = 0"),
        '2': ("价格大于30的商品", "SELECT * FROM Item WHERE price > 30"),
        '3': ("“生活用品”类商品", "SELECT * FROM Item WHERE category = 'DailyGoods'"),
        '4': ("u001 发布的所有商品", "SELECT * FROM Item WHERE seller_id = 'u001'"),
    }
    title, sql = sqls.get(q, ('', ''))
    if sql:
        cur.execute(sql)
        rows = cur.fetchall()
    else:
        rows = []
    cur.close()
    conn.close()
    return render_template('query_basic.html', title=title, rows=rows)

@app.route('/query/join')
def join_query():
    q = request.args.get('q')
    if not q:
        return render_template('query_join.html')
    conn = get_db()
    cur = conn.cursor()
    if q == '1':
        title = "所有已售商品及其买家姓名"
        cur.execute("SELECT i.item_name, u.user_name FROM Orders o "
                    "JOIN Item i ON o.item_id = i.item_id "
                    "JOIN User u ON o.buyer_id = u.user_id")
    elif q == '2':
        title = "每个订单：商品名 + 买家名 + 日期"
        cur.execute("SELECT o.order_id, i.item_name, u.user_name, o.order_date "
                    "FROM Orders o "
                    "JOIN Item i ON o.item_id = i.item_id "
                    "JOIN User u ON o.buyer_id = u.user_id")
    elif q == '3':
        title = "卖家是 u001 的商品是否被购买"
        cur.execute("SELECT i.item_id, i.item_name, "
                    "CASE WHEN o.item_id IS NOT NULL THEN '是' ELSE '否' END AS is_sold "
                    "FROM Item i LEFT JOIN Orders o ON i.item_id = o.item_id "
                    "WHERE i.seller_id = 'u001'")
    else:
        title = ''
        rows = []
        cur.close()
        conn.close()
        return render_template('query_join.html')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('query_join.html', title=title, rows=rows)

@app.route('/query/aggregate')
def aggregate_query():
    q = request.args.get('q')
    if not q:
        return render_template('query_aggregate.html')
    conn = get_db()
    cur = conn.cursor()
    if q == '1':
        title = "统计商品总数"
        cur.execute("SELECT COUNT(*) FROM Item")
    elif q == '2':
        title = "每类商品数量"
        cur.execute("SELECT category, COUNT(*) FROM Item GROUP BY category")
    elif q == '3':
        title = "所有商品平均价格"
        cur.execute("SELECT AVG(price) FROM Item")
    elif q == '4':
        title = "发布商品数量最多的用户"
        cur.execute("SELECT seller_id, COUNT(*) AS cnt FROM Item "
                    "GROUP BY seller_id ORDER BY cnt DESC LIMIT 1")
    else:
        title = ''
        rows = []
        cur.close()
        conn.close()
        return render_template('query_aggregate.html')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('query_aggregate.html', title=title, rows=rows)

@app.route('/query/view')
def view_query():
    v = request.args.get('v')
    if v == 'sold':
        title = "已售商品视图（商品名 + 买家ID）"
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM v_sold_item")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('query_view.html', title=title, rows=rows)
    elif v == 'unsold':
        title = "未售商品视图"
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM v_unsold_item")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('query_view.html', title=title, rows=rows)
    return render_template('query_view.html')
app = app
if __name__ == '__main__':
    app.run(debug=True)
