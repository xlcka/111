from flask import Flask, render_template, request, redirect, url_for, flash
import pymysql
from datetime import date

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': '12345678',   # 请修改为你的密码
    'database': 'campus_trade',
    'charset': 'utf8mb4'  
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

def init_db():
    """
    创建数据库、表、主键、外键、非空约束，并插入初始数据。
    使用 INSERT IGNORE 确保幂等性。
    """
    conn = pymysql.connect(host=DB_CONFIG['host'], port=DB_CONFIG['port'],
                           user=DB_CONFIG['user'], password=DB_CONFIG['password'],charset='utf8mb4' )
    cur = conn.cursor()
    # 建库
    cur.execute("CREATE DATABASE IF NOT EXISTS campus_trade "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute("USE campus_trade")

    # 建表 - User
    cur.execute("""
        CREATE TABLE IF NOT EXISTS User (
            user_id VARCHAR(10) PRIMARY KEY,
            user_name VARCHAR(50) NOT NULL,
            phone VARCHAR(20) NOT NULL
        ) ENGINE=InnoDB
    """)

    # 建表 - Item
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Item (
            item_id VARCHAR(10) PRIMARY KEY,
            item_name VARCHAR(100) NOT NULL,
            category VARCHAR(50) NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            status TINYINT NOT NULL DEFAULT 0 CHECK (status IN (0,1)),
            seller_id VARCHAR(10) NOT NULL,
            FOREIGN KEY (seller_id) REFERENCES User(user_id)
        ) ENGINE=InnoDB
    """)

    # 建表 - Orders
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Orders (
            order_id VARCHAR(10) PRIMARY KEY,
            item_id VARCHAR(10) UNIQUE NOT NULL,
            buyer_id VARCHAR(10) NOT NULL,
            order_date DATE NOT NULL,
            FOREIGN KEY (item_id) REFERENCES Item(item_id),
            FOREIGN KEY (buyer_id) REFERENCES User(user_id)
        ) ENGINE=InnoDB
    """)

    # 插入初始数据（作业提供的全部数据）
    # User
    cur.execute("INSERT IGNORE INTO User VALUES ('u001','ZhangSan','13800000001')")
    cur.execute("INSERT IGNORE INTO User VALUES ('u002','LiSi','13800000002')")
    cur.execute("INSERT IGNORE INTO User VALUES ('u003','WangWu','13800000003')")
    cur.execute("INSERT IGNORE INTO User VALUES ('u003','ZhaoLiu','13800000004')")
    # Item（全部未售）
    cur.execute("INSERT IGNORE INTO Item VALUES ('i001','CalculusBook','Book',20.00,0,'u001')")
    cur.execute("INSERT IGNORE INTO Item VALUES ('i002','DeskLamp','DailyGoods',35.00,1,'u002')")
    cur.execute("INSERT IGNORE INTO Item VALUES ('i003','Microcontroller','Electronics',80.00,0,'u001')")
    cur.execute("INSERT IGNORE INTO Item VALUES ('i004','Chair','Furniture',50.00,1,'u003')")
    cur.execute("INSERT IGNORE INTO Item VALUES ('i005','WaterBottle','DailyGoods',15.00,0,'u004')")

    # 插入订单数据
    cur.execute("INSERT IGNORE INTO Orders VALUES ('o001','i002','u001','2024-05-01')")
    cur.execute("INSERT IGNORE INTO Orders VALUES ('o002','i004','u002','2024-05-03')")
    
    # 创建视图（作业第六部分）
    cur.execute("CREATE OR REPLACE VIEW v_sold_item AS "
                "SELECT i.item_name, o.buyer_id FROM Item i JOIN Orders o ON i.item_id = o.item_id WHERE i.status = 1")
    cur.execute("CREATE OR REPLACE VIEW v_unsold_item AS "
                "SELECT * FROM Item WHERE status = 0")

    conn.commit()
    cur.close()
    conn.close()

# 每次启动时自动执行初始化
try:
    init_db()
except Exception as e:
    print(f"数据库初始化出错：{e}")

# ====================== 页面路由 ======================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/items')
def show_items():
    """商品列表页面（支持购买操作）"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Item ORDER BY item_id")
    items = cur.fetchall()
    # 获取所有用户，供购买下拉框使用
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
    """商品管理页面（增删改）"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Item ORDER BY item_id")
    items = cur.fetchall()
    cur.execute("SELECT user_id, user_name FROM User")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('manage.html', items=items, users=users)

# ====================== 数据操作（增删改） ======================
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

# ====================== 购买业务逻辑（作业第七部分）======================
@app.route('/buy/<item_id>', methods=['POST'])
def buy_item(item_id):
    buyer_id = request.form.get('buyer_id')
    if not buyer_id:
        flash("请选择买家！", "warning")
        return redirect(url_for('show_items'))

    conn = get_db()
    cur = conn.cursor()
    try:
        # 开启事务，保证一致性
        conn.begin()

        # 1. 检查商品是否已售（防止重复购买）
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

        # 2. 生成订单ID（简单时间戳+随机）
        import time, random
        order_id = "ord" + str(int(time.time()))[-6:] + str(random.randint(10,99))

        # 3. 插入订单记录
        cur.execute("INSERT INTO Orders (order_id, item_id, buyer_id, order_date) "
                    "VALUES (%s, %s, %s, CURDATE())", (order_id, item_id, buyer_id))

        # 4. 更新商品状态为已售
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

# ====================== 查询页面（基本/连接/聚合/视图）======================
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
        '3': ("“生活用品”类商品", "SELECT * FROM Item WHERE category = '生活用品'"),
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
    """展示两个视图（已售/未售）"""
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

if __name__ == '__main__':
    app.run(debug=True)