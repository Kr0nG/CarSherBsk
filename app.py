from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret')

login_manager = LoginManager(app)
login_manager.login_view = 'login'

DB_CONFIG = {
    'dbname': 'carsharing_gg29',
    'user': 'postgre',
    'password': 'CT0s2HSM3WpzFqmnRdWRRjDJriS3PlW4',
    'host': 'dpg-d4vqh2vpm1nc73btsd1g-a.oregon-postgres.render.com',
    'port': '5432'
}


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

# Подключение к базе данных
def get_db():
    return psycopg2.connect(**DB_CONFIG)


# Класс пользователя для Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email, password_hash, is_admin=False, phone=None, license=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.is_admin = is_admin
        self.phone = phone
        self.driver_license = license


# Инициализация базы данных при запуске
def init_db():
    with get_db() as conn, conn.cursor() as cur:
        # Создание таблицы пользователей
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

        # Создание таблицы автомобилей
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

        # Создание таблицы бронирований
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

        # Создание администратора по умолчанию
        cur.execute("SELECT id FROM users WHERE username = 'Denis'")
        if not cur.fetchone():
            cur.execute('INSERT INTO users (username, email, password_hash, is_admin) VALUES (%s, %s, %s, %s)',
                        ('Denis', 'Denis@carsharebsk.ru', generate_password_hash('Denis123'), True))
        conn.commit()


