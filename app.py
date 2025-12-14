import os
import json
from datetime import datetime
import time

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor

# ========== НАСТРОЙКА ПРИЛОЖЕНИЯ ==========
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-123456789')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ========== НАСТРОЙКА БАЗЫ ДАННЫХ ==========
def get_db_connection():
    """Подключение к PostgreSQL на Render"""
    try:
        conn = psycopg2.connect(
            dbname='postgres18',
            user='postgres18_user',
            password='O9xtslQ40gB97zgcQp01pKAiA4RlcAx5',
            host='dpg-d4vguk1r0fns739lmkfg-a.virginia-postgres.render.com',
            port=5432,
            connect_timeout=10
        )
        print("✅ Подключение к PostgreSQL успешно")
        return conn
    except Exception as e:
        print(f"❌ Ошибка подключения к PostgreSQL: {e}")
        return None

def init_database():
    """Инициализация базы данных"""
    print("🔄 Инициализация базы данных...")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Не удалось подключиться к базе данных")
        return False
    
    try:
        cur = conn.cursor()
        
        # 1. Таблица пользователей
        cur.execute('''
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
        ''')
        print("✅ Таблица 'users' создана/проверена")
        
        # 2. Таблица автомобилей
        cur.execute('''
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
        ''')
        print("✅ Таблица 'cars' создана/проверена")
        
        # 3. Таблица бронирований
        cur.execute('''
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
        ''')
        print("✅ Таблица 'bookings' создана/проверена")
        
        conn.commit()
        
        # 4. Проверяем есть ли администратор
        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cur.fetchone():
            password_hash = generate_password_hash('admin123')
            cur.execute('''
                INSERT INTO users (username, email, password_hash, is_admin)
                VALUES (%s, %s, %s, %s)
            ''', ('admin', 'admin@carsharebsk.ru', password_hash, True))
            print("👑 Администратор создан: admin / admin123")
        
        # 5. Проверяем есть ли тестовый пользователь
        cur.execute("SELECT id FROM users WHERE username = 'user'")
        if not cur.fetchone():
            password_hash2 = generate_password_hash('user123')
            cur.execute('''
                INSERT INTO users (username, email, password_hash, phone, driver_license)
                VALUES (%s, %s, %s, %s, %s)
            ''', ('user', 'user@example.com', password_hash2, '+79991234567', 'AB123456'))
            print("👤 Тестовый пользователь создан: user / user123")
        
        # 6. Проверяем есть ли автомобили
        cur.execute("SELECT COUNT(*) FROM cars")
        count = cur.fetchone()[0]
        
        if count == 0:
            print("🚗 Добавляем тестовые автомобили...")
            
            test_cars = [
                ('Hyundai', 'Solaris', 2023, 1200, 'Бензин', 'Автомат', 5,
                 'ул. Ленина, 123',
                 'https://s.auto.drom.ru/i24206/c/photos/fullsize/hyundai/solaris/hyundai_solaris_677323.jpg',
                 True, 'Белый', 'Экономичный городской автомобиль с низким расходом топлива.', 'Эконом',
                 ['Кондиционер', 'Bluetooth', 'Парктроники', 'Камера заднего вида'],
                 '1.6L', '6.5 л/100км'),
                
                ('Toyota', 'Camry', 2023, 2500, 'Бензин', 'Автомат', 5,
                 'пр. Ленина, 89',
                 'https://iat.ru/uploads/origin/models/737981/1.webp',
                 True, 'Черный', 'Комфортабельный седан для бизнес-поездок.', 'Комфорт',
                 ['Климат-контроль', 'Кожаный салон', 'Камера заднего вида', 'Паркинг-ассистент'],
                 '2.5L', '7.8 л/100км'),
                
                ('BMW', '5 Series', 2023, 4500, 'Бензин', 'Автомат', 5,
                 'пр. Коммунарский, 156',
                 'https://www.thedrive.com/wp-content/uploads/2024/10/tgI7q.jpg',
                 True, 'Черный', 'Представительский седан бизнес-класса.', 'Премиум',
                 ['Память сидений', 'Массаж сидений', 'Адаптивный круиз', 'Проекционный дисплей'],
                 '3.0L', '8.5 л/100км')
            ]
            
            for i, car in enumerate(test_cars, 1):
                cur.execute('''
                    INSERT INTO cars (
                        brand, model, year, daily_price, fuel_type, transmission,
                        seats, location, image_url, is_available, color, description,
                        car_class, features, engine, consumption
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', car)
                print(f"   ✅ Автомобиль {i}: {car[0]} {car[1]}")
        
        conn.commit()
        print("✅ База данных инициализирована успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка инициализации базы: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()

# Инициализируем базу
print("=" * 60)
print("🚀 ЗАПУСК CARSHAREBSK С POSTGRESQL")
print("=" * 60)
print(f"📡 Хост: dpg-d4vguk1r0fns739lmkfg-a.virginia-postgres.render.com")
print(f"🗄️  База: postgres18")
print(f"👤 Пользователь: postgres18_user")
print("=" * 60)

if init_database():
    print("✅ База данных готова к работе")
else:
    print("⚠️ Проблемы с инициализацией базы данных")

print("=" * 60)

# ========== МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ ==========
class User(UserMixin):
    def __init__(self, id, username, email, password_hash, is_admin=False, phone=None, driver_license=None):
        self.id = str(id)
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.is_admin = bool(is_admin)
        self.phone = phone
        self.driver_license = driver_license
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if user_data:
            return User(
                user_data['id'],
                user_data['username'],
                user_data['email'],
                user_data['password_hash'],
                user_data['is_admin'],
                user_data['phone'],
                user_data['driver_license']
            )
    except Exception as e:
        print(f"Ошибка загрузки пользователя: {e}")
    return None

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def execute_query(query, params=None, fetch=True):
    """Выполняет SQL запрос"""
    conn = get_db_connection()
    if not conn:
        print(f"❌ Нет подключения для запроса: {query[:50]}...")
        return None if fetch else 0
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params or ())
        
        if fetch and query.strip().upper().startswith('SELECT'):
            result = cur.fetchall()
        else:
            conn.commit()
            result = cur.rowcount
        
        cur.close()
        conn.close()
        return result
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        print(f"   Запрос: {query[:100]}...")
        if params:
            print(f"   Параметры: {params}")
        conn.rollback()
        return None if fetch else 0
    finally:
        if conn:
            conn.close()

# ========== ОСНОВНЫЕ МАРШРУТЫ ==========
@app.route('/')
def index():
    try:
        cars = execute_query(
            'SELECT * FROM cars WHERE is_available = TRUE ORDER BY id LIMIT 3'
        ) or []
        
        print(f"🔍 Найдено автомобилей на главной: {len(cars)}")
        
        stats = execute_query('SELECT COUNT(*) as count FROM cars')
        total_cars = stats[0]['count'] if stats else 0
        
        stats_users = execute_query('SELECT COUNT(*) as count FROM users')
        total_users = stats_users[0]['count'] if stats_users else 0
        
        return render_template('index.html',
                             cars=cars,
                             test_cars_count=total_cars,
                             total_users=total_users)
    except Exception as e:
        print(f"❌ Ошибка в главной странице: {e}")
        return render_template('index.html', cars=[], test_cars_count=0, total_users=0)

@app.route('/cars')
def cars():
    car_class = request.args.get('class', 'all')
    transmission = request.args.get('transmission', 'all')
    fuel_type = request.args.get('fuel_type', 'all')
    
    try:
        query = 'SELECT * FROM cars WHERE is_available = TRUE'
        params = []
        
        if car_class != 'all':
            query += ' AND car_class = %s'
            params.append(car_class)
        
        if transmission != 'all':
            query += ' AND transmission = %s'
            params.append(transmission)
        
        if fuel_type != 'all':
            query += ' AND fuel_type = %s'
            params.append(fuel_type)
        
        cars = execute_query(query, params) or []
        print(f"🔍 Найдено автомобилей: {len(cars)}")
        
        # Получаем уникальные значения для фильтров
        car_classes_result = execute_query("SELECT DISTINCT car_class FROM cars WHERE car_class IS NOT NULL")
        car_classes = [r['car_class'] for r in car_classes_result] if car_classes_result else ['Эконом', 'Комфорт', 'Премиум']
        
        transmissions_result = execute_query("SELECT DISTINCT transmission FROM cars WHERE transmission IS NOT NULL")
        transmissions = [r['transmission'] for r in transmissions_result] if transmissions_result else ['Автомат', 'Механика']
        
        fuel_types_result = execute_query("SELECT DISTINCT fuel_type FROM cars WHERE fuel_type IS NOT NULL")
        fuel_types = [r['fuel_type'] for r in fuel_types_result] if fuel_types_result else ['Бензин', 'Дизель', 'Электричество', 'Гибрид']
        
        stats = execute_query('SELECT COUNT(*) as count FROM cars')
        total_cars = stats[0]['count'] if stats else 0
        
        return render_template('cars.html',
                             cars=cars,
                             car_classes=car_classes,
                             transmissions=transmissions,
                             fuel_types=fuel_types,
                             selected_class=car_class,
                             selected_transmission=transmission,
                             selected_fuel_type=fuel_type,
                             test_cars_count=total_cars)
    except Exception as e:
        print(f"❌ Ошибка в странице автомобилей: {e}")
        return render_template('cars.html', cars=[], car_classes=[], transmissions=[],
                             fuel_types=[], test_cars_count=0)

@app.route('/car/<int:car_id>')
@login_required
def car_detail(car_id):
    try:
        car = execute_query('SELECT * FROM cars WHERE id = %s', (car_id,))
        if not car:
            flash('Автомобиль не найден', 'danger')
            return redirect(url_for('cars'))
        
        car = car[0]
        
        # Похожие автомобили
        similar_cars = execute_query('''
            SELECT * FROM cars 
            WHERE car_class = %s AND id != %s AND is_available = TRUE 
            LIMIT 3
        ''', (car['car_class'], car_id)) or []
        
        return render_template('booking.html', car=car, similar_cars=similar_cars)
    except Exception as e:
        print(f"❌ Ошибка в деталях автомобиля: {e}")
        flash('Ошибка при загрузке данных автомобиля', 'danger')
        return redirect(url_for('cars'))

@app.route('/book', methods=['POST'])
@login_required
def book_car():
    try:
        car_id = int(request.form['car_id'])
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        
        # Получаем автомобиль
        car = execute_query('SELECT * FROM cars WHERE id = %s', (car_id,))
        if not car:
            return jsonify({'success': False, 'message': 'Автомобиль не найден'})
        
        car = car[0]
        
        # Проверяем доступность
        conflicting = execute_query('''
            SELECT id FROM bookings 
            WHERE car_id = %s AND status = 'active' 
            AND (start_date <= %s AND end_date >= %s) 
            OR (start_date <= %s AND end_date >= %s)
        ''', (car_id, end_date, start_date, start_date, end_date))
        
        if conflicting:
            return jsonify({'success': False, 'message': 'Автомобиль уже забронирован на эти даты'})
        
        # Расчет стоимости
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        days = (end - start).days
        total_price = float(car['daily_price']) * days
        
        # Создаем бронирование
        result = execute_query('''
            INSERT INTO bookings (user_id, car_id, start_date, end_date, total_price)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        ''', (current_user.id, car_id, start_date, end_date, total_price), fetch=True)
        
        if result:
            return jsonify({
                'success': True,
                'message': f'Бронирование успешно создано! Стоимость: {total_price} ₽ за {days} дней.'
            })
        else:
            return jsonify({'success': False, 'message': 'Ошибка при создании бронирования'})
            
    except Exception as e:
        print(f"❌ Ошибка бронирования: {e}")
        return jsonify({'success': False, 'message': f'Произошла ошибка: {str(e)}'})

@app.route('/profile')
@login_required
def profile():
    try:
        bookings = execute_query('''
            SELECT b.*, c.brand, c.model, c.image_url
            FROM bookings b
            JOIN cars c ON b.car_id = c.id
            WHERE b.user_id = %s
            ORDER BY b.created_at DESC
        ''', (current_user.id,)) or []
        
        return render_template('profile.html', bookings=bookings)
    except Exception as e:
        print(f"❌ Ошибка в профиле: {e}")
        return render_template('profile.html', bookings=[])

@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    try:
        result = execute_query('''
            UPDATE bookings SET status = 'cancelled'
            WHERE id = %s AND user_id = %s AND status = 'active'
        ''', (booking_id, current_user.id), fetch=False)
        
        if result and result > 0:
            flash('Бронирование успешно отменено', 'success')
        else:
            flash('Бронирование не найдено или уже отменено', 'danger')
            
    except Exception as e:
        flash(f'Ошибка при отмене бронирования: {str(e)}', 'danger')
    
    return redirect(url_for('profile'))

# ========== АУТЕНТИФИКАЦИЯ ==========
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        phone = request.form.get('phone', '')
        driver_license = request.form.get('driver_license', '')
        
        # Проверяем существующего пользователя
        existing = execute_query(
            'SELECT id FROM users WHERE username = %s OR email = %s',
            (username, email)
        )
        
        if existing:
            flash('Пользователь с таким именем или email уже существует', 'danger')
            return redirect(url_for('register'))
        
        try:
            # Создаем нового пользователя
            password_hash = generate_password_hash(password)
            result = execute_query(
                '''
                INSERT INTO users (username, email, password_hash, phone, driver_license)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
                ''',
                (username, email, password_hash, phone, driver_license),
                fetch=True
            )
            
            if result:
                flash('Регистрация прошла успешно! Теперь вы можете войти в систему.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Ошибка при регистрации', 'danger')
                
        except Exception as e:
            flash(f'Ошибка при регистрации: {str(e)}', 'danger')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            user_data = execute_query(
                'SELECT * FROM users WHERE username = %s',
                (username,)
            )
            
            if user_data and len(user_data) > 0:
                user_data = user_data[0]
                if check_password_hash(user_data['password_hash'], password):
                    user = User(
                        user_data['id'],
                        user_data['username'],
                        user_data['email'],
                        user_data['password_hash'],
                        user_data['is_admin'],
                        user_data['phone'],
                        user_data['driver_license']
                    )
                    login_user(user)
                    
                    if user.is_admin:
                        flash('Вы успешно вошли в систему как администратор!', 'success')
                    else:
                        flash(f'Вы успешно вошли в систему! Добро пожаловать, {user.username}!', 'success')
                    
                    return redirect(url_for('index'))
            
            flash('Неверное имя пользователя или пароль', 'danger')
            
        except Exception as e:
            flash(f'Ошибка при входе: {str(e)}', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы. Ждем вас снова!', 'info')
    return redirect(url_for('index'))

# ========== ДОПОЛНИТЕЛЬНЫЕ СТРАНИЦЫ ==========
@app.route('/contacts')
def contacts():
    return render_template('contacts.html')

@app.route('/about')
def about():
    return render_template('about.html')

# ========== АДМИН ПАНЕЛЬ ==========
@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    try:
        stats_cars = execute_query('SELECT COUNT(*) as count FROM cars')
        stats_users = execute_query('SELECT COUNT(*) as count FROM users')
        stats_bookings = execute_query("SELECT COUNT(*) as count FROM bookings WHERE status = 'active'")
        stats_revenue = execute_query("SELECT COALESCE(SUM(total_price), 0) as total FROM bookings WHERE status = 'active'")
        
        all_cars = execute_query('SELECT * FROM cars ORDER BY id') or []
        
        return render_template('admin.html',
                             total_cars=stats_cars[0]['count'] if stats_cars else 0,
                             total_users=stats_users[0]['count'] if stats_users else 0,
                             active_bookings=stats_bookings[0]['count'] if stats_bookings else 0,
                             total_revenue=stats_revenue[0]['total'] if stats_revenue else 0,
                             all_cars=all_cars)
    except Exception as e:
        print(f"❌ Ошибка админ панели: {e}")
        return render_template('admin.html',
                             total_cars=0, total_users=0, active_bookings=0, total_revenue=0,
                             all_cars=[])

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    try:
        users = execute_query('SELECT * FROM users ORDER BY created_at DESC') or []
        
        # Статистика
        admin_count = execute_query("SELECT COUNT(*) as count FROM users WHERE is_admin = TRUE")
        user_count = execute_query("SELECT COUNT(*) as count FROM users WHERE is_admin = FALSE")
        
        # Все бронирования
        all_bookings = execute_query('''
            SELECT b.*, u.username, u.email, c.brand, c.model, c.image_url 
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN cars c ON b.car_id = c.id
            ORDER BY b.created_at DESC
        ''') or []
        
        return render_template('admin_users.html',
                             users=users,
                             admin_count=admin_count[0]['count'] if admin_count else 0,
                             user_count=user_count[0]['count'] if user_count else 0,
                             bookings_db=all_bookings)
    except Exception as e:
        print(f"❌ Ошибка страницы пользователей: {e}")
        return render_template('admin_users.html',
                             users=[], admin_count=0, user_count=0, bookings_db=[])

# ========== API ДЛЯ АДМИНА ==========
@app.route('/admin/get_car/<int:car_id>')
@login_required
def get_car_data(car_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    car = execute_query('SELECT * FROM cars WHERE id = %s', (car_id,))
    if car:
        return jsonify({'success': True, 'car': car[0]})
    return jsonify({'success': False, 'message': 'Автомобиль не найден'})

@app.route('/admin/update_car/<int:car_id>', methods=['POST'])
@login_required
def update_car(car_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.form
        features_str = data.get('features', '')
        features = [f.strip() for f in features_str.split(',') if f.strip()] if features_str else []
        
        result = execute_query('''
            UPDATE cars SET
                brand = %s, model = %s, year = %s, daily_price = %s,
                car_class = %s, fuel_type = %s, transmission = %s,
                color = %s, seats = %s, location = %s, description = %s,
                image_url = %s, engine = %s, consumption = %s, features = %s
            WHERE id = %s
        ''', (
            data.get('brand'), data.get('model'), data.get('year'), data.get('daily_price'),
            data.get('car_class'), data.get('fuel_type'), data.get('transmission'),
            data.get('color'), data.get('seats'), data.get('location'), data.get('description'),
            data.get('image_url'), data.get('engine'), data.get('consumption'), features, car_id
        ), fetch=False)
        
        if result:
            return jsonify({'success': True, 'message': 'Автомобиль обновлен'})
        return jsonify({'success': False, 'message': 'Ошибка обновления'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/add_car', methods=['POST'])
@login_required
def add_car():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.form
        
        if not data.get('brand') or not data.get('model'):
            return jsonify({'success': False, 'message': 'Заполните марку и модель'})
        
        if not data.get('image_url'):
            return jsonify({'success': False, 'message': 'Укажите ссылку на изображение'})
        
        features_str = data.get('features', '')
        features = [f.strip() for f in features_str.split(',') if f.strip()] if features_str else []
        
        result = execute_query('''
            INSERT INTO cars (
                brand, model, year, daily_price, car_class, fuel_type, transmission,
                color, seats, location, description, image_url, engine, consumption, features
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('brand'), data.get('model'), data.get('year'), data.get('daily_price'),
            data.get('car_class'), data.get('fuel_type'), data.get('transmission'),
            data.get('color'), data.get('seats'), data.get('location'), data.get('description'),
            data.get('image_url'), data.get('engine'), data.get('consumption'), features
        ), fetch=True)
        
        if result:
            return jsonify({'success': True, 'message': 'Автомобиль добавлен'})
        return jsonify({'success': False, 'message': 'Ошибка добавления'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/delete_car/<int:car_id>', methods=['POST'])
@login_required
def delete_car(car_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        active_bookings = execute_query(
            "SELECT COUNT(*) as count FROM bookings WHERE car_id = %s AND status = 'active'",
            (car_id,)
        )
        
        if active_bookings and active_bookings[0]['count'] > 0:
            return jsonify({
                'success': False,
                'message': f'Нельзя удалить автомобиль с активными бронированиями ({active_bookings[0]["count"]})'
            })
        
        result = execute_query('DELETE FROM cars WHERE id = %s', (car_id,), fetch=False)
        
        if result:
            return jsonify({'success': True, 'message': 'Автомобиль удален'})
        return jsonify({'success': False, 'message': 'Ошибка удаления'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/toggle_car/<int:car_id>', methods=['POST'])
@login_required
def toggle_car(car_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        car = execute_query('SELECT is_available FROM cars WHERE id = %s', (car_id,))
        if not car:
            return jsonify({'success': False, 'message': 'Автомобиль не найден'})
        
        new_status = not car[0]['is_available']
        
        result = execute_query(
            'UPDATE cars SET is_available = %s WHERE id = %s',
            (new_status, car_id),
            fetch=False
        )
        
        if result:
            status_text = "доступен" if new_status else "недоступен"
            return jsonify({'success': True, 'message': f'Автомобиль теперь {status_text}'})
        return jsonify({'success': False, 'message': 'Ошибка обновления'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ========== ОБРАБОТЧИК ОШИБОК ==========
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

# ========== ЗАПУСК ПРИЛОЖЕНИЯ ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print("=" * 60)
    print("🌐 Приложение запущено")
    print("=" * 60)
    print(f"🔑 Администратор: admin / admin123")
    print(f"👤 Тестовый пользователь: user / user123")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=True)