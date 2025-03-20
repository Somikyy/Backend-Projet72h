from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import logging
import uuid
import mysql.connector
from mysql.connector import Error

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='mocktail_server.log')
logger = logging.getLogger('mocktail_server')

app = Flask(__name__)
CORS(app)  # Включаем CORS для всех маршрутов

# Параметры подключения к базе данных
DB_CONFIG = {
    'host': '192.168.1.113',
    'user': 'mocktail_user',
    'password': 'sin',
    'database': 'mocktail_machine'
}

# Функция для получения соединения с базой данных
def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return None

# Проверка здоровья системы
@app.route('/health', methods=['GET'])
def health_check():
    """Эндпоинт для проверки работы сервера"""
    conn = get_db_connection()
    if conn:
        conn.close()
        return jsonify({"status": "online", "database": "connected", "timestamp": time.time()})
    return jsonify({"status": "online", "database": "disconnected", "timestamp": time.time()})

# Эндпоинт для приготовления коктейля
@app.route('/prepare_mocktail', methods=['POST'])
def prepare_mocktail():
    """Эндпоинт для приема запросов на приготовление коктейля"""
    try:
        data = request.json
        logger.info(f"Получен заказ: {data}")
        
        # Проверяем наличие обязательных полей
        required_fields = ['mocktailName', 'ingredients', 'totalVolume']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"Отсутствует обязательное поле: {field}"}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Не удалось подключиться к базе данных"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Создаем ID заказа
        order_id = str(uuid.uuid4())
        
        # Добавляем заказ в базу данных
        query = """
        INSERT INTO orders (order_id, mocktail_name, timestamp, status, total_volume)
        VALUES (%s, %s, %s, %s, %s)
        """
        values = (
            order_id,
            data['mocktailName'],
            time.time(),
            'received',
            data['totalVolume']
        )
        cursor.execute(query, values)
        
        # Добавляем ингредиенты заказа
        for ingredient_name, amount in data['ingredients'].items():
            query = """
            INSERT INTO order_ingredients (order_id, ingredient_name, amount)
            VALUES (%s, %s, %s)
            """
            values = (order_id, ingredient_name, amount)
            cursor.execute(query, values)
        
        # Обновляем уровни ингредиентов
        for ingredient_name, amount in data['ingredients'].items():
            query = """
            UPDATE ingredients
            SET current_level = GREATEST(0, current_level - %s)
            WHERE name = %s
            """
            values = (amount, ingredient_name)
            cursor.execute(query, values)
        
        # Имитируем время обработки
        time.sleep(1)
        
        # Обновляем статус заказа
        query = """
        UPDATE orders
        SET status = 'processing'
        WHERE order_id = %s
        """
        cursor.execute(query, (order_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Заказ коктейля принят и обрабатывается",
            "orderId": order_id
        })
        
    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {str(e)}")
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500

# Эндпоинт для проверки статуса заказа
@app.route('/order_status/<order_id>', methods=['GET'])
def order_status(order_id):
    """Эндпоинт для проверки статуса заказа"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Не удалось подключиться к базе данных"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Получаем основную информацию о заказе
        query = """
        SELECT * FROM orders WHERE order_id = %s
        """
        cursor.execute(query, (order_id,))
        order = cursor.fetchone()
        
        if not order:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Заказ не найден"}), 404
        
        # Получаем ингредиенты заказа
        query = """
        SELECT ingredient_name, amount FROM order_ingredients WHERE order_id = %s
        """
        cursor.execute(query, (order_id,))
        ingredients = cursor.fetchall()
        
        # Формируем словарь ингредиентов
        ingredients_dict = {item['ingredient_name']: item['amount'] for item in ingredients}
        
        # Добавляем ингредиенты к информации о заказе
        order['ingredients'] = ingredients_dict
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "order": order
        })
        
    except Exception as e:
        logger.error(f"Ошибка проверки статуса заказа: {str(e)}")
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500

# Эндпоинт для получения всех заказов
@app.route('/orders', methods=['GET'])
def get_orders():
    """Эндпоинт для получения всех заказов"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Не удалось подключиться к базе данных"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Получаем все заказы
        query = """
        SELECT * FROM orders ORDER BY timestamp DESC
        """
        cursor.execute(query)
        orders = cursor.fetchall()
        
        # Для каждого заказа получаем ингредиенты
        for order in orders:
            query = """
            SELECT ingredient_name, amount FROM order_ingredients WHERE order_id = %s
            """
            cursor.execute(query, (order['order_id'],))
            ingredients = cursor.fetchall()
            order['ingredients'] = {item['ingredient_name']: item['amount'] for item in ingredients}
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "orders": orders
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения заказов: {str(e)}")
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500

# ЭНДПОИНТЫ ДЛЯ ОТЗЫВОВ

