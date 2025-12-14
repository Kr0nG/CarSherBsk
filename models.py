import psycopg2
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from dotenv import load_dotenv

load_dotenv()


class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        self.create_tables()
        self.create_admin_user()

    def create_tables(self):
        with self.conn.cursor() as cur:
            # Таблица пользователей
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(80) UNIQUE NOT NULL,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE,
                    phone VARCHAR(20),
                    driver_license VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица автомобилей
            cur.execute('''
                CREATE TABLE IF NOT EXISTS cars (
                    id SERIAL PRIMARY KEY,
                    brand VARCHAR(100) NOT NULL,
                    model VARCHAR(100) NOT NULL,
                    year INTEGER NOT NULL,
                    license_plate VARCHAR(20) UNIQUE NOT NULL,
                    color VARCHAR(50),
                    fuel_type VARCHAR(50),
                    transmission VARCHAR(50),
                    seats INTEGER,
                    daily_price DECIMAL(10,2) NOT NULL,
                    is_available BOOLEAN DEFAULT TRUE,
                    location VARCHAR(255),
                    image_url VARCHAR(255),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица бронирований
            cur.execute('''
                CREATE TABLE IF NOT EXISTS bookings (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    car_id INTEGER REFERENCES cars(id),
                    start_date TIMESTAMP NOT NULL,
                    end_date TIMESTAMP NOT NULL,
                    total_price DECIMAL(10,2) NOT NULL,
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            self.conn.commit()
            print("Таблицы успешно созданы!")

    def create_admin_user(self):
        try:
            result = self.execute_query('SELECT id FROM users WHERE username = %s', ('admin',))
            if not result:
                password_hash = generate_password_hash('admin123')
                self.execute_query(
                    'INSERT INTO users (username, email, password_hash, is_admin) VALUES (%s, %s, %s, %s)',
                    ('admin', 'admin@carsharing.ru', password_hash, True)
                )
                print("Администратор создан: admin / admin123")
        except Exception as e:
            print(f"Ошибка при создании администратора: {e}")

    def execute_query(self, query, params=None, fetch=True):
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params or ())
                if fetch and query.strip().upper().startswith('SELECT'):
                    return cur.fetchall()
                self.conn.commit()
                if query.strip().upper().startswith('INSERT'):
                    return cur.lastrowid
                return cur.rowcount
        except Exception as e:
            self.conn.rollback()
            print(f"Ошибка выполнения запроса: {e}")
            raise e

    def get_user_by_username(self, username):
        result = self.execute_query(
            'SELECT id, username, email, password_hash, is_admin, phone, driver_license FROM users WHERE username = %s',
            (username,)
        )
        return result[0] if result else None

    def add_car(self, car_data):
        query = '''
            INSERT INTO cars (brand, model, year, license_plate, color, fuel_type, 
                            transmission, seats, daily_price, location, image_url, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        return self.execute_query(query, (
            car_data['brand'], car_data['model'], car_data['year'],
            car_data['license_plate'], car_data['color'], car_data['fuel_type'],
            car_data['transmission'], car_data['seats'], car_data['daily_price'],
            car_data['location'], car_data.get('image_url'), car_data['description']
        ), fetch=False)

    def get_available_cars(self):
        return self.execute_query('''
            SELECT * FROM cars 
            WHERE is_available = TRUE 
            ORDER BY created_at DESC
        ''')

    def get_car_by_id(self, car_id):
        result = self.execute_query('SELECT * FROM cars WHERE id = %s', (car_id,))
        return result[0] if result else None

    def create_booking(self, user_id, car_id, start_date, end_date, total_price):
        return self.execute_query('''
            INSERT INTO bookings (user_id, car_id, start_date, end_date, total_price)
            VALUES (%s, %s, %s, %s, %s)
        ''', (user_id, car_id, start_date, end_date, total_price), fetch=False)

    def get_user_bookings(self, user_id):
        return self.execute_query('''
            SELECT b.*, c.brand, c.model, c.license_plate, c.image_url
            FROM bookings b 
            JOIN cars c ON b.car_id = c.id 
            WHERE b.user_id = %s 
            ORDER BY b.created_at DESC
        ''', (user_id,))

    def check_car_availability(self, car_id, start_date, end_date):
        result = self.execute_query('''
            SELECT id FROM bookings 
            WHERE car_id = %s AND status = 'active' 
            AND ((start_date <= %s AND end_date >= %s) 
            OR (start_date <= %s AND end_date >= %s))
        ''', (car_id, start_date, start_date, end_date, end_date))
        return len(result) == 0

    def add_sample_cars(self):
        """Добавляет тестовые автомобили в базу данных"""
        sample_cars = [
            {
                'brand': 'Toyota',
                'model': 'Camry',
                'year': 2022,
                'license_plate': 'А123ВС777',
                'color': 'Белый',
                'fuel_type': 'Бензин',
                'transmission': 'Автомат',
                'seats': 5,
                'daily_price': 2500,
                'location': 'Центр города',
                'image_url': 'https://via.placeholder.com/300x200/007bff/ffffff?text=Toyota+Camry',
                'description': 'Комфортабельный седан для городских поездок'
            },
            {
                'brand': 'Hyundai',
                'model': 'Solaris',
                'year': 2021,
                'license_plate': 'В456ОР777',
                'color': 'Серый',
                'fuel_type': 'Бензин',
                'transmission': 'Автомат',
                'seats': 5,
                'daily_price': 1800,
                'location': 'Торговый центр',
                'image_url':'https://s.auto.drom.ru/i24206/c/photos/fullsize/hyundai/solaris/hyundai_solaris_677323.jpg',
                'description': 'Экономичный городской автомобиль'
            },
            {
                'brand': 'Kia',
                'model': 'Rio',
                'year': 2023,
                'license_plate': 'С789ТХ777',
                'color': 'Красный',
                'fuel_type': 'Бензин',
                'transmission': 'Механика',
                'seats': 5,
                'daily_price': 1700,
                'location': 'Железнодорожный вокзал',
                'image_url': 'https://via.placeholder.com/300x200/dc3545/ffffff?text=Kia+Rio',
                'description': 'Надежный хэтчбек с низким расходом'
            }
        ]

        for car in sample_cars:
            try:
                self.add_car(car)
            except Exception as e:
                print(f"Ошибка при добавлении автомобиля {car['brand']} {car['model']}: {e}")


class User(UserMixin):
    def __init__(self, id, username, email, is_admin=False, phone=None, driver_license=None):
        self.id = id
        self.username = username
        self.email = email
        self.is_admin = is_admin
        self.phone = phone
        self.driver_license = driver_license

    @staticmethod
    def get(user_id, db):
        result = db.execute_query(
            'SELECT id, username, email, is_admin, phone, driver_license FROM users WHERE id = %s',
            (user_id,)
        )
        if result:
            user_data = result[0]
            return User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4], user_data[5])
        return None

    @staticmethod
    def create(username, email, password, phone, driver_license, db):
        password_hash = generate_password_hash(password)
        result = db.execute_query(
            '''INSERT INTO users (username, email, password_hash, phone, driver_license) 
               VALUES (%s, %s, %s, %s, %s) RETURNING id''',
            (username, email, password_hash, phone, driver_license),
            fetch=True
        )
        return result[0][0] if result else None