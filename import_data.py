import mysql.connector
import json
import os

# Параметры подключения к базе данных
db_config = {
    'host': '172.20.10.4',
    'user': 'mocktail_user',
    'password': 'sin',
    'database': 'mocktail_machine'
}

# Путь к данным
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

INGREDIENTS_FILE = os.path.join(DATA_DIR, 'ingredients.json')

# Функция для проверки, существует ли файл ингредиентов
def init_ingredients_file_if_needed():
    if not os.path.exists(INGREDIENTS_FILE):
        # Создаем файл с дефолтными ингредиентами (как в вашем __main__.py)
        default_ingredients = [
            {
                "ingredientId": "cranberry",
                "name": "Jus de Cranberry",
                "currentLevel": 800,
                "maxLevel": 1000
            },
            {
                "ingredientId": "grenadine",
                "name": "Sirop de Grenadine",
                "currentLevel": 700,
                "maxLevel": 1000
            },
            {
                "ingredientId": "citron",
                "name": "Jus de Citron",
                "currentLevel": 600,
                "maxLevel": 1000
            },
            {
                "ingredientId": "sprite",
                "name": "Sprite",
                "currentLevel": 900,
                "maxLevel": 1000
            }
        ]
        with open(INGREDIENTS_FILE, 'w') as f:
            json.dump(default_ingredients, f, indent=2)
        print(f"Создан файл ингредиентов: {INGREDIENTS_FILE}")

# Добавление/обновление структуры таблиц для рейтингов
def update_table_structure():
    print("Обновление структуры таблиц для поддержки рейтингов...")
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        # Проверяем наличие колонки rating в таблице mocktails
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'mocktails' 
            AND COLUMN_NAME = 'rating'
            AND TABLE_SCHEMA = %s
        """, (db_config['database'],))
        
        if cursor.fetchone()[0] == 0:
            print("Добавление колонки rating в таблицу mocktails")
            cursor.execute("ALTER TABLE mocktails ADD COLUMN rating FLOAT DEFAULT 0")
        else:
            print("Колонка rating уже существует")
        
        # Проверяем наличие колонки review_count в таблице mocktails
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'mocktails' 
            AND COLUMN_NAME = 'review_count'
            AND TABLE_SCHEMA = %s
        """, (db_config['database'],))
        
        if cursor.fetchone()[0] == 0:
            print("Добавление колонки review_count в таблицу mocktails")
            cursor.execute("ALTER TABLE mocktails ADD COLUMN review_count INT DEFAULT 0")
        else:
            print("Колонка review_count уже существует")
        
        # Обновляем значения рейтингов на основе существующих отзывов
        print("Обновление рейтингов на основе существующих отзывов...")
        cursor.execute("""
            UPDATE mocktails m
            SET 
                rating = (SELECT COALESCE(AVG(rating), 0) FROM reviews r WHERE r.mocktail_id = m.mocktail_id),
                review_count = (SELECT COUNT(*) FROM reviews r WHERE r.mocktail_id = m.mocktail_id)
        """)
        
        conn.commit()
        print("Обновление структуры таблиц завершено успешно!")
        
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при обновлении структуры таблиц: {e}")
    
    finally:
        cursor.close()
        conn.close()

