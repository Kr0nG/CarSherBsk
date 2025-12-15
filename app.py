from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-change-me')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Конфигурация PostgreSQL из переменных окружения
DB_CONFIG = {
    'dbname': 'carsharing_gg29',
    'user': 'postgre',
    'password': 'CT0s2HSM3WpzFqmnRdWRRjDJriS3PlW4',
    'host': 'dpg-d4vqh2vpm1nc73btsd1g-a.oregon-postgres.render.com',
    'port': '5432'

}

# Флаг для отслеживания загрузки тестовых данных
TEST_DATA_LOADED = False


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


class User(UserMixin):
    def __init__(self, id, username, email, password_hash, is_admin=False, phone=None, driver_license=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.is_admin = is_admin
        self.phone = phone
        self.driver_license = driver_license

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Создаем таблицы если они не существуют
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
                range_info VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

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

        # Проверяем, есть ли администратор
        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cur.fetchone():
            password_hash = generate_password_hash('admin123')
            cur.execute('''
                INSERT INTO users (username, email, password_hash, is_admin)
                VALUES (%s, %s, %s, %s)
            ''', ('admin', 'admin@carsharebsk.ru', password_hash, True))

        conn.commit()
        cur.close()
        conn.close()
        print("✅ База данных инициализирована успешно!")

    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")


def load_test_data_once():
    """Загружает тестовые данные только один раз"""
    global TEST_DATA_LOADED

    if TEST_DATA_LOADED:
        return

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Проверяем, есть ли уже автомобили
        cur.execute('SELECT COUNT(*) as count FROM cars')
        count = cur.fetchone()['count']

        if count == 0:
            print("📥 Загрузка 3 тестовых автомобилей в базу данных...")

            test_cars = [
                {
                    'brand': 'Hyundai',
                    'model': 'Solaris',
                    'year': 2023,
                    'daily_price': 1200,
                    'fuel_type': 'Бензин',
                    'transmission': 'Автомат',
                    'seats': 5,
                    'location': 'ул. Ленина, 123',
                    'image_url': 'https://s.auto.drom.ru/i24206/c/photos/fullsize/hyundai/solaris/hyundai_solaris_677323.jpg',
                    'is_available': True,
                    'color': 'Белый',
                    'description': 'Экономичный городской автомобиль с низким расходом топлива.',
                    'car_class': 'Эконом',
                    'features': ['Кондиционер', 'Bluetooth', 'Парктроники', 'Камера заднего вида'],
                    'engine': '1.6L',
                    'consumption': '6.5 л/100км'
                },
                {
                    'brand': 'Toyota',
                    'model': 'Camry',
                    'year': 2023,
                    'daily_price': 2500,
                    'fuel_type': 'Бензин',
                    'transmission': 'Автомат',
                    'seats': 5,
                    'location': 'пр. Ленина, 89',
                    'image_url': 'https://iat.ru/uploads/origin/models/737981/1.webp',
                    'is_available': True,
                    'color': 'Черный',
                    'description': 'Комфортабельный седан для бизнес-поездок.',
                    'car_class': 'Комфорт',
                    'features': ['Климат-контроль', 'Кожаный салон', 'Камера заднего вида', 'Паркинг-ассистент'],
                    'engine': '2.5L',
                    'consumption': '7.8 л/100км'
                },
                {
                    'brand': 'BMW',
                    'model': '5 Series',
                    'year': 2023,
                    'daily_price': 4500,
                    'fuel_type': 'Бензин',
                    'transmission': 'Автомат',
                    'seats': 5,
                    'location': 'пр. Коммунарский, 156',
                    'image_url': 'https://www.thedrive.com/wp-content/uploads/2024/10/tgI7q.jpg?w=1819&h=1023',
                    'is_available': True,
                    'color': 'Черный',
                    'description': 'Представительский седан бизнес-класса.',
                    'car_class': 'Премиум',
                    'features': ['Память сидений', 'Массаж сидений', 'Адаптивный круиз', 'Проекционный дисплей'],
                    'engine': '3.0L',
                    'consumption': '8.5 л/100км'
                }
            ]

            for car in test_cars:
                features_array = car['features']
                cur.execute('''
                    INSERT INTO cars (brand, model, year, daily_price, fuel_type, transmission, 
                                    seats, location, image_url, is_available, color, description, 
                                    car_class, features, engine, consumption)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    car['brand'], car['model'], car['year'], car['daily_price'],
                    car['fuel_type'], car['transmission'], car['seats'], car['location'],
                    car['image_url'], car['is_available'], car['color'], car['description'],
                    car['car_class'], features_array, car['engine'], car['consumption']
                ))

        conn.commit()
        cur.close()
        conn.close()

        TEST_DATA_LOADED = True
        print("✅ Тестовые данные загружены успешно! (3 автомобиля)")

    except Exception as e:
        print(f"❌ Ошибка загрузки тестовых данных: {e}")


@login_manager.user_loader
def load_user(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()

        if user_data:
            return User(
                str(user_data['id']),
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


# Инициализация базы при старте
init_db()
load_test_data_once()


# Маршруты аутентификации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        phone = request.form['phone']
        driver_license = request.form['driver_license']

        # Проверка подтверждения пароля
        if password != confirm_password:
            flash('Пароли не совпадают. Пожалуйста, проверьте введенные пароли.', 'danger')
            return redirect(url_for('register'))

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # Проверка на существующего пользователя
            cur.execute('SELECT id FROM users WHERE username = %s OR email = %s',
                        (username, email))
            if cur.fetchone():
                flash('Пользователь с таким именем или email уже существует', 'danger')
                return redirect(url_for('register'))

            # Создание нового пользователя
            password_hash = generate_password_hash(password)
            cur.execute('''
                INSERT INTO users (username, email, password_hash, phone, driver_license)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            ''', (username, email, password_hash, phone, driver_license))

            user_id = cur.fetchone()[0]
            conn.commit()

            flash('Регистрация прошла успешно! Теперь вы можете войти в систему.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            flash(f'Ошибка при регистрации: {str(e)}', 'danger')
            return redirect(url_for('register'))
        finally:
            cur.close()
            conn.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute('SELECT * FROM users WHERE username = %s', (username,))
            user_data = cur.fetchone()
            cur.close()
            conn.close()

            if user_data and check_password_hash(user_data['password_hash'], password):
                user = User(
                    str(user_data['id']),
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
            else:
                flash('Неверное имя пользователя или пароль. Пожалуйста, проверьте введенные данные.', 'danger')

        except Exception as e:
            flash(f'Ошибка при входе: {str(e)}', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы. Ждем вас снова!', 'info')
    return redirect(url_for('index'))


# Основные маршруты
@app.route('/')
def index():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Получаем 3 автомобиля
        cur.execute('SELECT * FROM cars WHERE is_available = TRUE ORDER BY id LIMIT 3')
        cars = cur.fetchall()

        # Считаем общее количество автомобилей
        cur.execute('SELECT COUNT(*) as count FROM cars')
        total_cars = cur.fetchone()['count']

        # Считаем общее количество пользователей
        cur.execute('SELECT COUNT(*) as count FROM users')
        total_users = cur.fetchone()['count']

        cur.close()
        conn.close()

        return render_template('index.html',
                               cars=cars,
                               test_cars_count=total_cars,
                               total_users=total_users)
    except Exception as e:
        print(f"Ошибка в главной странице: {e}")
        return render_template('index.html', cars=[], test_cars_count=0, total_users=0)


@app.route('/cars')
def cars():
    car_class = request.args.get('class', 'all')
    transmission = request.args.get('transmission', 'all')
    fuel_type = request.args.get('fuel_type', 'all')

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Базовый запрос
        query = 'SELECT * FROM cars WHERE is_available = TRUE'
        params = []

        if car_class and car_class != 'all':
            query += ' AND car_class = %s'
            params.append(car_class)

        if transmission and transmission != 'all':
            query += ' AND transmission = %s'
            params.append(transmission)

        if fuel_type and fuel_type != 'all':
            query += ' AND fuel_type = %s'
            params.append(fuel_type)

        cur.execute(query, params)
        filtered_cars = cur.fetchall()

        # Получаем уникальные значения для фильтров
        cur.execute("SELECT DISTINCT car_class FROM cars WHERE car_class IS NOT NULL")
        car_classes = [row['car_class'] for row in cur.fetchall()]

        cur.execute("SELECT DISTINCT transmission FROM cars WHERE transmission IS NOT NULL")
        transmissions = [row['transmission'] for row in cur.fetchall()]

        cur.execute("SELECT DISTINCT fuel_type FROM cars WHERE fuel_type IS NOT NULL")
        fuel_types = [row['fuel_type'] for row in cur.fetchall()]

        # Общее количество автомобилей
        cur.execute('SELECT COUNT(*) as count FROM cars')
        total_cars = cur.fetchone()['count']

        cur.close()
        conn.close()

        return render_template('cars.html',
                               cars=filtered_cars,
                               car_classes=car_classes,
                               transmissions=transmissions,
                               fuel_types=fuel_types,
                               selected_class=car_class,
                               selected_transmission=transmission,
                               selected_fuel_type=fuel_type,
                               test_cars_count=total_cars)
    except Exception as e:
        print(f"Ошибка в странице автомобилей: {e}")
        return render_template('cars.html', cars=[], car_classes=[], transmissions=[],
                               fuel_types=[], test_cars_count=0)


@app.route('/car/<int:car_id>')
@login_required
def car_detail(car_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute('SELECT * FROM cars WHERE id = %s', (car_id,))
        car = cur.fetchone()

        if not car:
            flash('Автомобиль не найден. Пожалуйста, выберите другой автомобиль из нашего каталога.', 'danger')
            return redirect(url_for('cars'))

        # Похожие автомобили
        cur.execute('''
            SELECT * FROM cars 
            WHERE car_class = %s AND id != %s AND is_available = TRUE 
            LIMIT 3
        ''', (car['car_class'], car_id))
        similar_cars = cur.fetchall()

        cur.close()
        conn.close()

        return render_template('booking.html', car=car, similar_cars=similar_cars)
    except Exception as e:
        print(f"Ошибка в деталях автомобиля: {e}")
        flash('Ошибка при загрузке данных автомобиля', 'danger')
        return redirect(url_for('cars'))


@app.route('/book', methods=['POST'])
@login_required
def book_car():
    try:
        car_id = int(request.form['car_id'])
        start_date_str = request.form['start_date']
        end_date_str = request.form['end_date']

        # Валидация дат
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        today = datetime.now().date()

        # Проверка корректности дат
        if start_date < today:
            return jsonify({'success': False,
                            'message': 'Дата начала не может быть в прошлом. Пожалуйста, выберите корректную дату.'})

        if end_date < start_date:
            return jsonify({'success': False,
                            'message': 'Дата окончания не может быть раньше даты начала. Пожалуйста, проверьте выбранные даты.'})

        if start_date == end_date:
            return jsonify({'success': False,
                            'message': 'Минимальный срок аренды - 1 день. Пожалуйста, выберите период хотя бы на один день.'})

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Проверка доступности автомобиля
        cur.execute('SELECT * FROM cars WHERE id = %s', (car_id,))
        car = cur.fetchone()

        if not car:
            return jsonify({'success': False,
                            'message': 'Автомобиль не найден. Пожалуйста, обновите страницу и попробуйте снова.'})

        if not car['is_available']:
            return jsonify({'success': False,
                            'message': 'Автомобиль временно недоступен для бронирования. Пожалуйста, выберите другой автомобиль.'})

        # Проверка пересечений бронирований
        cur.execute('''
            SELECT id FROM bookings 
            WHERE car_id = %s AND status = 'active' 
            AND ((start_date <= %s AND end_date >= %s) 
            OR (start_date <= %s AND end_date >= %s))
        ''', (car_id, start_date, start_date, end_date, end_date))

        if cur.fetchone():
            return jsonify({'success': False,
                            'message': 'Автомобиль уже забронирован на выбранные даты. Пожалуйста, выберите другие даты или другой автомобиль.'})

        # Расчет стоимости
        days = (end_date - start_date).days
        if days < 1:
            return jsonify({'success': False,
                            'message': 'Минимальный срок аренды - 1 день. Пожалуйста, выберите период хотя бы на один день.'})

        total_price = float(car['daily_price']) * days

        # Создание бронирования
        cur.execute('''
            INSERT INTO bookings (user_id, car_id, start_date, end_date, total_price)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        ''', (current_user.id, car_id, start_date, end_date, total_price))

        booking_id = cur.fetchone()['id']
        conn.commit()

        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Бронирование успешно создано! Стоимость аренды составляет {total_price} ₽ за {days} дней.'
        })

    except ValueError as e:
        return jsonify(
            {'success': False, 'message': 'Неверный формат даты. Пожалуйста, выберите даты в корректном формате.'})
    except Exception as e:
        print(f"Ошибка бронирования: {e}")
        return jsonify({'success': False,
                        'message': f'Произошла ошибка при бронировании: {str(e)}. Пожалуйста, попробуйте еще раз.'})


@app.route('/profile')
@login_required
def profile():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute('''
            SELECT b.*, c.brand, c.model, c.image_url
            FROM bookings b
            JOIN cars c ON b.car_id = c.id
            WHERE b.user_id = %s
            ORDER BY b.created_at DESC
        ''', (current_user.id,))

        bookings = cur.fetchall()
        cur.close()
        conn.close()

        return render_template('profile.html', bookings=bookings)
    except Exception as e:
        print(f"Ошибка в профиле: {e}")
        return render_template('profile.html', bookings=[])


@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute('''
            UPDATE bookings SET status = 'cancelled'
            WHERE id = %s AND user_id = %s AND status = 'active'
        ''', (booking_id, current_user.id))

        if cur.rowcount == 0:
            flash('Бронирование не найдено или у вас нет прав для его отмены.', 'danger')
        else:
            conn.commit()
            flash('Бронирование успешно отменено. Мы надеемся увидеть вас снова!', 'success')

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Ошибка отмены бронирования: {e}")
        flash(f'Произошла ошибка при отмене бронирования: {str(e)}. Пожалуйста, обратитесь в поддержку.', 'danger')

    return redirect(url_for('profile'))


@app.route('/contacts')
def contacts():
    return render_template('contacts.html')


@app.route('/about')
def about():
    return render_template('about.html')


# Админ маршруты
@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Доступ запрещен.', 'danger')
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Статистика
        cur.execute('SELECT COUNT(*) as count FROM cars')
        total_cars = cur.fetchone()['count']

        cur.execute('SELECT COUNT(*) as count FROM users')
        total_users = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) as count FROM bookings WHERE status = 'active'")
        active_bookings = cur.fetchone()['count']

        cur.execute("SELECT COALESCE(SUM(total_price), 0) as total FROM bookings WHERE status = 'active'")
        total_revenue = cur.fetchone()['total']

        # Все автомобили
        cur.execute('SELECT * FROM cars ORDER BY id')
        all_cars = cur.fetchall()

        cur.close()
        conn.close()

        return render_template('admin.html',
                               total_cars=total_cars,
                               total_users=total_users,
                               active_bookings=active_bookings,
                               total_revenue=total_revenue,
                               all_cars=all_cars)
    except Exception as e:
        print(f"Ошибка админ панели: {e}")
        return render_template('admin.html',
                               total_cars=0, total_users=0, active_bookings=0, total_revenue=0,
                               all_cars=[])


# Админ функции для автомобилей
@app.route('/admin/get_car/<int:car_id>', methods=['GET'])
@login_required
def get_car_data(car_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Доступ запрещен'})

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM cars WHERE id = %s', (car_id,))
        car = cur.fetchone()
        cur.close()
        conn.close()

        if not car:
            return jsonify({'success': False, 'message': 'Автомобиль не найден'})

        return jsonify({
            'success': True,
            'car': car
        })
    except Exception as e:
        print(f"Ошибка получения данных автомобиля: {e}")
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})


@app.route('/admin/update_car/<int:car_id>', methods=['POST'])
@login_required
def update_car(car_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Доступ запрещен'})

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Получаем данные из формы
        brand = request.form.get('brand')
        model = request.form.get('model')
        year = request.form.get('year')
        daily_price = request.form.get('daily_price')
        car_class = request.form.get('car_class')
        fuel_type = request.form.get('fuel_type')
        transmission = request.form.get('transmission')
        color = request.form.get('color')
        seats = request.form.get('seats')
        location = request.form.get('location')
        description = request.form.get('description')
        image_url = request.form.get('image_url')
        engine = request.form.get('engine')
        consumption = request.form.get('consumption')
        features_str = request.form.get('features', '')

        # Преобразуем строку особенностей в массив
        features = []
        if features_str:
            # Разделяем по запятым, убираем лишние пробелы и пустые элементы
            features = [f.strip() for f in features_str.split(',') if f.strip()]

        # Обновляем автомобиль
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
            brand, model, year, daily_price, car_class, fuel_type, transmission,
            color, seats, location, description, image_url, engine, consumption,
            features if features else None, car_id
        ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Автомобиль успешно обновлен!'
        })

    except Exception as e:
        print(f"Ошибка обновления автомобиля: {e}")
        return jsonify({'success': False, 'message': f'Ошибка при обновлении: {str(e)}'})


@app.route('/admin/delete_car/<int:car_id>', methods=['POST'])
@login_required
def delete_car(car_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Доступ запрещен'})

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Получаем информацию об автомобиле
        cur.execute('SELECT brand, model FROM cars WHERE id = %s', (car_id,))
        car = cur.fetchone()

        if not car:
            return jsonify({'success': False, 'message': 'Автомобиль не найден'})

        # Проверяем только активные бронирования
        cur.execute("SELECT COUNT(*) FROM bookings WHERE car_id = %s AND status = 'active'", (car_id,))
        active_count = cur.fetchone()[0]

        if active_count > 0:
            return jsonify({
                'success': False,
                'message': f'Невозможно удалить автомобиль с активными бронированиями ({active_count} активных).'
            })

        # Удаляем все бронирования автомобиля
        cur.execute('DELETE FROM bookings WHERE car_id = %s', (car_id,))
        deleted_bookings = cur.rowcount

        # Удаляем автомобиль
        cur.execute('DELETE FROM cars WHERE id = %s', (car_id,))

        conn.commit()
        cur.close()
        conn.close()

        message = f'Автомобиль {car[0]} {car[1]} успешно удален.'
        if deleted_bookings > 0:
            message += f' Удалено {deleted_bookings} связанных бронирований.'

        return jsonify({
            'success': True,
            'message': message
        })

    except Exception as e:
        print(f"Ошибка удаления автомобиля: {e}")
        return jsonify({'success': False, 'message': f'Ошибка при удалении: {str(e)}'})


@app.route('/admin/add_car', methods=['POST'])
@login_required
def add_car():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Доступ запрещен.'})

    try:
        brand = request.form['brand']
        model = request.form['model']
        year = int(request.form['year'])
        daily_price = float(request.form['daily_price'])
        car_class = request.form['car_class']
        fuel_type = request.form['fuel_type']
        transmission = request.form['transmission']
        image_url = request.form.get('image_url', '')
        location = request.form.get('location', 'ул. Ленина, 123')
        color = request.form.get('color', 'синий')
        seats = int(request.form.get('seats', 5))
        description = request.form.get('description', f'Новый автомобиль {brand} {model}.')
        engine = request.form.get('engine', '')
        consumption = request.form.get('consumption', '')
        features_str = request.form.get('features', '')

        # Преобразуем строку особенностей в массив
        features = []
        if features_str:
            features = [f.strip() for f in features_str.split(',') if f.strip()]

        if year < 2000 or year > 2030:
            return jsonify({'success': False,
                            'message': 'Год выпуска должен быть между 2000 и 2030.'})

        if daily_price <= 0:
            return jsonify({'success': False,
                            'message': 'Цена должна быть положительной.'})

        if not image_url:
            return jsonify({'success': False,
                            'message': 'Пожалуйста, укажите ссылку на изображение автомобиля.'})

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute('''
            INSERT INTO cars (brand, model, year, daily_price, car_class, fuel_type, 
                            transmission, image_url, location, color, seats, description,
                            engine, consumption, features)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (brand, model, year, daily_price, car_class, fuel_type, transmission,
              image_url, location, color, seats, description, engine, consumption,
              features if features else None))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'success': True,
                        'message': f'Автомобиль {brand} {model} успешно добавлен.'})

    except Exception as e:
        print(f"Ошибка добавления автомобиля: {e}")
        return jsonify({'success': False,
                        'message': f'Ошибка при добавлении автомобиля: {str(e)}'})


