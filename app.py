from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

login_manager = LoginManager(app)
login_manager.login_view = 'login'

DB_CONFIG = {
    'dbname': 'carsharing_gg29',
    'user': 'postgre',
    'password': 'CT0s2HSM3WpzFqmnRdWRRjDJriS3PlW4',
    'host': 'dpg-d4vqh2vpm1nc73btsd1g-a.oregon-postgres.render.com',
    'port': '5432',
    'sslmode': 'require'
}

class User(UserMixin):
    def __init__(self, id, username, email, password_hash, is_admin=False, phone=None, driver_license=None):
        self.id = str(id)
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.is_admin = is_admin
        self.phone = phone
        self.driver_license = driver_license

def get_db():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        
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
        
        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cur.fetchone():
            hash = generate_password_hash('admin123')
            cur.execute('INSERT INTO users (username, email, password_hash, is_admin) VALUES (%s, %s, %s, %s)',
                       ('admin', 'admin@carsharebsk.ru', hash, True))
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ База готова")
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")

@login_manager.user_loader
def load_user(user_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['email'],
                       user_data['password_hash'], user_data['is_admin'],
                       user_data['phone'], user_data['driver_license'])
    except:
        pass
    return None

init_db()

# Регистрация
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
            conn = get_db()
            cur = conn.cursor()
            cur.execute('SELECT id FROM users WHERE username = %s OR email = %s', 
                       (data['username'], data['email']))
            if cur.fetchone():
                flash('Пользователь уже существует', 'danger')
                conn.close()
                return redirect(url_for('register'))
            
            hash = generate_password_hash(data['password'])
            cur.execute('INSERT INTO users (username, email, password_hash, phone, driver_license) VALUES (%s, %s, %s, %s, %s)',
                       (data['username'], data['email'], hash, data['phone'], data['driver_license']))
            conn.commit()
            cur.close()
            conn.close()
            
            flash('Регистрация успешна!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'danger')
    
    return render_template('register.html')

# Логин
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            conn = get_db()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute('SELECT * FROM users WHERE username = %s', (request.form['username'],))
            user_data = cur.fetchone()
            cur.close()
            conn.close()
            
            if user_data and check_password_hash(user_data['password_hash'], request.form['password']):
                user = User(user_data['id'], user_data['username'], user_data['email'],
                           user_data['password_hash'], user_data['is_admin'],
                           user_data['phone'], user_data['driver_license'])
                login_user(user)
                flash(f'Добро пожаловать, {user.username}!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Неверные данные', 'danger')
        except:
            flash('Ошибка входа', 'danger')
    
    return render_template('login.html')

# Логаут
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли', 'info')
    return redirect(url_for('index'))

# Главная
@app.route('/')
def index():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM cars WHERE is_available = TRUE LIMIT 3')
        cars = cur.fetchall()
        
        cur.execute('SELECT COUNT(*) as count FROM cars')
        total_cars = cur.fetchone()['count']
        
        cur.execute('SELECT COUNT(*) as count FROM users')
        total_users = cur.fetchone()['count']
        
        cur.close()
        conn.close()
        
        return render_template('index.html', cars=cars, test_cars_count=total_cars, total_users=total_users)
    except:
        return render_template('index.html', cars=[], test_cars_count=0, total_users=0)

# Автомобили
@app.route('/cars')
def cars():
    car_class = request.args.get('class', 'all')
    transmission = request.args.get('transmission', 'all')
    fuel_type = request.args.get('fuel_type', 'all')
    
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
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
        cars = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return render_template('cars.html', cars=cars)
    except:
        return render_template('cars.html', cars=[])

# Бронирование
@app.route('/car/<int:car_id>')
@login_required
def car_detail(car_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM cars WHERE id = %s', (car_id,))
        car = cur.fetchone()
        
        if car:
            cur.close()
            conn.close()
            return render_template('booking.html', car=car)
    except:
        pass
    
    flash('Авто не найден', 'danger')
    return redirect(url_for('cars'))

# Бронировать
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
        
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM cars WHERE id = %s', (car_id,))
        car = cur.fetchone()
        
        if not car or not car['is_available']:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Авто недоступно'})
        
        days = (end - start).days
        price = float(car['daily_price']) * days
        
        cur.execute('INSERT INTO bookings (user_id, car_id, start_date, end_date, total_price) VALUES (%s, %s, %s, %s, %s)',
                   (current_user.id, car_id, start, end, price))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Успешно! {price} ₽ за {days} дн.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

# Профиль
@app.route('/profile')
@login_required
def profile():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT b.*, c.brand, c.model, c.image_url FROM bookings b JOIN cars c ON b.car_id = c.id WHERE b.user_id = %s ORDER BY b.created_at DESC',
                   (current_user.id,))
        bookings = cur.fetchall()
        cur.close()
        conn.close()
        
        return render_template('profile.html', bookings=bookings)
    except:
        return render_template('profile.html', bookings=[])

# Отмена брони
@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE bookings SET status = 'cancelled' WHERE id = %s AND user_id = %s",
                   (booking_id, current_user.id))
        conn.commit()
        cur.close()
        conn.close()
        
        flash('Бронь отменена', 'success')
    except:
        flash('Ошибка', 'danger')
    
    return redirect(url_for('profile'))