# Получение всех отзывов для коктейля
@app.route('/reviews/<mocktail_id>', methods=['GET'])
def get_mocktail_reviews(mocktail_id):
    """Получение всех отзывов для конкретного коктейля"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Не удалось подключиться к базе данных"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Получаем отзывы
        query = """
        SELECT * FROM reviews WHERE mocktail_id = %s ORDER BY created_at DESC
        """
        cursor.execute(query, (mocktail_id,))
        reviews = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "reviews": reviews
        })
    except Exception as e:
        logger.error(f"Ошибка получения отзывов: {str(e)}")
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500

# Добавление нового отзыва
@app.route('/reviews', methods=['POST'])
def add_review():
    """Добавление нового отзыва для коктейля"""
    try:
        data = request.json
        logger.info(f"Получен отзыв: {data}")
        
        # Проверяем наличие обязательных полей
        required_fields = ['mocktailId', 'userName', 'rating', 'comment']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"Отсутствует обязательное поле: {field}"}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Не удалось подключиться к базе данных"}), 500
        
        cursor = conn.cursor()
        
        # Создаем ID отзыва
        review_id = str(uuid.uuid4())
        
        # Добавляем отзыв
        query = """
        INSERT INTO reviews (review_id, mocktail_id, user_name, rating, comment, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (
            review_id,
            data['mocktailId'],
            data['userName'],
            data['rating'],
            data['comment'],
            data.get('createdAt', time.time())
        )
        cursor.execute(query, values)
        
        # Обновляем средний рейтинг коктейля
        query = """
        SELECT AVG(rating) as avg_rating, COUNT(*) as review_count 
        FROM reviews 
        WHERE mocktail_id = %s
        """
        cursor.execute(query, (data['mocktailId'],))
        result = cursor.fetchone()
        
        if result and result[0] is not None:
            avg_rating = float(result[0])
            review_count = int(result[1])
            
            query = """
            UPDATE mocktails
            SET rating = %s, review_count = %s
            WHERE mocktail_id = %s
            """
            cursor.execute(query, (avg_rating, review_count, data['mocktailId']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Отзыв успешно добавлен",
            "reviewId": review_id
        })
    except Exception as e:
        logger.error(f"Ошибка добавления отзыва: {str(e)}")
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500

# ЭНДПОИНТЫ ДЛЯ ИНГРЕДИЕНТОВ

# Получение уровней ингредиентов
@app.route('/ingredients/levels', methods=['GET'])
def get_ingredient_levels():
    """Получение текущих уровней всех ингредиентов"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Не удалось подключиться к базе данных"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Получаем ингредиенты
        query = """
        SELECT ingredient_id as ingredientId, name, current_level as currentLevel, max_level as maxLevel 
        FROM ingredients
        """
        cursor.execute(query)
        ingredients = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "ingredients": ingredients
        })
    except Exception as e:
        logger.error(f"Ошибка получения уровней ингредиентов: {str(e)}")
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500

# Проверка наличия ингредиентов
@app.route('/ingredients/check', methods=['POST'])
def check_ingredients():
    """Проверка наличия достаточного количества ингредиентов для коктейля"""
    try:
        data = request.json
        logger.info(f"Проверка ингредиентов: {data}")
        
        if 'ingredients' not in data:
            return jsonify({"success": False, "message": "Отсутствует обязательное поле: ingredients"}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Не удалось подключиться к базе данных"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Проверяем наличие каждого ингредиента
        requested_ingredients = data['ingredients']
        missing_ingredients = []
        
        for name, amount in requested_ingredients.items():
            # Ищем ингредиент по имени
            query = """
            SELECT current_level FROM ingredients WHERE name = %s
            """
            cursor.execute(query, (name,))
            result = cursor.fetchone()
            
            if not result:
                missing_ingredients.append(f"{name} (не доступен)")
            elif result['current_level'] < amount:
                missing_ingredients.append(f"{name} (требуется {amount} мл, доступно {result['current_level']} мл)")
        
        cursor.close()
        conn.close()
        
        if missing_ingredients:
            return jsonify({
                "available": False,
                "message": "Некоторые ингредиенты недоступны в достаточном количестве",
                "missingIngredients": missing_ingredients
            })
        
        return jsonify({
            "available": True,
            "message": "Все ингредиенты доступны"
        })
    except Exception as e:
        logger.error(f"Ошибка проверки ингредиентов: {str(e)}")
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500

# Обновление уровня ингредиентов (для админ-панели)
@app.route('/ingredients/update', methods=['POST'])
def update_ingredient_levels_admin():
    """Обновление уровней ингредиентов (административная функция)"""
    try:
        data = request.json
        logger.info(f"Обновление уровней ингредиентов: {data}")
        
        if 'updatedLevels' not in data:
            return jsonify({"success": False, "message": "Отсутствует обязательное поле: updatedLevels"}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Не удалось подключиться к базе данных"}), 500
        
        cursor = conn.cursor()
        
        # Обновляем уровни
        updated_levels = data['updatedLevels']
        for ingredient_id, level in updated_levels.items():
            query = """
            UPDATE ingredients
            SET current_level = %s
            WHERE ingredient_id = %s
            """
            cursor.execute(query, (level, ingredient_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Уровни ингредиентов успешно обновлены"
        })
    except Exception as e:
        logger.error(f"Ошибка обновления уровней ингредиентов: {str(e)}")
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500

if __name__ == '__main__':
    logger.info("Запуск сервера Mocktail Machine с MySQL...")
    app.run(host='0.0.0.0', port=5001, debug=True)