@app.route('/admin/toggle_car/<int:car_id>', methods=['POST'])
@login_required
def toggle_car(car_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Доступ запрещен.'})

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Получаем текущий статус
        cur.execute('SELECT brand, model, is_available FROM cars WHERE id = %s', (car_id,))
        car_data = cur.fetchone()

        if not car_data:
            return jsonify({'success': False,
                            'message': 'Автомобиль не найден.'})

        # Меняем статус
        new_status = not car_data[2]
        cur.execute('UPDATE cars SET is_available = %s WHERE id = %s', (new_status, car_id))
        conn.commit()

        cur.close()
        conn.close()

        action = "доступен" if new_status else "недоступен"
        return jsonify(
            {'success': True, 'message': f'Автомобиль {car_data[0]} {car_data[1]} теперь {action}.'})

    except Exception as e:
        print(f"Ошибка переключения статуса автомобиля: {e}")
        return jsonify({'success': False, 'message': f'Произошла ошибка: {str(e)}.'})


@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Доступ запрещен.', 'danger')
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Получаем всех пользователей
        cur.execute('SELECT * FROM users ORDER BY created_at DESC')
        users = cur.fetchall()

        # Получаем статистику бронирований для каждого пользователя
        user_stats = {}
        cur.execute('''
            SELECT user_id, 
                   COUNT(*) as total_bookings,
                   SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_bookings
            FROM bookings 
            GROUP BY user_id
        ''')

        for row in cur.fetchall():
            user_stats[row['user_id']] = {
                'total': row['total_bookings'],
                'active': row['active_bookings']
            }

        # Получаем ВСЕ бронирования
        cur.execute('''
            SELECT b.*, u.username, u.email, c.brand, c.model, c.image_url 
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN cars c ON b.car_id = c.id
            ORDER BY b.created_at DESC
        ''')
        all_bookings = cur.fetchall()

        # Статистика
        cur.execute("SELECT COUNT(*) as count FROM users WHERE is_admin = TRUE")
        admin_count = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) as count FROM users WHERE is_admin = FALSE")
        user_count = cur.fetchone()['count']

        cur.close()
        conn.close()

        return render_template('admin_users.html',
                               users=users,
                               user_stats=user_stats,
                               admin_count=admin_count,
                               user_count=user_count,
                               bookings_db=all_bookings)
    except Exception as e:
        print(f"Ошибка страницы пользователей: {e}")
        return render_template('admin_users.html',
                               users=[], user_stats={}, admin_count=0, user_count=0,
                               bookings_db=[])


