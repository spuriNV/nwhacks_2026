"""
MongoDB setup script for YOLO detections and interactions.
Run this once to set up the database and collections.
"""
from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime

# Configuration
MONGO_URI = "mongodb://localhost:27017"
DATABASE_NAME = "camera_system"


def setup_database():
    print("=" * 50)
    print("MongoDB Setup")
    print("=" * 50)

    # Connect to MongoDB
    print(f"\nConnecting to {MONGO_URI}...")
    client = MongoClient(MONGO_URI)

    # Test connection
    try:
        client.admin.command('ping')
        print("Connected successfully!")
    except Exception as e:
        print(f"Connection failed: {e}")
        print("\nMake sure MongoDB is running:")
        print("  - Docker: docker run -d -p 27017:27017 --name mongodb mongo")
        print("  - Or install MongoDB locally")
        return None

    # Get/create database
    db = client[DATABASE_NAME]
    print(f"\nDatabase: {DATABASE_NAME}")

    # ------------------------------
    # Collection 1: YOLO Objects
    # ------------------------------
    print("\n--- Setting up 'yolo_objects' collection ---")

    # Create collection with schema validation
    if "yolo_objects" not in db.list_collection_names():
        db.create_collection("yolo_objects", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["object_name", "accuracy", "timestamp"],
                "properties": {
                    "object_name": {
                        "bsonType": "string",
                        "description": "Name of detected object (e.g., 'person', 'chair')"
                    },
                    "accuracy": {
                        "bsonType": "double",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence score 0-1"
                    },
                    "camera_id": {
                        "bsonType": "string",
                        "description": "Which camera detected this"
                    },
                    "bounding_box": {
                        "bsonType": "object",
                        "properties": {
                            "x1": {"bsonType": "double"},
                            "y1": {"bsonType": "double"},
                            "x2": {"bsonType": "double"},
                            "y2": {"bsonType": "double"}
                        }
                    },
                    "timestamp": {
                        "bsonType": "date",
                        "description": "When the detection occurred"
                    }
                }
            }
        })
        print("  Created 'yolo_objects' collection with validation")
    else:
        print("  Collection 'yolo_objects' already exists")

    # Create indexes
    db.yolo_objects.create_index([("timestamp", DESCENDING)])
    db.yolo_objects.create_index([("object_name", ASCENDING)])
    db.yolo_objects.create_index([("camera_id", ASCENDING), ("timestamp", DESCENDING)])
    print("  Created indexes on timestamp, object_name, camera_id")

    # ------------------------------
    # Collection 2: Interactions (Button + Vibration)
    # ------------------------------
    print("\n--- Setting up 'interactions' collection ---")

    if "interactions" not in db.list_collection_names():
        db.create_collection("interactions", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["timestamp"],
                "properties": {
                    "button": {
                        "bsonType": "object",
                        "properties": {
                            "button_id": {"bsonType": "string"},
                            "num_presses": {"bsonType": "int"}
                        }
                    },
                    "vibration": {
                        "bsonType": "object",
                        "properties": {
                            "vibration_id": {"bsonType": "string"},
                            "vibration_level": {"bsonType": "int"}
                        }
                    },
                    "timestamp": {
                        "bsonType": "date",
                        "description": "When the interaction occurred"
                    }
                }
            }
        })
        print("  Created 'interactions' collection with validation")
    else:
        print("  Collection 'interactions' already exists")

    # Create indexes
    db.interactions.create_index([("timestamp", DESCENDING)])
    db.interactions.create_index([("button.button_id", ASCENDING)])
    db.interactions.create_index([("vibration.vibration_id", ASCENDING)])
    print("  Created indexes on timestamp, button_id, vibration_id")

    # ------------------------------
    # Insert sample data
    # ------------------------------
    print("\n--- Inserting sample data ---")

    # Sample YOLO detection
    sample_yolo = {
        "object_name": "person",
        "accuracy": 0.92,
        "camera_id": "cam1",
        "bounding_box": {
            "x1": 100.0,
            "y1": 50.0,
            "x2": 300.0,
            "y2": 400.0
        },
        "timestamp": datetime.utcnow()
    }
    result = db.yolo_objects.insert_one(sample_yolo)
    print(f"  Inserted sample YOLO detection: {result.inserted_id}")

    # Sample interaction
    sample_interaction = {
        "button": {
            "button_id": "BTN_A",
            "num_presses": 3
        },
        "vibration": {
            "vibration_id": "VIB_1",
            "vibration_level": 75
        },
        "timestamp": datetime.utcnow()
    }
    result = db.interactions.insert_one(sample_interaction)
    print(f"  Inserted sample interaction: {result.inserted_id}")

    # ------------------------------
    # Summary
    # ------------------------------
    print("\n" + "=" * 50)
    print("Setup complete!")
    print("=" * 50)
    print(f"\nDatabase: {DATABASE_NAME}")
    print(f"Collections:")
    for coll in db.list_collection_names():
        count = db[coll].count_documents({})
        print(f"  - {coll}: {count} documents")

    return db


if __name__ == "__main__":
    setup_database()
