import mysql.connector
import json
import os

# Параметры подключения к базе данных
db_config = {
    'host': 'localhost',
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

# Импорт ингредиентов
def import_ingredients():
    # Проверяем наличие файла ингредиентов
    init_ingredients_file_if_needed()
    
    # Загрузка данных из JSON
    with open(INGREDIENTS_FILE, 'r') as f:
        ingredients = json.load(f)
    
    # Подключение к базе данных
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        # Очистка таблицы перед импортом
        cursor.execute("DELETE FROM ingredients")
        
        # Вставка данных в таблицу ingredients
        for ingredient in ingredients:
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
        
        # Сохранение изменений
        conn.commit()
        print(f"Импортировано {len(ingredients)} ингредиентов")
    
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при импорте ингредиентов: {e}")
    
    finally:
        cursor.close()
        conn.close()

# Импорт коктейлей из данных cocktail_manager.dart
def import_mocktails():
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
        # 1. Очистка таблиц перед импортом (в обратном порядке из-за ограничений внешнего ключа)
        cursor.execute("DELETE FROM mocktail_ingredients")
        cursor.execute("DELETE FROM mocktail_tags")
        cursor.execute("DELETE FROM mocktails")
        cursor.execute("DELETE FROM tags")
        
        # 2. Импорт коктейлей
        for mocktail in mocktails:
            # Вставка основной информации о коктейле
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
            
            # 3. Вставка тегов
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
            
            # 4. Вставка ингредиентов
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
        print(f"Импортировано {len(mocktails)} коктейлей")
    
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при импорте коктейлей: {e}")
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("Начинаем импорт данных в базу данных mocktail_machine...")
    import_ingredients()
    import_mocktails()
    print("Импорт данных завершен!")