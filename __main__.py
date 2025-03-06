from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='mocktail_server.log')
logger = logging.getLogger('mocktail_server')

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# In-memory storage for orders
orders = []

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint to check if the server is running"""
    return jsonify({"status": "online", "timestamp": time.time()})

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
        
        # Add order to our list with a timestamp
        order = {
            "id": len(orders) + 1,
            "timestamp": time.time(),
            "status": "received",
            **data
        }
        orders.append(order)
        
        # In a real system, here you would send signals to control the hardware
        # For example, activate pumps for each ingredient in the specified amounts
        
        # Simulate processing time
        time.sleep(1)
        
        # Update order status
        order["status"] = "processing"
        
        return jsonify({
            "success": True,
            "message": "Mocktail order received and processing",
            "orderId": order["id"]
        })
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route('/order_status/<int:order_id>', methods=['GET'])
def order_status(order_id):
    """Endpoint to check the status of an order"""
    try:
        # Find the order with the given ID
        for order in orders:
            if order["id"] == order_id:
                return jsonify({
                    "success": True,
                    "order": order
                })
        
        return jsonify({"success": False, "message": "Order not found"}), 404
        
    except Exception as e:
        logger.error(f"Error checking order status: {str(e)}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route('/orders', methods=['GET'])
def get_orders():
    """Endpoint to get all orders"""
    return jsonify({
        "success": True,
        "orders": orders
    })

if __name__ == '__main__':
    logger.info("Starting Mocktail Machine server...")
    app.run(host='0.0.0.0', port=5000, debug=True)