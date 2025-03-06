from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import logging
import uuid
import json
import os
import threading

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='mocktail_server.log')
logger = logging.getLogger('mocktail_server')

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Storage paths
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

ORDERS_FILE = os.path.join(DATA_DIR, 'orders.json')
REVIEWS_FILE = os.path.join(DATA_DIR, 'reviews.json')
INGREDIENTS_FILE = os.path.join(DATA_DIR, 'ingredients.json')

# Thread lock for file operations
file_lock = threading.Lock()

# Initialize data files if they don't exist
def init_data_files():
    # Orders
    if not os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'w') as f:
            json.dump([], f)
    
    # Reviews
    if not os.path.exists(REVIEWS_FILE):
        with open(REVIEWS_FILE, 'w') as f:
            json.dump([], f)
    
    # Ingredients
    if not os.path.exists(INGREDIENTS_FILE):
        # Initialize with default ingredients
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
            json.dump(default_ingredients, f)

# Initialize data files at startup
init_data_files()

# Helper function to read data from file
def read_data(file_path):
    with file_lock:
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading from {file_path}: {str(e)}")
            return []

# Helper function to write data to file
def write_data(file_path, data):
    with file_lock:
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing to {file_path}: {str(e)}")

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint to check if the server is running"""
    return jsonify({"status": "online", "timestamp": time.time()})

# Endpoint to prepare a mocktail
@app.route('/prepare_mocktail', methods=['POST'])
def prepare_mocktail():
    """Endpoint to receive mocktail preparation requests"""
    try:
        data = request.json
        logger.info(f"Received order: {data}")
        
        # Validate required fields
        required_fields = ['mocktailName', 'ingredients', 'totalVolume']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"Missing required field: {field}"}), 400
        
        # Add order to our list with a timestamp and ID
        orders = read_data(ORDERS_FILE)
        
        order_id = str(uuid.uuid4())
        order = {
            "id": order_id,
            "timestamp": time.time(),
            "status": "received",
            "mocktailName": data['mocktailName'],
            "ingredients": data['ingredients'],
            "totalVolume": data['totalVolume']
        }
        orders.append(order)
        write_data(ORDERS_FILE, orders)
        
        # Update ingredient levels
        update_ingredient_levels(data['ingredients'])
        
        # Simulate processing time
        time.sleep(1)
        
        # Update order status
        for i, o in enumerate(orders):
            if o['id'] == order_id:
                orders[i]['status'] = "processing"
                break
        
        write_data(ORDERS_FILE, orders)
        
        return jsonify({
            "success": True,
            "message": "Mocktail order received and processing",
            "orderId": order_id
        })
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

# Endpoint to check order status
@app.route('/order_status/<order_id>', methods=['GET'])
def order_status(order_id):
    """Endpoint to check the status of an order"""
    try:
        orders = read_data(ORDERS_FILE)
        
        # Find the order with the given ID
        for order in orders:
            if order['id'] == order_id:
                return jsonify({
                    "success": True,
                    "order": order
                })
        
        return jsonify({"success": False, "message": "Order not found"}), 404
        
    except Exception as e:
        logger.error(f"Error checking order status: {str(e)}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

# Endpoint to get all orders
@app.route('/orders', methods=['GET'])
def get_orders():
    """Endpoint to get all orders"""
    orders = read_data(ORDERS_FILE)
    return jsonify({
        "success": True,
        "orders": orders
    })

# REVIEWS ENDPOINTS

# Get all reviews for a mocktail
@app.route('/reviews/<mocktail_id>', methods=['GET'])
def get_mocktail_reviews(mocktail_id):
    """Get all reviews for a specific mocktail"""
    try:
        reviews = read_data(REVIEWS_FILE)
        
        # Filter reviews for the specified mocktail
        mocktail_reviews = [r for r in reviews if r['mocktailId'] == mocktail_id]
        
        return jsonify({
            "success": True,
            "reviews": mocktail_reviews
        })
    except Exception as e:
        logger.error(f"Error fetching reviews: {str(e)}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

# Add a new review
@app.route('/reviews', methods=['POST'])
def add_review():
    """Add a new review for a mocktail"""
    try:
        data = request.json
        logger.info(f"Received review: {data}")
        
        # Validate required fields
        required_fields = ['mocktailId', 'userName', 'rating', 'comment']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"Missing required field: {field}"}), 400
        
        # Read existing reviews
        reviews = read_data(REVIEWS_FILE)
        
        # Create new review
        review_id = str(uuid.uuid4())
        review = {
            "id": review_id,
            "mocktailId": data['mocktailId'],
            "userName": data['userName'],
            "rating": data['rating'],
            "comment": data['comment'],
            "createdAt": data.get('createdAt', time.time())
        }
        
        reviews.append(review)
        write_data(REVIEWS_FILE, reviews)
        
        return jsonify({
            "success": True,
            "message": "Review added successfully",
            "reviewId": review_id
        })
    except Exception as e:
        logger.error(f"Error adding review: {str(e)}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

# INGREDIENTS ENDPOINTS

# Get ingredient levels
@app.route('/ingredients/levels', methods=['GET'])
def get_ingredient_levels():
    """Get the current levels of all ingredients"""
    try:
        ingredients = read_data(INGREDIENTS_FILE)
        return jsonify({
            "success": True,
            "ingredients": ingredients
        })
    except Exception as e:
        logger.error(f"Error fetching ingredient levels: {str(e)}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

# Check ingredient availability
@app.route('/ingredients/check', methods=['POST'])
def check_ingredients():
    """Check if there are enough ingredients for a mocktail"""
    try:
        data = request.json
        logger.info(f"Checking ingredients: {data}")
        
        if 'ingredients' not in data:
            return jsonify({"success": False, "message": "Missing required field: ingredients"}), 400
        
        ingredients = read_data(INGREDIENTS_FILE)
        requested_ingredients = data['ingredients']
        
        # Check if there are enough of each ingredient
        missing_ingredients = []
        for name, amount in requested_ingredients.items():
            # Find the ingredient by name
            ingredient_found = False
            for ingredient in ingredients:
                if ingredient['name'].lower() == name.lower():
                    ingredient_found = True
                    if ingredient['currentLevel'] < amount:
                        missing_ingredients.append(f"{name} (need {amount} ml, have {ingredient['currentLevel']} ml)")
                    break
            
            if not ingredient_found:
                missing_ingredients.append(f"{name} (not available)")
        
        if missing_ingredients:
            return jsonify({
                "available": False,
                "message": "Some ingredients are not available in sufficient quantity",
                "missingIngredients": missing_ingredients
            })
        
        return jsonify({
            "available": True,
            "message": "All ingredients are available"
        })
    except Exception as e:
        logger.error(f"Error checking ingredients: {str(e)}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

# Обновление уровня ингредиентов (для админ-панели)
@app.route('/ingredients/update', methods=['POST'])
def update_ingredient_levels_admin():
    """Update ingredient levels (admin function)"""
    try:
        data = request.json
        logger.info(f"Updating ingredient levels: {data}")
        
        if 'updatedLevels' not in data:
            return jsonify({"success": False, "message": "Missing required field: updatedLevels"}), 400
        
        updated_levels = data['updatedLevels']
        
        # Получаем текущие ингредиенты
        ingredients = read_data(INGREDIENTS_FILE)
        
        # Обновляем уровни
        for i, ingredient in enumerate(ingredients):
            if ingredient['ingredientId'] in updated_levels:
                ingredients[i]['currentLevel'] = updated_levels[ingredient['ingredientId']]
        
        # Сохраняем обновленные данные
        write_data(INGREDIENTS_FILE, ingredients)
        
        return jsonify({
            "success": True,
            "message": "Ingredient levels updated successfully"
        })
    except Exception as e:
        logger.error(f"Error updating ingredient levels: {str(e)}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

# Helper function to update ingredient levels
def update_ingredient_levels(used_ingredients):
    """Update ingredient levels after preparing a mocktail"""
    try:
        ingredients = read_data(INGREDIENTS_FILE)
        
        for name, amount in used_ingredients.items():
            for i, ingredient in enumerate(ingredients):
                if ingredient['name'].lower() == name.lower():
                    # Decrease the level, but don't go below 0
                    ingredients[i]['currentLevel'] = max(0, ingredient['currentLevel'] - amount)
                    break
        
        write_data(INGREDIENTS_FILE, ingredients)
        logger.info(f"Updated ingredient levels after using: {used_ingredients}")
    except Exception as e:
        logger.error(f"Error updating ingredient levels: {str(e)}")

if __name__ == '__main__':
    logger.info("Starting Mocktail Machine server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