# Обновление ингредиентов (вместо удаления и повторной вставки)
def update_ingredients():
    # Проверяем наличие файла ингредиентов
    init_ingredients_file_if_needed()
    
    # Загрузка данных из JSON
    with open(INGREDIENTS_FILE, 'r') as f:
        ingredients = json.load(f)
    
    # Подключение к базе данных
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        for ingredient in ingredients:
            # Проверяем, существует ли ингредиент
            cursor.execute(
                "SELECT COUNT(*) FROM ingredients WHERE ingredient_id = %s", 
                (ingredient['ingredientId'],)
            )
            if cursor.fetchone()[0] > 0:
                # Обновляем существующий ингредиент
                query = """
                UPDATE ingredients
                SET name = %s, current_level = %s, max_level = %s
                WHERE ingredient_id = %s
                """
                values = (
                    ingredient['name'],
                    ingredient['currentLevel'],
                    ingredient['maxLevel'],
                    ingredient['ingredientId']
                )
                cursor.execute(query, values)
                print(f"Обновлен ингредиент: {ingredient['name']}")
            else:
                # Вставляем новый ингредиент
                query = """
                INSERT INTO ingredients (ingredient_id, name, current_level, max_level)
                VALUES (%s, %s, %s, %s)
                """
                values = (
                    ingredient['ingredientId'],
                    ingredient['name'],
                    ingredient['currentLevel'],
                    ingredient['maxLevel']
                )
                cursor.execute(query, values)
                print(f"Добавлен новый ингредиент: {ingredient['name']}")
        
        # Сохранение изменений
        conn.commit()
        print(f"Обновление ингредиентов завершено")
    
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при обновлении ингредиентов: {e}")
    
    finally:
        cursor.close()
        conn.close()