# Загрузка тестовых автомобилей при первом запуске
def load_test_data():
    with get_db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT COUNT(*) as count FROM cars')
        if cur.fetchone()['count'] == 0:
            cars = [
                ('Hyundai', 'Solaris', 2023, 1200, 'Бензин', 'Автомат', 5, 'ул. Ленина, 123',
                 'https://s.auto.drom.ru/i24206/c/photos/fullsize/hyundai/solaris/hyundai_solaris_677323.jpg',
                 True, 'Белый', 'Экономичный городской автомобиль', 'Эконом',
                 ['Кондиционер', 'Bluetooth', 'Парктроники'], '1.6L', '6.5 л/100км'),
                ('Toyota', 'Camry', 2023, 2500, 'Бензин', 'Автомат', 5, 'пр. Ленина, 89',
                 'https://iat.ru/uploads/origin/models/737981/1.webp', True, 'Черный',
                 'Комфортабельный седан для бизнес-поездок', 'Комфорт',
                 ['Климат-контроль', 'Кожаный салон', 'Камера заднего вида'], '2.5L', '7.8 л/100км'),
                ('BMW', '5 Series', 2023, 4500, 'Бензин', 'Автомат', 5, 'пр. Коммунарский, 156',
                 'https://www.thedrive.com/wp-content/uploads/2024/10/tgI7q.jpg?w=1819&h=1023',
                 True, 'Черный', 'Представительский седан бизнес-класса', 'Премиум',
                 ['Память сидений', 'Массаж сидений', 'Адаптивный круиз'], '3.0L', '8.5 л/100км')
            ]
            for car in cars:
                cur.execute('''
                    INSERT INTO cars (brand, model, year, daily_price, fuel_type, transmission,
                                    seats, location, image_url, is_available, color, description,
                                    car_class, features, engine, consumption)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', car)
            conn.commit()
            print("✅ Тестовые автомобили загружены")


# Загрузка пользователя для Flask-Login
@login_manager.user_loader
def load_user(user_id):
    with get_db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        data = cur.fetchone()
        if data:
            return User(str(data['id']), data['username'], data['email'],
                        data['password_hash'], data['is_admin'], data['phone'], data['driver_license'])
    return None


# ========== АУТЕНТИФИКАЦИЯ ==========

# Регистрация нового пользователя
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = request.form
        if data['password'] != data['confirm_password']:
            flash('Пароли не совпадают', 'danger')
            return redirect(url_for('register'))

        try:
            with get_db() as conn, conn.cursor() as cur:
                cur.execute('SELECT id FROM users WHERE username = %s OR email = %s', (data['username'], data['email']))
                if cur.fetchone():
                    flash('Пользователь уже существует', 'danger')
                    return redirect(url_for('register'))

                cur.execute(
                    'INSERT INTO users (username, email, password_hash, phone, driver_license) VALUES (%s, %s, %s, %s, %s)',
                    (data['username'], data['email'], generate_password_hash(data['password']), data['phone'],
                     data['driver_license']))
                conn.commit()
                flash('Регистрация успешна!', 'success')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'danger')

    return render_template('register.html')


# Вход в систему
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with get_db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT * FROM users WHERE username = %s', (username,))
            data = cur.fetchone()

            if data and check_password_hash(data['password_hash'], password):
                user = User(str(data['id']), data['username'], data['email'],
                            data['password_hash'], data['is_admin'], data['phone'], data['driver_license'])
                login_user(user)
                flash(f'Добро пожаловать, {user.username}!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Неверные данные', 'danger')

    return render_template('login.html')


# Выход из системы
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


# ========== ОСНОВНЫЕ МАРШРУТЫ ==========

# Главная страница с популярными автомобилями
@app.route('/')
def index():
    with get_db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Три самых популярных автомобиля по количеству бронирований
        cur.execute('''
            SELECT c.*, COUNT(b.id) as booking_count
            FROM cars c LEFT JOIN bookings b ON c.id = b.car_id
            WHERE c.is_available = TRUE
            GROUP BY c.id ORDER BY booking_count DESC LIMIT 3
        ''')
        popular_cars = cur.fetchall()

        cur.execute('SELECT COUNT(*) as count FROM cars')
        total_cars = cur.fetchone()['count']

        cur.execute('SELECT COUNT(*) as count FROM users')
        total_users = cur.fetchone()['count']

        return render_template('index.html', cars=popular_cars, test_cars_count=total_cars, total_users=total_users)


# Страница всех автомобилей с фильтрами
@app.route('/cars')
def cars():
    car_class = request.args.get('class', 'all')
    transmission = request.args.get('transmission', 'all')
    fuel_type = request.args.get('fuel_type', 'all')

    with get_db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
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

        cur.execute(query, params)
        filtered_cars = cur.fetchall()

        cur.execute("SELECT DISTINCT car_class FROM cars WHERE car_class IS NOT NULL")
        car_classes = [r['car_class'] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT transmission FROM cars")
        transmissions = [r['transmission'] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT fuel_type FROM cars")
        fuel_types = [r['fuel_type'] for r in cur.fetchall()]

        return render_template('cars.html', cars=filtered_cars, car_classes=car_classes,
                               transmissions=transmissions, fuel_types=fuel_types,
                               selected_class=car_class, selected_transmission=transmission,
                               selected_fuel_type=fuel_type)


# Страница деталей автомобиля для бронирования
@app.route('/car/<int:car_id>')
@login_required
def car_detail(car_id):
    with get_db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT * FROM cars WHERE id = %s', (car_id,))
        car = cur.fetchone()
        if not car:
            flash('Автомобиль не найден', 'danger')
            return redirect(url_for('cars'))

        cur.execute('SELECT * FROM cars WHERE car_class = %s AND id != %s LIMIT 3', (car['car_class'], car_id))
        similar = cur.fetchall()
        return render_template('booking.html', car=car, similar_cars=similar)


# ========== СОЗДАНИЕ БРОНИРОВАНИЯ АВТОМОБИЛЯ ==========
@app.route('/book', methods=['POST'])
@login_required
def book_car():
    try:
        car_id = int(request.form['car_id'])
        start = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        today = datetime.now().date()

        # Проверка корректности дат
        if start < today:
            return jsonify({'success': False, 'message': 'Дата начала не может быть в прошлом'})
        if end < start:
            return jsonify({'success': False, 'message': 'Дата окончания не может быть раньше даты начала'})
        if start == end:
            return jsonify({'success': False, 'message': 'Минимальный срок аренды - 1 день'})

        with get_db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Проверка доступности автомобиля
            cur.execute('SELECT * FROM cars WHERE id = %s', (car_id,))
            car = cur.fetchone()
            if not car or not car['is_available']:
                return jsonify({'success': False, 'message': 'Автомобиль временно недоступен'})

            # Проверка пересечений бронирований
            cur.execute('''
                SELECT id FROM bookings 
                WHERE car_id = %s AND status = 'active' 
                AND (start_date <= %s AND end_date >= %s)
            ''', (car_id, end, start))

            if cur.fetchone():
                return jsonify({'success': False, 'message': 'Автомобиль уже забронирован на эти даты'})

            # Расчет стоимости и создание бронирования
            days = (end - start).days
            price = float(car['daily_price']) * days

            cur.execute('''
                INSERT INTO bookings (user_id, car_id, start_date, end_date, total_price)
                VALUES (%s, %s, %s, %s, %s)
            ''', (current_user.id, car_id, start, end, price))
            conn.commit()

            return jsonify({'success': True, 'message': f'Бронирование создано! Стоимость: {price} ₽ за {days} дней.'})
    except:
        return jsonify({'success': False, 'message': 'Ошибка при бронировании'})


# Личный кабинет пользователя с историей бронирований
@app.route('/profile')
@login_required
def profile():
    with get_db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            'SELECT b.*, c.brand, c.model, c.image_url FROM bookings b JOIN cars c ON b.car_id = c.id WHERE b.user_id = %s ORDER BY b.created_at DESC',
            (current_user.id,))
        return render_template('profile.html', bookings=cur.fetchall())


# Отмена бронирования пользователем
@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    with get_db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE bookings SET status = 'cancelled' WHERE id = %s AND user_id = %s",
                    (booking_id, current_user.id))
        conn.commit()
        flash('Бронь отменена', 'success')
    return redirect(url_for('profile'))


# Страница контактов
@app.route('/contacts')
def contacts():
    return render_template('contacts.html')


# Страница "О нас"
@app.route('/about')
def about():
    return render_template('about.html')


# ========== АДМИНИСТРАТОР ==========

# Декоратор для проверки прав администратора
def admin_required(f):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Доступ запрещен', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


# Панель администратора со статистикой
@app.route('/admin')
@login_required
@admin_required
def admin():
    with get_db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT COUNT(*) as count FROM cars')
        total_cars = cur.fetchone()['count']
        cur.execute('SELECT COUNT(*) as count FROM users')
        total_users = cur.fetchone()['count']
        cur.execute("SELECT COUNT(*) as count FROM bookings WHERE status = 'active'")
        active = cur.fetchone()['count']
        cur.execute("SELECT COALESCE(SUM(total_price), 0) as total FROM bookings WHERE status = 'active'")
        revenue = cur.fetchone()['total']
        cur.execute('SELECT * FROM cars ORDER BY id')
        cars = cur.fetchall()

        return render_template('admin.html', total_cars=total_cars, total_users=total_users,
                               active_bookings=active, total_revenue=revenue, all_cars=cars)


# Получение данных автомобиля для редактирования
@app.route('/admin/get_car/<int:car_id>')
@login_required
@admin_required
def get_car_data(car_id):
    with get_db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT * FROM cars WHERE id = %s', (car_id,))
        car = cur.fetchone()
        return jsonify({'success': bool(car), 'car': car})


# Обновление данных автомобиля
@app.route('/admin/update_car/<int:car_id>', methods=['POST'])
@login_required
@admin_required
def update_car(car_id):
    with get_db() as conn, conn.cursor() as cur:
        data = request.form

        features_str = data.get('features', '')
        features = [f.strip() for f in features_str.split(',') if f.strip()]

        update_query = '''
            UPDATE cars SET 
                brand = COALESCE(%s, brand),
                model = COALESCE(%s, model),
                year = COALESCE(%s, year),
                daily_price = COALESCE(%s, daily_price),
                car_class = COALESCE(%s, car_class),
                fuel_type = COALESCE(%s, fuel_type),
                transmission = COALESCE(%s, transmission),
                color = COALESCE(%s, color),
                seats = COALESCE(%s, seats),
                location = COALESCE(%s, location),
                description = COALESCE(%s, description),
                image_url = COALESCE(%s, image_url),
                engine = COALESCE(%s, engine),
                consumption = COALESCE(%s, consumption),
                features = COALESCE(%s, features)
            WHERE id = %s
        '''

        cur.execute(update_query, (
            data.get('brand'), data.get('model'), data.get('year'),
            data.get('daily_price'), data.get('car_class'),
            data.get('fuel_type'), data.get('transmission'),
            data.get('color'), data.get('seats'), data.get('location'),
            data.get('description'), data.get('image_url'),
            data.get('engine'), data.get('consumption'),
            features if features else None, car_id
        ))

        conn.commit()
        return jsonify({'success': True, 'message': 'Автомобиль обновлен'})


# Удаление автомобиля
@app.route('/admin/delete_car/<int:car_id>', methods=['POST'])
@login_required
@admin_required
def delete_car(car_id):
    with get_db() as conn, conn.cursor() as cur:
        cur.execute('SELECT brand, model FROM cars WHERE id = %s', (car_id,))
        car = cur.fetchone()
        if not car:
            return jsonify({'success': False, 'message': 'Автомобиль не найден'})

        cur.execute("SELECT COUNT(*) FROM bookings WHERE car_id = %s AND status = 'active'", (car_id,))
        if cur.fetchone()[0] > 0:
            return jsonify({'success': False, 'message': 'Есть активные брони'})

        cur.execute('DELETE FROM bookings WHERE car_id = %s', (car_id,))
        cur.execute('DELETE FROM cars WHERE id = %s', (car_id,))
        conn.commit()
        return jsonify({'success': True, 'message': f'Автомобиль {car[0]} {car[1]} удален'})


# Добавление нового автомобиля
@app.route('/admin/add_car', methods=['POST'])
@login_required
@admin_required
def add_car():
    data = request.form
    if not data.get('image_url'):
        return jsonify({'success': False, 'message': 'Нужна ссылка на фото'})

    features_str = data.get('features', '')
    features = [f.strip() for f in features_str.split(',') if f.strip()]

    with get_db() as conn, conn.cursor() as cur:
        cur.execute('''
            INSERT INTO cars (brand, model, year, daily_price, car_class, fuel_type, 
                            transmission, image_url, location, color, seats, description,
                            engine, consumption, features)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data['brand'], data['model'], int(data['year']), float(data['daily_price']),
            data['car_class'], data['fuel_type'], data['transmission'], data['image_url'],
            data.get('location', 'ул. Ленина, 123'), data.get('color', 'синий'),
            int(data.get('seats', 5)), data.get('description', f'Новый {data["brand"]} {data["model"]}'),
            data.get('engine', ''), data.get('consumption', ''), features if features else None
        ))
        conn.commit()
        return jsonify({'success': True, 'message': f'Автомобиль {data["brand"]} {data["model"]} добавлен'})


