
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret')

# Настройка базы данных через SQLAlchemy
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgre:CT0s2HSM3WpzFqmnRdWRRjDJriS3PlW4@dpg-d4vqh2vpm1nc73btsd1g-a.oregon-postgres.render.com:5432/carsharing_gg29'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
}

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ========== МОДЕЛИ БАЗЫ ДАННЫХ ==========

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    phone = db.Column(db.String(20))
    driver_license = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Отношения
    bookings = db.relationship('Booking', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Car(db.Model):
    __tablename__ = 'cars'

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    daily_price = db.Column(db.Numeric(10, 2), nullable=False)
    fuel_type = db.Column(db.String(50))
    transmission = db.Column(db.String(50))
    seats = db.Column(db.Integer, default=5)
    location = db.Column(db.String(255))
    image_url = db.Column(db.Text)
    is_available = db.Column(db.Boolean, default=True)
    color = db.Column(db.String(50))
    description = db.Column(db.Text)
    car_class = db.Column(db.String(50), default='Эконом')
    features = db.Column(db.ARRAY(db.String))
    engine = db.Column(db.String(100))
    consumption = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Отношения
    bookings = db.relationship('Booking', backref='car', lazy=True)


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

# Инициализация базы данных при запуске
def init_db():
    with app.app_context():
        db.create_all()

        # Создание администратора по умолчанию
        admin = User.query.filter_by(username='Denis').first()
        if not admin:
            admin = User(
                username='Denis',
                email='Denis@carsharebsk.ru',
                is_admin=True
            )
            admin.set_password('Denis123')
            db.session.add(admin)
            db.session.commit()


# Загрузка тестовых автомобилей при первом запуске
def load_test_data():
    with app.app_context():
        if Car.query.count() == 0:
            test_cars = [
                Car(
                    brand='Hyundai',
                    model='Solaris',
                    year=2023,
                    daily_price=1200,
                    fuel_type='Бензин',
                    transmission='Автомат',
                    seats=5,
                    location='ул. Ленина, 123',
                    image_url='https://s.auto.drom.ru/i24206/c/photos/fullsize/hyundai/solaris/hyundai_solaris_677323.jpg',
                    is_available=True,
                    color='Белый',
                    description='Экономичный городской автомобиль',
                    car_class='Эконом',
                    features=['Кондиционер', 'Bluetooth', 'Парктроники'],
                    engine='1.6L',
                    consumption='6.5 л/100км'
                ),
                Car(
                    brand='Toyota',
                    model='Camry',
                    year=2023,
                    daily_price=2500,
                    fuel_type='Бензин',
                    transmission='Автомат',
                    seats=5,
                    location='пр. Ленина, 89',
                    image_url='https://iat.ru/uploads/origin/models/737981/1.webp',
                    is_available=True,
                    color='Черный',
                    description='Комфортабельный седан для бизнес-поездок',
                    car_class='Комфорт',
                    features=['Климат-контроль', 'Кожаный салон', 'Камера заднего вида'],
                    engine='2.5L',
                    consumption='7.8 л/100км'
                ),
                Car(
                    brand='BMW',
                    model='5 Series',
                    year=2023,
                    daily_price=4500,
                    fuel_type='Бензин',
                    transmission='Автомат',
                    seats=5,
                    location='пр. Коммунарский, 156',
                    image_url='https://www.thedrive.com/wp-content/uploads/2024/10/tgI7q.jpg?w=1819&h=1023',
                    is_available=True,
                    color='Черный',
                    description='Представительский седан бизнес-класса',
                    car_class='Премиум',
                    features=['Память сидений', 'Массаж сидений', 'Адаптивный круиз'],
                    engine='3.0L',
                    consumption='8.5 л/100км'
                )
            ]

            for car in test_cars:
                db.session.add(car)
            db.session.commit()
            print("✅ Тестовые автомобили загружены")


# Загрузка пользователя для Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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
            # Проверка существования пользователя
            existing_user = User.query.filter(
                (User.username == data['username']) | (User.email == data['email'])
            ).first()

            if existing_user:
                flash('Пользователь уже существует', 'danger')
                return redirect(url_for('register'))

            # Создание нового пользователя
            new_user = User(
                username=data['username'],
                email=data['email'],
                phone=data['phone'],
                driver_license=data['driver_license']
            )
            new_user.set_password(data['password'])

            db.session.add(new_user)
            db.session.commit()

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

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
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
    # Три самых популярных автомобиля по количеству бронирований
    popular_cars = Car.query.filter_by(is_available=True) \
        .outerjoin(Booking) \
        .group_by(Car.id) \
        .order_by(db.func.count(Booking.id).desc()) \
        .limit(3).all()

    total_cars = Car.query.count()
    total_users = User.query.count()

    return render_template('index.html', cars=popular_cars, test_cars_count=total_cars, total_users=total_users)


# Страница всех автомобилей с фильтрами
@app.route('/cars')
def cars():
    car_class = request.args.get('class', 'all')
    transmission = request.args.get('transmission', 'all')
    fuel_type = request.args.get('fuel_type', 'all')

    query = Car.query.filter_by(is_available=True)

    if car_class != 'all':
        query = query.filter_by(car_class=car_class)
    if transmission != 'all':
        query = query.filter_by(transmission=transmission)
    if fuel_type != 'all':
        query = query.filter_by(fuel_type=fuel_type)

    filtered_cars = query.all()

    # Получение уникальных значений для фильтров
    car_classes = db.session.query(Car.car_class).distinct().filter(Car.car_class.isnot(None)).all()
    transmissions = db.session.query(Car.transmission).distinct().all()
    fuel_types = db.session.query(Car.fuel_type).distinct().all()

    return render_template('cars.html',
                           cars=filtered_cars,
                           car_classes=[c[0] for c in car_classes],
                           transmissions=[t[0] for t in transmissions],
                           fuel_types=[f[0] for f in fuel_types],
                           selected_class=car_class,
                           selected_transmission=transmission,
                           selected_fuel_type=fuel_type)


# Страница деталей автомобиля для бронирования
@app.route('/car/<int:car_id>')
@login_required
def car_detail(car_id):
    car = Car.query.get_or_404(car_id)
    if not car:
        flash('Автомобиль не найден', 'danger')
        return redirect(url_for('cars'))

    similar_cars = Car.query.filter(
        Car.car_class == car.car_class,
        Car.id != car_id
    ).limit(3).all()

    return render_template('booking.html', car=car, similar_cars=similar_cars)


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

        # Проверка доступности автомобиля
        car = Car.query.get(car_id)
        if not car or not car.is_available:
            return jsonify({'success': False, 'message': 'Автомобиль временно недоступен'})

        # Проверка пересечений бронирований
        existing_booking = Booking.query.filter(
            Booking.car_id == car_id,
            Booking.status == 'active',
            Booking.start_date <= end,
            Booking.end_date >= start
        ).first()

        if existing_booking:
            return jsonify({'success': False, 'message': 'Автомобиль уже забронирован на эти даты'})

        # Расчет стоимости и создание бронирования
        days = (end - start).days
        price = float(car.daily_price) * days

        new_booking = Booking(
            user_id=current_user.id,
            car_id=car_id,
            start_date=start,
            end_date=end,
            total_price=price
        )

        db.session.add(new_booking)
        db.session.commit()

        return jsonify({'success': True, 'message': f'Бронирование создано! Стоимость: {price} ₽ за {days} дней.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка при бронировании: {str(e)}'})


# Личный кабинет пользователя с историей бронирований
@app.route('/profile')
@login_required
def profile():
    bookings = Booking.query.filter_by(user_id=current_user.id) \
        .join(Car) \
        .order_by(Booking.created_at.desc()) \
        .all()

    return render_template('profile.html', bookings=bookings)


# Отмена бронирования пользователем
@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.filter_by(id=booking_id, user_id=current_user.id).first()
    if booking:
        booking.status = 'cancelled'
        db.session.commit()
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
    total_cars = Car.query.count()
    total_users = User.query.count()
    active_bookings = Booking.query.filter_by(status='active').count()
    total_revenue = db.session.query(
        db.func.coalesce(db.func.sum(Booking.total_price), 0)
    ).filter_by(status='active').scalar()

    all_cars = Car.query.order_by(Car.id).all()

    return render_template('admin.html',
                           total_cars=total_cars,
                           total_users=total_users,
                           active_bookings=active_bookings,
                           total_revenue=total_revenue,
                           all_cars=all_cars)


# Получение данных автомобиля для редактирования
@app.route('/admin/get_car/<int:car_id>')
@login_required
@admin_required
def get_car_data(car_id):
    car = Car.query.get(car_id)
    if car:
        car_data = {
            'id': car.id,
            'brand': car.brand,
            'model': car.model,
            'year': car.year,
            'daily_price': float(car.daily_price),
            'car_class': car.car_class,
            'fuel_type': car.fuel_type,
            'transmission': car.transmission,
            'color': car.color,
            'seats': car.seats,
            'location': car.location,
            'description': car.description,
            'image_url': car.image_url,
            'engine': car.engine,
            'consumption': car.consumption,
            'features': car.features
        }
        return jsonify({'success': True, 'car': car_data})
    return jsonify({'success': False})


# Обновление данных автомобиля
@app.route('/admin/update_car/<int:car_id>', methods=['POST'])
@login_required
@admin_required
def update_car(car_id):
    car = Car.query.get(car_id)
    if not car:
        return jsonify({'success': False, 'message': 'Автомобиль не найден'})

    data = request.form

    # Обновление полей
    car.brand = data.get('brand', car.brand)
    car.model = data.get('model', car.model)
    car.year = int(data.get('year', car.year))
    car.daily_price = float(data.get('daily_price', car.daily_price))
    car.car_class = data.get('car_class', car.car_class)
    car.fuel_type = data.get('fuel_type', car.fuel_type)
    car.transmission = data.get('transmission', car.transmission)
    car.color = data.get('color', car.color)
    car.seats = int(data.get('seats', car.seats))
    car.location = data.get('location', car.location)
    car.description = data.get('description', car.description)
    car.image_url = data.get('image_url', car.image_url)
    car.engine = data.get('engine', car.engine)
    car.consumption = data.get('consumption', car.consumption)

    # Обработка features
    features_str = data.get('features', '')
    if features_str:
        car.features = [f.strip() for f in features_str.split(',') if f.strip()]

    db.session.commit()
    return jsonify({'success': True, 'message': 'Автомобиль обновлен'})


# Удаление автомобиля
@app.route('/admin/delete_car/<int:car_id>', methods=['POST'])
@login_required
@admin_required
def delete_car(car_id):
    car = Car.query.get(car_id)
    if not car:
        return jsonify({'success': False, 'message': 'Автомобиль не найден'})

    # Проверка активных бронирований
    active_bookings = Booking.query.filter_by(car_id=car_id, status='active').count()
    if active_bookings > 0:
        return jsonify({'success': False, 'message': 'Есть активные брони'})

    # Удаление связанных бронирований
    Booking.query.filter_by(car_id=car_id).delete()

    # Удаление автомобиля
    db.session.delete(car)
    db.session.commit()

    return jsonify({'success': True, 'message': f'Автомобиль {car.brand} {car.model} удален'})


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

    new_car = Car(
        brand=data['brand'],
        model=data['model'],
        year=int(data['year']),
        daily_price=float(data['daily_price']),
        car_class=data['car_class'],
        fuel_type=data['fuel_type'],
        transmission=data['transmission'],
        image_url=data['image_url'],
        location=data.get('location', 'ул. Ленина, 123'),
        color=data.get('color', 'синий'),
        seats=int(data.get('seats', 5)),
        description=data.get('description', f'Новый {data["brand"]} {data["model"]}'),
        engine=data.get('engine', ''),
        consumption=data.get('consumption', ''),
        features=features if features else None
    )

    db.session.add(new_car)
    db.session.commit()

    return jsonify({'success': True, 'message': f'Автомобиль {data["brand"]} {data["model"]} добавлен'})


# Переключение доступности автомобиля
@app.route('/admin/toggle_car/<int:car_id>', methods=['POST'])
@login_required
@admin_required
def toggle_car(car_id):
    car = Car.query.get(car_id)
    if not car:
        return jsonify({'success': False, 'message': 'Автомобиль не найден'})

    car.is_available = not car.is_available
    db.session.commit()

    status = "доступен" if car.is_available else "недоступен"
    return jsonify({'success': True, 'message': f'Автомобиль {car.brand} {car.model} теперь {status}'})


# Управление пользователями
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    bookings = Booking.query.join(User).join(Car) \
        .order_by(Booking.created_at.desc()) \
        .all()

    # Статистика бронирований по пользователям
    user_stats = {}
    stats = db.session.query(
        Booking.user_id,
        db.func.count(Booking.id).label('total'),
        db.func.sum(db.case((Booking.status == 'active', 1), else_=0)).label('active')
    ).group_by(Booking.user_id).all()

    for stat in stats:
        user_stats[stat.user_id] = {
            'total': stat.total,
            'active': stat.active
        }

    admin_count = User.query.filter_by(is_admin=True).count()
    user_count = User.query.filter_by(is_admin=False).count()

    return render_template('admin_users.html',
                           users=users,
                           user_stats=user_stats,
                           bookings_db=bookings,
                           admin_count=admin_count,
                           user_count=user_count)


# Отмена бронирования администратором
@app.route('/admin/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def admin_cancel_booking(booking_id):
    booking = Booking.query.get(booking_id)
    if booking:
        booking.status = 'cancelled'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Бронирование отменено'})
    return jsonify({'success': False, 'message': 'Бронирование не найдено'})


# Удаление пользователя администратором
@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    if str(user_id) == current_user.id:
        return jsonify({'success': False, 'message': 'Нельзя удалить свой аккаунт'})

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'Пользователь не найден'})

    # Удаление связанных бронирований
    Booking.query.filter_by(user_id=user_id).delete()

    # Удаление пользователя
    db.session.delete(user)
    db.session.commit()

    user_type = "администратора" if user.is_admin else "пользователя"
    return jsonify({'success': True, 'message': f'{user_type} {user.username} удален'})


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

    with app.app_context():
        init_db()
        load_test_data()

    app.run(debug=True, port=5001)
