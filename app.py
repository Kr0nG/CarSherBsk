from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from functools import wraps  # Добавлен импорт

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-key')

login_manager = LoginManager(app)
login_manager.login_view = 'login'

DB_CONFIG = {
    'dbname': 'carsharing_gg29',
    'user': 'postgre',
    'password': 'CT0s2HSM3WpzFqmnRdWRRjDJriS3PlW4',
    'host': 'dpg-d4vqh2vpm1nc73btsd1g-a.oregon-postgres.render.com',
    'port': '5432'
}

TEST_DATA_LOADED = False

class User(UserMixin):
    def __init__(self, id, username, email, password_hash, is_admin=False, phone=None, driver_license=None):
        self.id = str(id)
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.is_admin = is_admin
        self.phone = phone
        self.driver_license = driver_license

    @staticmethod
    def from_dict(data):
        return User(data['id'], data['username'], data['email'], data['password_hash'],
                   data['is_admin'], data['phone'], data['driver_license'])

def get_db():
    return psycopg2.connect(**DB_CONFIG)

def query_db(query, params=(), fetch='all'):
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch == 'all':
                return cur.fetchall()
            elif fetch == 'one':
                return cur.fetchone()
            else:
                conn.commit()
                return cur.rowcount

def init_db():
    try:
        # Таблицы
        query_db('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                phone VARCHAR(20),
                driver_license VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''', fetch=None)
        
        query_db('''
            CREATE TABLE IF NOT EXISTS cars (
                id SERIAL PRIMARY KEY,
                brand VARCHAR(100) NOT NULL,
                model VARCHAR(100) NOT NULL,
                year INTEGER NOT NULL,
                daily_price DECIMAL(10,2) NOT NULL,
                fuel_type VARCHAR(50),
                transmission VARCHAR(50),
                seats INTEGER DEFAULT 5,
                location VARCHAR(255),
                image_url TEXT,
                is_available BOOLEAN DEFAULT TRUE,
                color VARCHAR(50),
                description TEXT,
                car_class VARCHAR(50) DEFAULT 'Эконом',
                features TEXT[],
                engine VARCHAR(100),
                consumption VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''', fetch=None)
        
        query_db('''
            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                car_id INTEGER REFERENCES cars(id),
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                total_price DECIMAL(10,2) NOT NULL,
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''', fetch=None)
        
        # Админ по умолчанию
        if not query_db("SELECT id FROM users WHERE username = 'admin'", fetch='one'):
            hash = generate_password_hash('admin123')
            query_db("INSERT INTO users (username, email, password_hash, is_admin) VALUES (%s, %s, %s, %s)",
                    ('admin', 'admin@carsharebsk.ru', hash, True), fetch=None)
        
        print("✅ База инициализирована")
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")

def load_test_data():
    global TEST_DATA_LOADED
    if TEST_DATA_LOADED or query_db("SELECT COUNT(*) as c FROM cars", fetch='one')['c'] > 0:
        return
    
    cars = [
        ('Hyundai', 'Solaris', 2023, 1200, 'Бензин', 'Автомат', 5, 'ул. Ленина, 123',
         'https://s.auto.drom.ru/i24206/c/photos/fullsize/hyundai/solaris/hyundai_solaris_677323.jpg',
         True, 'Белый', 'Экономный городской авто', 'Эконом',
         ['Кондиционер', 'Bluetooth', 'Парктроники'], '1.6L', '6.5 л/100км'),
        
        ('Toyota', 'Camry', 2023, 2500, 'Бензин', 'Автомат', 5, 'пр. Ленина, 89',
         'https://iat.ru/uploads/origin/models/737981/1.webp',
         True, 'Черный', 'Комфортабельный седан', 'Комфорт',
         ['Климат-контроль', 'Кожаный салон', 'Камера'], '2.5L', '7.8 л/100км'),
        
        ('BMW', '5 Series', 2023, 4500, 'Бензин', 'Автомат', 5, 'пр. Коммунарский, 156',
         'https://www.thedrive.com/wp-content/uploads/2024/10/tgI7q.jpg?w=1819&h=1023',
         True, 'Черный', 'Представительский седан', 'Премиум',
         ['Память сидений', 'Массаж', 'Адаптивный круиз'], '3.0L', '8.5 л/100км')
    ]
    
    for car in cars:
        query_db('''
            INSERT INTO cars (brand, model, year, daily_price, fuel_type, transmission,
            seats, location, image_url, is_available, color, description,
            car_class, features, engine, consumption) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', car, fetch=None)
    
    TEST_DATA_LOADED = True
    print("✅ Тестовые данные загружены")

@login_manager.user_loader
def load_user(user_id):
    user = query_db('SELECT * FROM users WHERE id = %s', (user_id,), fetch='one')
    return User.from_dict(user) if user else None

init_db()
load_test_data()

# Маршруты аутентификации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        data = request.form
        if data['password'] != data['confirm_password']:
            flash('Пароли не совпадают', 'danger')
            return redirect(url_for('register'))
        
        if query_db('SELECT id FROM users WHERE username = %s OR email = %s', 
                   (data['username'], data['email']), fetch='one'):
            flash('Пользователь уже существует', 'danger')
            return redirect(url_for('register'))
        
        hash = generate_password_hash(data['password'])
        query_db('INSERT INTO users (username, email, password_hash, phone, driver_license) VALUES (%s, %s, %s, %s, %s)',
                (data['username'], data['email'], hash, data['phone'], data['driver_license']), fetch=None)
        flash('Регистрация успешна!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        user = query_db('SELECT * FROM users WHERE username = %s', (request.form['username'],), fetch='one')
        if user and check_password_hash(user['password_hash'], request.form['password']):
            login_user(User.from_dict(user))
            flash(f'Добро пожаловать, {user["username"]}!', 'success')
            return redirect(url_for('index'))
        flash('Неверные данные', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

# Основные маршруты
@app.route('/')
def index():
    cars = query_db('SELECT * FROM cars WHERE is_available = TRUE LIMIT 3', fetch='all')
    stats = {
        'total_cars': query_db('SELECT COUNT(*) as c FROM cars', fetch='one')['c'],
        'total_users': query_db('SELECT COUNT(*) as c FROM users', fetch='one')['c']
    }
    return render_template('index.html', cars=cars, **stats)

@app.route('/cars')
def cars():
    filters = {k: v for k, v in request.args.items() if v != 'all'}
    query = 'SELECT * FROM cars WHERE is_available = TRUE'
    params = []
    
    for key, value in filters.items():
        query += f' AND {key} = %s'
        params.append(value)
    
    cars = query_db(query, params, fetch='all')
    
    # Опции фильтров
    options = {}
    for field in ['car_class', 'transmission', 'fuel_type']:
        rows = query_db(f'SELECT DISTINCT {field} FROM cars WHERE {field} IS NOT NULL', fetch='all')
        options[f'{field}s'] = [r[field] for r in rows]
    
    return render_template('cars.html', cars=cars, **options, **filters)

@app.route('/car/<int:car_id>')
@login_required
def car_detail(car_id):
    car = query_db('SELECT * FROM cars WHERE id = %s', (car_id,), fetch='one')
    if not car:
        flash('Авто не найден', 'danger')
        return redirect(url_for('cars'))
    
    similar = query_db('SELECT * FROM cars WHERE car_class = %s AND id != %s LIMIT 3',
                      (car['car_class'], car_id), fetch='all')
    return render_template('booking.html', car=car, similar_cars=similar)

@app.route('/book', methods=['POST'])
@login_required
def book_car():
    try:
        car_id = int(request.form['car_id'])
        start = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        today = datetime.now().date()
        
        if start < today or end < start:
            return jsonify({'success': False, 'message': 'Некорректные даты'})
        
        car = query_db('SELECT * FROM cars WHERE id = %s', (car_id,), fetch='one')
        if not car or not car['is_available']:
            return jsonify({'success': False, 'message': 'Авто недоступно'})
        
        # Проверка доступности
        if query_db('''
            SELECT id FROM bookings WHERE car_id = %s AND status = 'active' 
            AND ((start_date <= %s AND end_date >= %s) OR (start_date <= %s AND end_date >= %s))
        ''', (car_id, start, start, end, end), fetch='one'):
            return jsonify({'success': False, 'message': 'Даты заняты'})
        
        days = (end - start).days
        price = float(car['daily_price']) * days
        
        query_db('INSERT INTO bookings (user_id, car_id, start_date, end_date, total_price) VALUES (%s, %s, %s, %s, %s)',
                (current_user.id, car_id, start, end, price), fetch=None)
        
        return jsonify({'success': True, 'message': f'Бронирование создано! {price} ₽ за {days} дн.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

@app.route('/profile')
@login_required
def profile():
    bookings = query_db('''
        SELECT b.*, c.brand, c.model, c.image_url FROM bookings b
        JOIN cars c ON b.car_id = c.id WHERE b.user_id = %s ORDER BY b.created_at DESC
    ''', (current_user.id,), fetch='all')
    return render_template('profile.html', bookings=bookings)

@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    rows = query_db("UPDATE bookings SET status = 'cancelled' WHERE id = %s AND user_id = %s AND status = 'active'",
                   (booking_id, current_user.id), fetch=None)
    flash('Бронирование отменено' if rows > 0 else 'Не найдено', 'success' if rows > 0 else 'danger')
    return redirect(url_for('profile'))

@app.route('/contacts')
def contacts():
    return render_template('contacts.html')

@app.route('/about')
def about():
    return render_template('about.html')

# Декоратор для админ-доступа
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Требуется авторизация', 'danger')
            return redirect(url_for('login'))
        if not current_user.is_admin:
            flash('Доступ запрещен', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@login_required
@admin_required
def admin():
    stats = {
        'total_cars': query_db('SELECT COUNT(*) as c FROM cars', fetch='one')['c'],
        'total_users': query_db('SELECT COUNT(*) as c FROM users', fetch='one')['c'],
        'active_bookings': query_db("SELECT COUNT(*) as c FROM bookings WHERE status = 'active'", fetch='one')['c'],
        'total_revenue': query_db("SELECT COALESCE(SUM(total_price), 0) as s FROM bookings WHERE status = 'active'", fetch='one')['s'],
        'all_cars': query_db('SELECT * FROM cars ORDER BY id', fetch='all')
    }
    return render_template('admin.html', **stats)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = query_db('SELECT * FROM users ORDER BY created_at DESC', fetch='all')
    
    # Статистика бронирований
    stats = {}
    bookings = query_db('''
        SELECT user_id, COUNT(*) as total, 
        SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active 
        FROM bookings GROUP BY user_id
    ''', fetch='all')
    
    for row in bookings:
        stats[row['user_id']] = {'total': row['total'], 'active': row['active']}
    
    all_bookings = query_db('''
        SELECT b.*, u.username, u.email, c.brand, c.model, c.image_url 
        FROM bookings b JOIN users u ON b.user_id = u.id JOIN cars c ON b.car_id = c.id
        ORDER BY b.created_at DESC
    ''', fetch='all')
    
    return render_template('admin_users.html', users=users, user_stats=stats, 
                          admin_count=query_db("SELECT COUNT(*) as c FROM users WHERE is_admin = TRUE", fetch='one')['c'],
                          user_count=query_db("SELECT COUNT(*) as c FROM users WHERE is_admin = FALSE", fetch='one')['c'],
                          bookings_db=all_bookings)

# CRUD для автомобилей (админ)
@app.route('/admin/get_car/<int:car_id>')
@login_required
@admin_required
def get_car_data(car_id):
    car = query_db('SELECT * FROM cars WHERE id = %s', (car_id,), fetch='one')
    return jsonify({'success': bool(car), 'car': car})

@app.route('/admin/update_car/<int:car_id>', methods=['POST'])
@login_required
@admin_required
def update_car(car_id):
    data = request.form
    features = [f.strip() for f in data.get('features', '').split(',') if f.strip()]
    
    query_db('''
        UPDATE cars SET 
        brand = COALESCE(NULLIF(%s, ''), brand),
        model = COALESCE(NULLIF(%s, ''), model),
        year = COALESCE(NULLIF(%s, ''), year),
        daily_price = COALESCE(NULLIF(%s, ''), daily_price),
        car_class = COALESCE(NULLIF(%s, ''), car_class),
        fuel_type = COALESCE(NULLIF(%s, ''), fuel_type),
        transmission = COALESCE(NULLIF(%s, ''), transmission),
        color = COALESCE(NULLIF(%s, ''), color),
        seats = COALESCE(NULLIF(%s, ''), seats),
        location = COALESCE(NULLIF(%s, ''), location),
        description = COALESCE(NULLIF(%s, ''), description),
        image_url = COALESCE(NULLIF(%s, ''), image_url),
        engine = COALESCE(NULLIF(%s, ''), engine),
        consumption = COALESCE(NULLIF(%s, ''), consumption),
        features = COALESCE(%s, features)
        WHERE id = %s
    ''', (data.get('brand'), data.get('model'), data.get('year'), data.get('daily_price'),
          data.get('car_class'), data.get('fuel_type'), data.get('transmission'),
          data.get('color'), data.get('seats'), data.get('location'), data.get('description'),
          data.get('image_url'), data.get('engine'), data.get('consumption'),
          features if features else None, car_id), fetch=None)
    
    return jsonify({'success': True, 'message': 'Авто обновлен'})

@app.route('/admin/delete_car/<int:car_id>', methods=['POST'])
@login_required
@admin_required
def delete_car(car_id):
    # Проверка активных бронирований
    active = query_db("SELECT COUNT(*) as c FROM bookings WHERE car_id = %s AND status = 'active'", 
                     (car_id,), fetch='one')['c']
    if active > 0:
        return jsonify({'success': False, 'message': f'Есть активные бронирования ({active})'})
    
    query_db('DELETE FROM bookings WHERE car_id = %s', (car_id,), fetch=None)
    query_db('DELETE FROM cars WHERE id = %s', (car_id,), fetch=None)
    return jsonify({'success': True, 'message': 'Авто удален'})

@app.route('/admin/add_car', methods=['POST'])
@login_required
@admin_required
def add_car():
    data = request.form
    features = [f.strip() for f in data.get('features', '').split(',') if f.strip()]
    
    query_db('''
        INSERT INTO cars (brand, model, year, daily_price, car_class, fuel_type, 
        transmission, image_url, location, color, seats, description,
        engine, consumption, features) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (data['brand'], data['model'], int(data['year']), float(data['daily_price']),
          data['car_class'], data['fuel_type'], data['transmission'], data.get('image_url'),
          data.get('location', 'ул. Ленина, 123'), data.get('color', 'синий'),
          int(data.get('seats', 5)), data.get('description', 'Новый авто'),
          data.get('engine'), data.get('consumption'), features if features else None), fetch=None)
    
    return jsonify({'success': True, 'message': f'{data["brand"]} {data["model"]} добавлен'})

@app.route('/admin/toggle_car/<int:car_id>', methods=['POST'])
@login_required
@admin_required
def toggle_car(car_id):
    car = query_db('SELECT brand, model, is_available FROM cars WHERE id = %s', (car_id,), fetch='one')
    if car:
        new = not car['is_available']
        query_db('UPDATE cars SET is_available = %s WHERE id = %s', (new, car_id), fetch=None)
        status = "доступен" if new else "недоступен"
        return jsonify({'success': True, 'message': f'{car["brand"]} {car["model"]} теперь {status}'})
    return jsonify({'success': False, 'message': 'Не найден'})

@app.route('/admin/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def admin_cancel_booking(booking_id):
    rows = query_db("UPDATE bookings SET status = 'cancelled' WHERE id = %s AND status = 'active'", 
                   (booking_id,), fetch=None)
    return jsonify({'success': rows > 0, 'message': 'Отменено' if rows > 0 else 'Не найдено'})

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    if str(user_id) == current_user.id:
        return jsonify({'success': False, 'message': 'Нельзя удалить себя'})
    
    active = query_db("SELECT COUNT(*) as c FROM bookings WHERE user_id = %s AND status = 'active'", 
                     (user_id,), fetch='one')['c']
    if active > 0:
        return jsonify({'success': False, 'message': 'Есть активные бронирования'})
    
    user = query_db('SELECT username, is_admin FROM users WHERE id = %s', (user_id,), fetch='one')
    if user and not user['is_admin']:
        query_db('DELETE FROM bookings WHERE user_id = %s', (user_id,), fetch=None)
        query_db('DELETE FROM users WHERE id = %s', (user_id,), fetch=None)
        return jsonify({'success': True, 'message': f'Пользователь {user["username"]} удален'})
    
    return jsonify({'success': False, 'message': 'Не найден или админ'})

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

if __name__ == '__main__':
    print("🚀 CarShareBsk запущен: http://localhost:5001")
    print("🔑 Админ: admin / admin123")
    app.run(debug=True, port=5001)