# Обновление коктейлей (вместо удаления и повторной вставки)
def update_mocktails():
    # Данные о коктейлях (преобразованные из cocktail_manager.dart)
    mocktails = [
        {
            "mocktail_id": "sunrise_rouge",
            "name": "Sunrise Rouge",
            "description": "Un mocktail rafraîchissant aux fruits rouges avec des bulles",
            "image_url": "assets/images/sunrise.png",
            "ingredients": {
                "Jus de Cranberry": 70,
                "Sirop de Grenadine": 20,
                "Sprite": 60
            },
            "tags": ["Fruité", "Pétillant", "Rouge"]
        },
        {
            "mocktail_id": "citrus_fizz",
            "name": "Citrus Fizz",
            "description": "Une boisson pétillante et acidulée",
            "image_url": "assets/images/citrus.png",
            "ingredients": {
                "Jus de Citron": 30,
                "Sprite": 100,
                "Sirop de Grenadine": 20
            },
            "tags": ["Agrumes", "Pétillant", "Rafraîchissant"]
        },
        {
            "mocktail_id": "berry_splash",
            "name": "Berry Splash",
            "description": "Un mélange parfait de fruits rouges et d'agrumes",
            "image_url": "assets/images/berry.png",
            "ingredients": {
                "Jus de Cranberry": 90,
                "Jus de Citron": 30,
                "Sprite": 30
            },
            "tags": ["Fruité", "Rafraîchissant", "Rouge"]
        },
        {
            "mocktail_id": "bleu_lagoon",
            "name": "Bleu Lagoon",
            "description": "Un mocktail rafraîchissant avec une belle couleur bleutée",
            "image_url": "assets/images/blue.png",
            "ingredients": {
                "Sprite": 100,
                "Jus de Citron": 40,
                "Sirop de Grenadine": 10
            },
            "tags": ["Doux", "Pétillant", "Rafraîchissant"]
        },
        {
            "mocktail_id": "sunset_dream",
            "name": "Sunset Dream",
            "description": "Un mocktail élégant avec des saveurs douces de fruits rouges",
            "image_url": "assets/images/sunset.png",
            "ingredients": {
                "Jus de Cranberry": 60,
                "Sprite": 70,
                "Sirop de Grenadine": 20
            },
            "tags": ["Doux", "Élégant", "Fruité"]
        },
        {
            "mocktail_id": "zesty_lemon",
            "name": "Zesty Lemon",
            "description": "Une explosion d'agrumes pour un rafraîchissement maximal",
            "image_url": "assets/images/lemon.png",
            "ingredients": {
                "Jus de Citron": 50,
                "Sprite": 90,
                "Sirop de Grenadine": 10
            },
            "tags": ["Agrumes", "Acidulé", "Rafraîchissant"]
        },
        {
            "mocktail_id": "ruby_sparkle",
            "name": "Ruby Sparkle",
            "description": "Un mocktail festif avec une belle couleur rubis profonde",
            "image_url": "assets/images/ruby.png",
            "ingredients": {
                "Jus de Cranberry": 80,
                "Sirop de Grenadine": 30,
                "Sprite": 40
            },
            "tags": ["Fruité", "Festif", "Rouge"]
        },
        {
            "mocktail_id": "fresh_breeze",
            "name": "Fresh Breeze",
            "description": "Un mélange léger et aérien qui évoque la fraîcheur d'une brise d'été",
            "image_url": "assets/images/breeze.png",
            "ingredients": {
                "Jus de Citron": 35,
                "Sprite": 95,
                "Jus de Cranberry": 20
            },
            "tags": ["Léger", "Rafraîchissant", "Estival"]
        }
    ]
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        for mocktail in mocktails:
            # Проверяем, существует ли коктейль
            cursor.execute(
                "SELECT COUNT(*) FROM mocktails WHERE mocktail_id = %s", 
                (mocktail['mocktail_id'],)
            )
            if cursor.fetchone()[0] > 0:
                # Обновляем существующий коктейль
                query = """
                UPDATE mocktails
                SET name = %s, description = %s, image_url = %s
                WHERE mocktail_id = %s
                """
                values = (
                    mocktail['name'],
                    mocktail['description'],
                    mocktail['image_url'],
                    mocktail['mocktail_id']
                )
                cursor.execute(query, values)
                print(f"Обновлен коктейль: {mocktail['name']}")
                
                # Сначала удаляем связи с тегами и ингредиентами
                cursor.execute("DELETE FROM mocktail_tags WHERE mocktail_id = %s", (mocktail['mocktail_id'],))
                cursor.execute("DELETE FROM mocktail_ingredients WHERE mocktail_id = %s", (mocktail['mocktail_id'],))
            else:
                # Вставляем новый коктейль
                query = """
                INSERT INTO mocktails (mocktail_id, name, description, image_url)
                VALUES (%s, %s, %s, %s)
                """
                values = (
                    mocktail['mocktail_id'],
                    mocktail['name'],
                    mocktail['description'],
                    mocktail['image_url']
                )
                cursor.execute(query, values)
                print(f"Добавлен новый коктейль: {mocktail['name']}")
            
            # Добавляем теги
            for tag in mocktail['tags']:
                # Проверяем, существует ли уже такой тег
                cursor.execute("SELECT tag_id FROM tags WHERE name = %s", (tag,))
                result = cursor.fetchone()
                
                if result:
                    tag_id = result[0]
                else:
                    cursor.execute("INSERT INTO tags (name) VALUES (%s)", (tag,))
                    tag_id = cursor.lastrowid
                
                # Связываем тег с коктейлем
                cursor.execute(
                    "INSERT INTO mocktail_tags (mocktail_id, tag_id) VALUES (%s, %s)",
                    (mocktail['mocktail_id'], tag_id)
                )
            
            # Добавляем ингредиенты
            for ingredient_name, amount in mocktail['ingredients'].items():
                # Получаем ID ингредиента
                cursor.execute("SELECT ingredient_id FROM ingredients WHERE name = %s", (ingredient_name,))
                result = cursor.fetchone()
                
                if result:
                    ingredient_id = result[0]
                    # Связываем ингредиент с коктейлем
                    cursor.execute(
                        "INSERT INTO mocktail_ingredients (mocktail_id, ingredient_id, amount) VALUES (%s, %s, %s)",
                        (mocktail['mocktail_id'], ingredient_id, amount)
                    )
                else:
                    print(f"Внимание: Ингредиент '{ingredient_name}' не найден в базе данных")
        
        conn.commit()
        print(f"Обновление коктейлей завершено")
    
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при обновлении коктейлей: {e}")
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("Начинаем обновление данных в базе данных mocktail_machine...")
    # Обновляем структуру таблиц для поддержки рейтингов
    update_table_structure()
    update_ingredients()
    update_mocktails()
    print("Обновление данных завершено!")
