"""
MongoDB client helper for inserting YOLO detections and interactions.
Import this in your camera script to save data to MongoDB.
"""
from pymongo import MongoClient
from datetime import datetime
from typing import Optional, List, Dict

# Configuration
MONGO_URI = "mongodb://localhost:27017"
DATABASE_NAME = "camera_system"


class MongoDBClient:
    def __init__(self, uri: str = MONGO_URI, db_name: str = DATABASE_NAME):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.yolo_objects = self.db.yolo_objects
        self.interactions = self.db.interactions

    def insert_yolo_detection(
        self,
        object_name: str,
        accuracy: float,
        camera_id: str,
        bounding_box: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ) -> str:
        """Insert a single YOLO detection."""
        doc = {
            "object_name": object_name,
            "accuracy": accuracy,
            "camera_id": camera_id,
            "timestamp": timestamp or datetime.utcnow()
        }
        if bounding_box:
            doc["bounding_box"] = bounding_box

        result = self.yolo_objects.insert_one(doc)
        return str(result.inserted_id)

    def insert_yolo_detections_batch(self, detections: List[Dict]) -> List[str]:
        """Insert multiple YOLO detections at once."""
        if not detections:
            return []

        # Add timestamp if not present
        for det in detections:
            if "timestamp" not in det:
                det["timestamp"] = datetime.utcnow()

        result = self.yolo_objects.insert_many(detections)
        return [str(id) for id in result.inserted_ids]

    def insert_interaction(
        self,
        button_id: Optional[str] = None,
        num_presses: Optional[int] = None,
        vibration_id: Optional[str] = None,
        vibration_level: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ) -> str:
        """Insert an interaction (button press and/or vibration)."""
        doc = {
            "timestamp": timestamp or datetime.utcnow()
        }

        if button_id is not None:
            doc["button"] = {
                "button_id": button_id,
                "num_presses": num_presses or 1
            }

        if vibration_id is not None:
            doc["vibration"] = {
                "vibration_id": vibration_id,
                "vibration_level": vibration_level or 0
            }

        result = self.interactions.insert_one(doc)
        return str(result.inserted_id)

    def get_recent_detections(self, limit: int = 100, camera_id: Optional[str] = None) -> List[Dict]:
        """Get recent YOLO detections."""
        query = {}
        if camera_id:
            query["camera_id"] = camera_id

        cursor = self.yolo_objects.find(query).sort("timestamp", -1).limit(limit)
        return list(cursor)

    def get_detection_counts(self, camera_id: Optional[str] = None) -> Dict[str, int]:
        """Get count of detections by object type."""
        match_stage = {}
        if camera_id:
            match_stage = {"$match": {"camera_id": camera_id}}

        pipeline = [
            match_stage,
            {"$group": {"_id": "$object_name", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ] if match_stage else [
            {"$group": {"_id": "$object_name", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]

        result = self.yolo_objects.aggregate(pipeline)
        return {doc["_id"]: doc["count"] for doc in result}

    def close(self):
        """Close the MongoDB connection."""
        self.client.close()


# Singleton instance for easy import
_client = None


def get_mongo_client() -> MongoDBClient:
    """Get or create the MongoDB client singleton."""
    global _client
    if _client is None:
        _client = MongoDBClient()
    return _client


# Example usage
if __name__ == "__main__":
    client = MongoDBClient()

    # Insert a detection
    det_id = client.insert_yolo_detection(
        object_name="person",
        accuracy=0.95,
        camera_id="cam1",
        bounding_box={"x1": 100.0, "y1": 50.0, "x2": 300.0, "y2": 400.0}
    )
    print(f"Inserted detection: {det_id}")

    # Insert an interaction
    int_id = client.insert_interaction(
        button_id="BTN_A",
        num_presses=2,
        vibration_id="VIB_1",
        vibration_level=50
    )
    print(f"Inserted interaction: {int_id}")

    # Get counts
    counts = client.get_detection_counts()
    print(f"Detection counts: {counts}")

    client.close()
