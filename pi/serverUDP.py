from pymongo import MongoClient
from datetime import datetime, timedelta

# Connect to MongoDB on your laptop
# Replace '192.168.1.100' with your laptop's actual IP address
MONGO_HOST = '192.168.1.100'
MONGO_PORT = 27017
DATABASE_NAME = 'your_database_name'  # Replace with your actual database name

# Create MongoDB client
client = MongoClient(f'mongodb://{MONGO_HOST}:{MONGO_PORT}/')
db = client[DATABASE_NAME]
collection = db['yolo_objects']

# Example queries:

# 1. Get all objects
def get_all_objects():
    objects = list(collection.find())
    for obj in objects:
        print(f"Object: {obj['objectName']}, "
              f"Accuracy: {obj['accuracyEstimation']}, "
              f"Time: {obj['timestamp']}")
    return objects

# 2. Get objects by name
def get_objects_by_name(object_name):
    objects = list(collection.find({'objectName': object_name}))
    return objects

# 3. Get objects with accuracy above threshold
def get_high_accuracy_objects(min_accuracy=0.8):
    objects = list(collection.find({'accuracyEstimation': {'$gte': min_accuracy}}))
    return objects

# 4. Get recent objects (last N minutes)
def get_recent_objects(minutes=10):
    time_threshold = datetime.now() - timedelta(minutes=minutes)
    objects = list(collection.find({'timestamp': {'$gte': time_threshold}}))
    return objects

# 5. Count objects by name
def count_objects():
    pipeline = [
        {'$group': {
            '_id': '$objectName',
            'count': {'$sum': 1},
            'avg_accuracy': {'$avg': '$accuracyEstimation'}
        }},
        {'$sort': {'count': -1}}
    ]
    results = list(collection.aggregate(pipeline))
    for result in results:
        print(f"{result['_id']}: {result['count']} detections, "
              f"avg accuracy: {result['avg_accuracy']:.2f}")
    return results

# 6. Get latest detection of each object type
def get_latest_detections():
    pipeline = [
        {'$sort': {'timestamp': -1}},
        {'$group': {
            '_id': '$objectName',
            'latest_timestamp': {'$first': '$timestamp'},
            'accuracy': {'$first': '$accuracyEstimation'}
        }}
    ]
    results = list(collection.aggregate(pipeline))
    return results

# Example usage
if __name__ == '__main__':
    print("=== All Objects ===")
    get_all_objects()
    
    print("\n=== Person Detections ===")
    persons = get_objects_by_name('person')
    print(f"Found {len(persons)} person detections")
    
    print("\n=== High Accuracy Objects (>80%) ===")
    high_acc = get_high_accuracy_objects(0.8)
    print(f"Found {len(high_acc)} high accuracy detections")
    
    print("\n=== Recent Objects (last 10 min) ===")
    recent = get_recent_objects(10)
    print(f"Found {len(recent)} recent detections")
    
    print("\n=== Object Count Summary ===")
    count_objects()
    
    # Close connection when done
    client.close()