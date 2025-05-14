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
    'host': '172.20.10.4',
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

@app.route('/order_status/update', methods=['POST'])
def update_order_status():
    """Endpoint pour mettre à jour le statut d'une commande"""
    try:
        data = request.json
        logger.info(f"Mise à jour du statut de commande: {data}")
        
        # Vérification des champs requis
        required_fields = ['orderId', 'status']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"Champ requis manquant: {field}"}), 400
        
        order_id = data['orderId']
        new_status = data['status']
        
        # Statuts valides
        valid_statuses = ['received', 'processing', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return jsonify({"success": False, "message": f"Statut invalide. Valeurs autorisées: {', '.join(valid_statuses)}"}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Erreur de connexion à la base de données"}), 500
        
        cursor = conn.cursor()
        
        # Vérifier si la commande existe
        query = """
        SELECT * FROM orders WHERE order_id = %s
        """
        cursor.execute(query, (order_id,))
        order = cursor.fetchone()
        
        if not order:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Commande introuvable"}), 404
        
        # Mise à jour du statut
        query = """
        UPDATE orders
        SET status = %s
        WHERE order_id = %s
        """
        cursor.execute(query, (new_status, order_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"Statut de la commande mis à jour: {new_status}"
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du statut: {str(e)}")
        return jsonify({"success": False, "message": f"Erreur serveur: {str(e)}"}), 500

@app.route('/reviews/<review_id>', methods=['DELETE'])
def delete_review(review_id):
    """Supprimer un avis spécifique"""
    try:
        data = request.json
        logger.info(f"Suppression de l'avis {review_id}")
        
        # Récupération du mocktail_id depuis le body
        mocktail_id = data.get('mocktailId')
        if not mocktail_id:
            return jsonify({"success": False, "message": "mocktailId requis dans le corps de la requête"}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Erreur de connexion à la base de données"}), 500
        
        cursor = conn.cursor()
        
        # Vérifier si l'avis existe
        query = """
        SELECT * FROM reviews WHERE review_id = %s AND mocktail_id = %s
        """
        cursor.execute(query, (review_id, mocktail_id))
        review = cursor.fetchone()
        
        if not review:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Avis introuvable"}), 404
        
        # Supprimer l'avis
        query = """
        DELETE FROM reviews WHERE review_id = %s
        """
        cursor.execute(query, (review_id,))
        
        # Mettre à jour la note moyenne et le nombre d'avis du mocktail
        query = """
        SELECT AVG(rating) as avg_rating, COUNT(*) as review_count 
        FROM reviews 
        WHERE mocktail_id = %s
        """
        cursor.execute(query, (mocktail_id,))
        result = cursor.fetchone()
        
        if result and result[0] is not None:
            avg_rating = float(result[0])
            review_count = int(result[1])
            
            query = """
            UPDATE mocktails
            SET rating = %s, review_count = %s
            WHERE mocktail_id = %s
            """
            cursor.execute(query, (avg_rating, review_count, mocktail_id))
        else:
            # S'il n'y a plus d'avis, réinitialiser la note
            query = """
            UPDATE mocktails
            SET rating = 0, review_count = 0
            WHERE mocktail_id = %s
            """
            cursor.execute(query, (mocktail_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Avis supprimé avec succès"
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de l'avis: {str(e)}")
        return jsonify({"success": False, "message": f"Erreur serveur: {str(e)}"}), 500

@app.route('/reviews/<review_id>', methods=['PUT'])
def update_review(review_id):
    """Modifier un avis existant"""
    try:
        data = request.json
        logger.info(f"Mise à jour de l'avis {review_id}: {data}")
        
        # Vérification des champs requis
        required_fields = ['mocktailId', 'rating', 'comment']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"Champ requis manquant: {field}"}), 400
        
        mocktail_id = data['mocktailId']
        rating = data['rating']
        comment = data['comment']
        
        # Validation de la note
        try:
            rating = float(rating)
            if not (1.0 <= rating <= 5.0):
                return jsonify({"success": False, "message": "La note doit être entre 1.0 et 5.0"}), 400
        except ValueError:
            return jsonify({"success": False, "message": "Format de note invalide"}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Erreur de connexion à la base de données"}), 500
        
        cursor = conn.cursor()
        
        # Vérifier si l'avis existe
        query = """
        SELECT * FROM reviews WHERE review_id = %s AND mocktail_id = %s
        """
        cursor.execute(query, (review_id, mocktail_id))
        review = cursor.fetchone()
        
        if not review:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Avis introuvable"}), 404
        
        # Mise à jour de l'avis
        query = """
        UPDATE reviews
        SET rating = %s, comment = %s
        WHERE review_id = %s
        """
        cursor.execute(query, (rating, comment, review_id))
        
        # Mettre à jour la note moyenne du mocktail
        query = """
        SELECT AVG(rating) as avg_rating, COUNT(*) as review_count 
        FROM reviews 
        WHERE mocktail_id = %s
        """
        cursor.execute(query, (mocktail_id,))
        result = cursor.fetchone()
        
        if result and result[0] is not None:
            avg_rating = float(result[0])
            review_count = int(result[1])
            
            query = """
            UPDATE mocktails
            SET rating = %s, review_count = %s
            WHERE mocktail_id = %s
            """
            cursor.execute(query, (avg_rating, review_count, mocktail_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Avis mis à jour avec succès"
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de l'avis: {str(e)}")
        return jsonify({"success": False, "message": f"Erreur serveur: {str(e)}"}), 500


# Проверка здоровья системы
@app.route('/health', methods=['GET'])
def health_check():
    """Эндпоинт для проверки работы сервера"""
    conn = get_db_connection()
    if conn:
        conn.close()
        return jsonify({"status": "online", "database": "connected", "timestamp": time.time()})
    return jsonify({"status": "online", "database": "disconnected", "timestamp": time.time()})

# Эндпоинт для получения всех коктейлей с их рейтингами
@app.route('/mocktails', methods=['GET'])
def get_mocktails():
    """Эндпоинт для получения всех коктейлей с их рейтингами"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Не удалось подключиться к базе данных"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Получаем все коктейли с рейтингами
        query = """
        SELECT m.mocktail_id, m.name, m.description, m.image_url, 
               COALESCE(m.rating, 0) as rating, COALESCE(m.review_count, 0) as review_count
        FROM mocktails m
        """
        cursor.execute(query)
        mocktails = cursor.fetchall()
        
        # Для каждого коктейля получаем ингредиенты и теги
        for mocktail in mocktails:
            # Получаем ингредиенты
            query = """
            SELECT i.name, mi.amount
            FROM mocktail_ingredients mi
            JOIN ingredients i ON mi.ingredient_id = i.ingredient_id
            WHERE mi.mocktail_id = %s
            """
            cursor.execute(query, (mocktail['mocktail_id'],))
            ingredients_data = cursor.fetchall()
            mocktail['ingredients'] = {item['name']: item['amount'] for item in ingredients_data}
            
            # Получаем теги
            query = """
            SELECT t.name
            FROM mocktail_tags mt
            JOIN tags t ON mt.tag_id = t.tag_id
            WHERE mt.mocktail_id = %s
            """
            cursor.execute(query, (mocktail['mocktail_id'],))
            tags_data = cursor.fetchall()
            mocktail['tags'] = [item['name'] for item in tags_data]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "mocktails": mocktails
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения коктейлей: {str(e)}")
        return jsonify({"success": False, "message": f"Ошибка сервера: {str(e)}"}), 500
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
    """Get reviews for a specific mocktail"""
    try:
        print(f"===== PYTHON BACKEND DEBUG =====")
        print(f"Received request for reviews with mocktail_id: {mocktail_id}")
        
        conn = get_db_connection()
        if not conn:
            print("Database connection failed")
            return jsonify({"success": False, "message": "Failed to connect to database"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # First try by exact mocktail_id
        query = """
        SELECT * FROM reviews WHERE mocktail_id = %s ORDER BY created_at DESC
        """
        cursor.execute(query, (mocktail_id,))
        reviews = cursor.fetchall()
        print(f"Query by mocktail_id={mocktail_id} returned {len(reviews)} reviews")
        
        # If no results, try by name
        if not reviews:
            print(f"Trying to find by name match")
            query = """
            SELECT r.* FROM reviews r
            JOIN mocktails m ON r.mocktail_id = m.mocktail_id
            WHERE m.name = %s
            ORDER BY r.created_at DESC
            """
            cursor.execute(query, (mocktail_id,))
            reviews = cursor.fetchall()
            print(f"Query by name={mocktail_id} returned {len(reviews)} reviews")
        
        # If still no results, try by formatted name
        if not reviews:
            formatted_id = mocktail_id.lower().replace(' ', '_')
            print(f"Trying with formatted ID: {formatted_id}")
            query = """
            SELECT r.* FROM reviews r
            JOIN mocktails m ON r.mocktail_id = m.mocktail_id
            WHERE m.mocktail_id = %s
            ORDER BY r.created_at DESC
            """
            cursor.execute(query, (formatted_id,))
            reviews = cursor.fetchall()
            print(f"Query by formatted_id={formatted_id} returned {len(reviews)} reviews")
        
        # Print each review for debugging
        for review in reviews:
            print(f"Review found: {review}")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "reviews": reviews
        })
    except Exception as e:
        logger.error(f"Error getting reviews: {str(e)}")
        print(f"Exception occurred: {str(e)}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

# Добавление нового отзыва

@app.route('/reviews', methods=['POST'])
def add_review():
    """Add a new review for a mocktail"""
    try:
        data = request.json
        print(f"===== ADD REVIEW BACKEND DEBUG =====")
        print(f"Received review data: {data}")
        
        # Validate required fields
        required_fields = ['mocktailId', 'userName', 'rating', 'comment']
        for field in required_fields:
            if field not in data:
                print(f"Missing required field: {field}")
                return jsonify({"success": False, "message": f"Missing required field: {field}"}), 400
        
        conn = get_db_connection()
        if not conn:
            print("Database connection failed")
            return jsonify({"success": False, "message": "Failed to connect to database"}), 500
        
        cursor = conn.cursor()
        
        # First, find the correct mocktail_id
        mocktail_id = data['mocktailId']
        print(f"Looking for mocktail with ID or name: {mocktail_id}")
        
        # Try to find by ID first
        cursor.execute("SELECT mocktail_id FROM mocktails WHERE mocktail_id = %s", (mocktail_id,))
        result = cursor.fetchone()
        
        # If not found by ID, try by name
        if not result:
            print(f"Not found by ID, trying by name")
            cursor.execute("SELECT mocktail_id FROM mocktails WHERE name = %s", (mocktail_id,))
            result = cursor.fetchone()
        
        # If still not found, create a formatted ID from the name
        if not result:
            formatted_id = mocktail_id.lower().replace(' ', '_')
            print(f"Not found by name, trying formatted ID: {formatted_id}")
            cursor.execute("SELECT mocktail_id FROM mocktails WHERE mocktail_id = %s", (formatted_id,))
            result = cursor.fetchone()
            
            if result:
                mocktail_id = result[0]
            else:
                # Just use the formatted ID if we can't find a match
                mocktail_id = formatted_id
        else:
            mocktail_id = result[0]
            
        print(f"Using mocktail_id: {mocktail_id}")
        
        # Create a review ID
        review_id = str(uuid.uuid4())
        
        # Add the review
        query = """
        INSERT INTO reviews (review_id, mocktail_id, user_name, rating, comment, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        created_at = data.get('createdAt', time.time())
        if isinstance(created_at, str):
            # Convert ISO string to timestamp if needed
            try:
                from datetime import datetime
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
            except:
                created_at = time.time()
                
        values = (
            review_id,
            mocktail_id,
            data['userName'],
            data['rating'],
            data['comment'],
            created_at
        )
        cursor.execute(query, values)
        
        # Update the average rating for the mocktail
        print("Updating average rating")
        query = """
        SELECT AVG(rating) as avg_rating, COUNT(*) as review_count 
        FROM reviews 
        WHERE mocktail_id = %s
        """
        cursor.execute(query, (mocktail_id,))
        result = cursor.fetchone()
        
        if result and result[0] is not None:
            avg_rating = float(result[0])
            review_count = int(result[1])
            
            print(f"New rating: {avg_rating}, Count: {review_count}")
            
            query = """
            UPDATE mocktails
            SET rating = %s, review_count = %s
            WHERE mocktail_id = %s
            """
            cursor.execute(query, (avg_rating, review_count, mocktail_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Review successfully added",
            "reviewId": review_id
        })
    except Exception as e:
        logger.error(f"Error adding review: {str(e)}")
        print(f"Exception occurred: {str(e)}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

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