# Переключение доступности автомобиля
@app.route('/admin/toggle_car/<int:car_id>', methods=['POST'])
@login_required
@admin_required
def toggle_car(car_id):
    with get_db() as conn, conn.cursor() as cur:
        cur.execute('SELECT brand, model, is_available FROM cars WHERE id = %s', (car_id,))
        car = cur.fetchone()
        if not car:
            return jsonify({'success': False, 'message': 'Автомобиль не найден'})

        new_status = not car[2]
        cur.execute('UPDATE cars SET is_available = %s WHERE id = %s', (new_status, car_id))
        conn.commit()

        status = "доступен" if new_status else "недоступен"
        return jsonify({'success': True, 'message': f'Автомобиль {car[0]} {car[1]} теперь {status}'})


# Управление пользователями (ИСПРАВЛЕННЫЙ ВАРИАНТ)
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    with get_db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT * FROM users ORDER BY created_at DESC')
        users = cur.fetchall()

        # Статистика бронирований по пользователям - ИСПРАВЛЕННЫЙ ЗАПРОС
        user_stats = {}
        cur.execute('''
            SELECT user_id, 
                   COUNT(*) as total,
                   SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active
            FROM bookings 
            GROUP BY user_id
        ''')

        for r in cur.fetchall():
            user_stats[r['user_id']] = {
                'total': r['total'],
                'active': r['active']
            }

        # Все бронирования
        cur.execute('''
            SELECT b.*, u.username, u.email, c.brand, c.model, c.image_url 
            FROM bookings b JOIN users u ON b.user_id = u.id JOIN cars c ON b.car_id = c.id
            ORDER BY b.created_at DESC
        ''')
        bookings = cur.fetchall()

        # ДОБАВЬТЕ ЭТОТ КОД - Подсчет администраторов и пользователей
        cur.execute("SELECT COUNT(*) as count FROM users WHERE is_admin = TRUE")
        admin_count = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) as count FROM users WHERE is_admin = FALSE")
        user_count = cur.fetchone()['count']

        return render_template('admin_users.html',
                               users=users,
                               user_stats=user_stats,
                               bookings_db=bookings,
                               admin_count=admin_count,  # ДОБАВЬТЕ ЭТО
                               user_count=user_count)


# Отмена бронирования администратором
@app.route('/admin/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def admin_cancel_booking(booking_id):
    with get_db() as conn, conn.cursor() as cur:
        cur.execute("UPDATE bookings SET status = 'cancelled' WHERE id = %s", (booking_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Бронирование отменено'})


# Удаление пользователя администратором
@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required

@admin_required
def admin_delete_user(user_id):
    if str(user_id) == current_user.id:
        return jsonify({'success': False, 'message': 'Нельзя удалить свой аккаунт'})

    with get_db() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT username, is_admin FROM users WHERE id = %s', (user_id,))
        user = cur.fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'Пользователь не найден'})

        cur.execute('DELETE FROM bookings WHERE user_id = %s', (user_id,))
        cur.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()

        user_type = "администратора" if user['is_admin'] else "пользователя"
        return jsonify({'success': True, 'message': f'{user_type} {user["username"]} удален'})


# ========== ОБРАБОТКА ОШИБОК И ЗАПУСК ==========

# Обработка ошибки 404
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


# Запуск приложения
if __name__ == '__main__':
    print("🚀 Сервис каршеринга запущен")
    print("🌐 http://localhost:5001")
    print("🔑 admin / admin123")

    init_db()
    load_test_data()
    app.run(debug=True, port=5001)