# Контакты и о нас
@app.route('/contacts')
def contacts():
    return render_template('contacts.html')

@app.route('/about')
def about():
    return render_template('about.html')

# Декоратор админа
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Доступ запрещен', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# Админка
@app.route('/admin')
@login_required
@admin_required
def admin():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute('SELECT COUNT(*) as count FROM cars')
        total_cars = cur.fetchone()['count']
        
        cur.execute('SELECT COUNT(*) as count FROM users')
        total_users = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM bookings WHERE status = 'active'")
        active_bookings = cur.fetchone()['count']
        
        cur.execute("SELECT COALESCE(SUM(total_price), 0) as total FROM bookings WHERE status = 'active'")
        total_revenue = cur.fetchone()['total']
        
        cur.execute('SELECT * FROM cars ORDER BY id')
        all_cars = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return render_template('admin.html', total_cars=total_cars, total_users=total_users,
                             active_bookings=active_bookings, total_revenue=total_revenue,
                             all_cars=all_cars)
    except:
        return render_template('admin.html', total_cars=0, total_users=0, active_bookings=0,
                             total_revenue=0, all_cars=[])

# Получить авто для редактирования
@app.route('/admin/get_car/<int:car_id>')
@login_required
@admin_required
def get_car_data(car_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM cars WHERE id = %s', (car_id,))
        car = cur.fetchone()
        cur.close()
        conn.close()
        
        if car and car.get('features'):
            car['features_str'] = ', '.join(car['features'])
        else:
            car['features_str'] = ''
        
        return jsonify({'success': True, 'car': car})
    except:
        return jsonify({'success': False, 'message': 'Ошибка'})

# Обновить авто
@app.route('/admin/update_car/<int:car_id>', methods=['POST'])
@login_required
@admin_required
def update_car(car_id):
    try:
        data = request.form
        features = [f.strip() for f in data.get('features', '').split(',') if f.strip()]
        
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute('''
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
            data.get('image_url'), data.get('engine'), data.get('consumption'),
            features if features else None, car_id
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Авто обновлен'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

# Удалить авто
@app.route('/admin/delete_car/<int:car_id>', methods=['POST'])
@login_required
@admin_required
def delete_car(car_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM bookings WHERE car_id = %s AND status = 'active'", (car_id,))
        if cur.fetchone()[0] > 0:
            return jsonify({'success': False, 'message': 'Есть активные брони'})
        
        cur.execute('DELETE FROM bookings WHERE car_id = %s', (car_id,))
        cur.execute('DELETE FROM cars WHERE id = %s', (car_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Авто удален'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

# Добавить авто
@app.route('/admin/add_car', methods=['POST'])
@login_required
@admin_required
def add_car():
    try:
        data = request.form
        features = [f.strip() for f in data.get('features', '').split(',') if f.strip()]
        
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute('''
            INSERT INTO cars (brand, model, year, daily_price, car_class, fuel_type, 
            transmission, image_url, location, color, seats, description,
            engine, consumption, features)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data['brand'], data['model'], data['year'], data['daily_price'],
            data['car_class'], data['fuel_type'], data['transmission'],
            data.get('image_url', ''),
            data.get('location', 'ул. Ленина, 123'),
            data.get('color', 'синий'),
            data.get('seats', 5),
            data.get('description', 'Новый авто'),
            data.get('engine', ''),
            data.get('consumption', ''),
            features if features else None
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': f'{data["brand"]} {data["model"]} добавлен'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

# Переключить статус авто
@app.route('/admin/toggle_car/<int:car_id>', methods=['POST'])
@login_required
@admin_required
def toggle_car(car_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute('SELECT brand, model, is_available FROM cars WHERE id = %s', (car_id,))
        car = cur.fetchone()
        
        if car:
            new_status = not car[2]
            cur.execute('UPDATE cars SET is_available = %s WHERE id = %s', (new_status, car_id))
            conn.commit()
            
            status = "доступен" if new_status else "недоступен"
            return jsonify({'success': True, 'message': f'{car[0]} {car[1]} теперь {status}'})
        
        return jsonify({'success': False, 'message': 'Не найден'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})
    finally:
        if 'conn' in locals():
            conn.close()

# Запуск
if __name__ == '__main__':
    print("🚀 Запуск: http://localhost:5001")
    print("🔑 Админ: admin / admin123")
    app.run(debug=True, port=5001)