# Отмена бронирования админом
@app.route('/admin/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def admin_cancel_booking(booking_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Доступ запрещен.'})

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Получаем информацию о бронировании
        cur.execute('''
            SELECT b.id, u.username, c.brand, c.model 
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN cars c ON b.car_id = c.id
            WHERE b.id = %s
        ''', (booking_id,))

        booking_info = cur.fetchone()

        if not booking_info:
            return jsonify({'success': False, 'message': 'Бронирование не найдено.'})

        # Отменяем бронирование
        cur.execute('''
            UPDATE bookings SET status = 'cancelled'
            WHERE id = %s AND status = 'active'
            RETURNING id
        ''', (booking_id,))

        updated_booking = cur.fetchone()

        if not updated_booking:
            return jsonify({'success': False, 'message': 'Бронирование уже отменено или неактивно.'})

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Бронирование #{booking_id} пользователя {booking_info[1]} (авто: {booking_info[2]} {booking_info[3]}) успешно отменено.'
        })

    except Exception as e:
        print(f"Ошибка отмены бронирования админом: {e}")
        return jsonify({'success': False, 'message': f'Ошибка при отмене: {str(e)}'})


# Удаление пользователя админом
@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Доступ запрещен.'})

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Проверяем, не пытается ли пользователь удалить самого себя
        if str(user_id) == current_user.id:
            return jsonify({'success': False, 'message': 'Вы не можете удалить свой собственный аккаунт.'})

        # Проверяем, есть ли у пользователя активные бронирования
        cur.execute("SELECT COUNT(*) as count FROM bookings WHERE user_id = %s AND status = 'active'", (user_id,))
        active_bookings = cur.fetchone()['count']

        if active_bookings > 0:
            return jsonify({
                'success': False,
                'message': 'Невозможно удалить пользователя с активными бронированиями. Сначала отмените все бронирования.'
            })

        # Получаем информацию о пользователе
        cur.execute('SELECT username, is_admin FROM users WHERE id = %s', (user_id,))
        user_info = cur.fetchone()

        if not user_info:
            return jsonify({'success': False, 'message': 'Пользователь не найден.'})

        # Нельзя удалить других администраторов
        if user_info['is_admin']:
            return jsonify({
                'success': False,
                'message': 'Нельзя удалить администратора. Только суперадминистратор может удалить других администраторов.'
            })

        # Удаляем все бронирования пользователя
        cur.execute('DELETE FROM bookings WHERE user_id = %s', (user_id,))

        # Удаляем пользователя
        cur.execute('DELETE FROM users WHERE id = %s', (user_id,))

        conn.commit()

        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Пользователь {user_info["username"]} и все его данные успешно удалены.'
        })

    except Exception as e:
        print(f"Ошибка удаления пользователя: {e}")
        return jsonify({'success': False, 'message': f'Ошибка при удалении: {str(e)}'})


# Обработчики ошибок
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


if __name__ == '__main__':
    print("🚀 Запуск CarShareBsk приложения с PostgreSQL...")
    print("🌐 Доступно по адресу: http://localhost:5001")
    print("🔑 Тестовые данные для входа:")
    print("   Администратор: admin / admin123")
    print("   Обычный пользователь: user / user123")
    app.run(debug=True, port=5001)