"""
MongoDB Handler for property data operations.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Iterator

import pymongo
from pymongo import MongoClient, errors

from .exceptions import DatabaseConnectionError, DatabaseOperationError, ValidationError


logger = logging.getLogger(__name__)


class MongoDBHandler:
    """
    MongoDB handler for property database operations.
    Provides comprehensive CRUD operations with connection management.
    """
    
    def __init__(self, config):
        """
        Initialize MongoDB handler.
        
        Args:
            config: Configuration object with database settings
            
        Raises:
            DatabaseConnectionError: If connection fails
        """
        self.config = config
        self.connected = False
        
        try:
            # Initialize MongoDB client
            self.client = MongoClient(
                self.config.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database
            db_name = self.config.get_database_name()
            self.database = self.client[db_name]
            
            self.connected = True
            logger.info(f"Connected to MongoDB database: {db_name}")
            
            # Create indexes
            self.create_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise DatabaseConnectionError(f"MongoDB connection failed: {e}")
    
    def get_collection(self, collection_name: str):
        """
        Get MongoDB collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            MongoDB collection object
        """
        return self.database[collection_name]
    
    def create_indexes(self) -> bool:
        """
        Create indexes for better query performance.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Properties collection indexes
            properties = self.get_collection('properties')
            properties.create_index('id', unique=True)
            properties.create_index('city')
            properties.create_index('neighborhood')
            properties.create_index('price')
            properties.create_index('size')
            properties.create_index('bedrooms')
            properties.create_index('created_at')
            properties.create_index([('city', 1), ('neighborhood', 1)])
            properties.create_index([('price', 1), ('size', 1)])
            
            # Price history collection indexes
            price_history = self.get_collection('price_history')
            price_history.create_index([('city', 1), ('neighborhood', 1), ('date', -1)])
            price_history.create_index('date')
            price_history.create_index('city')
            
            # Market analysis collection indexes
            market_analysis = self.get_collection('market_analysis')
            market_analysis.create_index('city')
            market_analysis.create_index('updated_at')
            
            logger.info("Database indexes created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            return False
    
    def ping(self) -> bool:
        """
        Test database connection.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Database ping failed: {e}")
            return False
    
    def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("MongoDB connection closed")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check.
        
        Returns:
            Health status dictionary
        """
        try:
            start_time = time.time()
            
            # Test connection
            connected = self.ping()
            response_time = time.time() - start_time
            
            # Get collection stats
            collections = {}
            for collection_name in ['properties', 'price_history', 'market_analysis']:
                try:
                    collection = self.get_collection(collection_name)
                    count = collection.count_documents({})
                    collections[collection_name] = {'count': count}
                except Exception as e:
                    collections[collection_name] = {'error': str(e)}
            
            # Get index information
            indexes = {}
            try:
                properties = self.get_collection('properties')
                indexes['properties'] = list(properties.list_indexes())
            except Exception as e:
                indexes['error'] = str(e)
            
            return {
                'connected': connected,
                'response_time': response_time,
                'collections': collections,
                'indexes': indexes,
                'database_name': self.config.get_database_name()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    # Property Operations
    def save_property(self, property_data: Dict[str, Any]) -> bool:
        """
        Save a single property.
        
        Args:
            property_data: Property data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate property data
            if not self._validate_property_data(property_data):
                return False
            
            # Add metadata
            property_data['created_at'] = datetime.utcnow()
            property_data['updated_at'] = datetime.utcnow()
            
            # Save to database
            collection = self.get_collection('properties')
            result = collection.insert_one(property_data)
            
            return bool(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error saving property: {e}")
            return False
    
    def save_properties(self, properties: List[Dict[str, Any]]) -> bool:
        """
        Save multiple properties in batch.
        
        Args:
            properties: List of property data dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not properties:
                return True
            
            # Validate and prepare properties
            valid_properties = []
            for prop in properties:
                if self._validate_property_data(prop):
                    prop['created_at'] = datetime.utcnow()
                    prop['updated_at'] = datetime.utcnow()
                    valid_properties.append(prop)
            
            if not valid_properties:
                return False
            
            # Batch insert
            collection = self.get_collection('properties')
            result = collection.insert_many(valid_properties, ordered=False)
            
            return len(result.inserted_ids) == len(valid_properties)
            
        except Exception as e:
            logger.error(f"Error saving properties: {e}")
            return False
    
    def upsert_property(self, property_data: Dict[str, Any]) -> bool:
        """
        Update existing property or insert if not exists.
        
        Args:
            property_data: Property data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self._validate_property_data(property_data):
                return False
            
            property_id = property_data.get('id')
            if not property_id:
                return False
            
            # Update metadata
            property_data['updated_at'] = datetime.utcnow()
            if 'created_at' not in property_data:
                property_data['created_at'] = datetime.utcnow()
            
            # Upsert
            collection = self.get_collection('properties')
            result = collection.replace_one(
                {'id': property_id},
                property_data,
                upsert=True
            )
            
            return result.acknowledged
            
        except Exception as e:
            logger.error(f"Error upserting property: {e}")
            return False
    
    def find_properties(
        self, 
        filters: Dict[str, Any], 
        page: int = 1, 
        limit: int = 50
    ) -> Iterator[Dict[str, Any]]:
        """
        Find properties with filters and pagination.
        
        Args:
            filters: MongoDB query filters
            page: Page number (1-based)
            limit: Number of results per page
            
        Returns:
            Iterator of property documents
        """
        try:
            collection = self.get_collection('properties')
            skip = (page - 1) * limit
            
            cursor = collection.find(filters).skip(skip).limit(limit)
            return cursor
            
        except Exception as e:
            logger.error(f"Error finding properties: {e}")
            return iter([])
    
    def remove_duplicates(self) -> int:
        """
        Remove duplicate properties based on ID.
        
        Returns:
            Number of duplicates removed
        """
        try:
            collection = self.get_collection('properties')
            
            # Find duplicates using aggregation
            pipeline = [
                {"$group": {
                    "_id": "$id",
                    "count": {"$sum": 1},
                    "docs": {"$push": "$_id"}
                }},
                {"$match": {"count": {"$gt": 1}}}
            ]
            
            duplicates = list(collection.aggregate(pipeline))
            total_removed = 0
            
            for duplicate in duplicates:
                # Keep the first document, remove the rest
                docs_to_remove = duplicate['docs'][1:]
                result = collection.delete_many({'_id': {'$in': docs_to_remove}})
                total_removed += result.deleted_count
            
            return total_removed
            
        except Exception as e:
            logger.error(f"Error removing duplicates: {e}")
            return 0
    
    # Price History Operations
    def save_price_history(self, price_entry: Dict[str, Any]) -> bool:
        """
        Save price history entry.
        
        Args:
            price_entry: Price history data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add metadata
            price_entry['created_at'] = datetime.utcnow()
            
            collection = self.get_collection('price_history')
            result = collection.insert_one(price_entry)
            
            return bool(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error saving price history: {e}")
            return False
    
    def get_price_history(self, city: str) -> Iterator[Dict[str, Any]]:
        """
        Get price history for a city.
        
        Args:
            city: City name
            
        Returns:
            Iterator of price history documents
        """
        try:
            collection = self.get_collection('price_history')
            cursor = collection.find({'city': city}).sort('date', -1)
            return cursor
            
        except Exception as e:
            logger.error(f"Error getting price history: {e}")
            return iter([])
    
    def get_price_history_by_neighborhood(
        self, 
        city: str, 
        neighborhood: str
    ) -> Iterator[Dict[str, Any]]:
        """
        Get price history for a specific neighborhood.
        
        Args:
            city: City name
            neighborhood: Neighborhood name
            
        Returns:
            Iterator of price history documents
        """
        try:
            collection = self.get_collection('price_history')
            filters = {'city': city, 'neighborhood': neighborhood}
            cursor = collection.find(filters).sort('date', -1)
            return cursor
            
        except Exception as e:
            logger.error(f"Error getting neighborhood price history: {e}")
            return iter([])
    
    def get_price_history_range(
        self, 
        city: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Iterator[Dict[str, Any]]:
        """
        Get price history within date range.
        
        Args:
            city: City name
            start_date: Start date
            end_date: End date
            
        Returns:
            Iterator of price history documents
        """
        try:
            collection = self.get_collection('price_history')
            filters = {
                'city': city,
                'date': {'$gte': start_date, '$lte': end_date}
            }
            cursor = collection.find(filters).sort('date', -1)
            return cursor
            
        except Exception as e:
            logger.error(f"Error getting price history range: {e}")
            return iter([])
    
    def aggregate_price_trends(self, city: str, months: int = 12) -> List[Dict[str, Any]]:
        """
        Aggregate price trends for analysis.
        
        Args:
            city: City name
            months: Number of months to analyze
            
        Returns:
            List of aggregated trend data
        """
        try:
            collection = self.get_collection('price_history')
            
            # Calculate date threshold
            threshold_date = datetime.utcnow() - timedelta(days=months * 30)
            
            pipeline = [
                {'$match': {
                    'city': city,
                    'date': {'$gte': threshold_date}
                }},
                {'$group': {
                    '_id': {
                        'year': {'$year': '$date'},
                        'month': {'$month': '$date'}
                    },
                    'avg_price': {'$avg': '$avg_price'},
                    'total_properties': {'$sum': '$total_properties'}
                }},
                {'$sort': {'_id.year': 1, '_id.month': 1}}
            ]
            
            return list(collection.aggregate(pipeline))
            
        except Exception as e:
            logger.error(f"Error aggregating price trends: {e}")
            return []
    
    # Market Analysis Operations
    def get_market_analysis(self, city: str) -> Dict[str, Any]:
        """
        Get comprehensive market analysis for a city.
        
        Args:
            city: City name
            
        Returns:
            Market analysis data
        """
        try:
            collection = self.get_collection('properties')
            
            pipeline = [
                {'$match': {'city': city}},
                {'$group': {
                    '_id': '$city',
                    'avg_price': {'$avg': '$price'},
                    'min_price': {'$min': '$price'},
                    'max_price': {'$max': '$price'},
                    'total_properties': {'$sum': 1},
                    'avg_size': {'$avg': '$size'}
                }}
            ]
            
            result = list(collection.aggregate(pipeline))
            return result[0] if result else {}
            
        except Exception as e:
            logger.error(f"Error getting market analysis: {e}")
            return {}
    
    def calculate_neighborhood_stats(self, city: str) -> List[Dict[str, Any]]:
        """
        Calculate statistics by neighborhood.
        
        Args:
            city: City name
            
        Returns:
            List of neighborhood statistics
        """
        try:
            collection = self.get_collection('properties')
            
            pipeline = [
                {'$match': {'city': city}},
                {'$group': {
                    '_id': '$neighborhood',
                    'avg_price': {'$avg': '$price'},
                    'median_price': {'$median': {'input': '$price'}},
                    'total_properties': {'$sum': 1},
                    'avg_size': {'$avg': '$size'}
                }},
                {'$sort': {'avg_price': -1}}
            ]
            
            return list(collection.aggregate(pipeline))
            
        except Exception as e:
            logger.error(f"Error calculating neighborhood stats: {e}")
            return []
    
    def find_trending_neighborhoods(self, city: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find trending neighborhoods based on growth.
        
        Args:
            city: City name
            limit: Maximum number of results
            
        Returns:
            List of trending neighborhoods
        """
        try:
            collection = self.get_collection('price_history')
            
            # Calculate 6-month growth trends
            threshold_date = datetime.utcnow() - timedelta(days=180)
            
            pipeline = [
                {'$match': {
                    'city': city,
                    'date': {'$gte': threshold_date}
                }},
                {'$group': {
                    '_id': '$neighborhood',
                    'recent_avg': {'$avg': {'$cond': [
                        {'$gte': ['$date', datetime.utcnow() - timedelta(days=90)]},
                        '$avg_price',
                        None
                    ]}},
                    'older_avg': {'$avg': {'$cond': [
                        {'$lt': ['$date', datetime.utcnow() - timedelta(days=90)]},
                        '$avg_price',
                        None
                    ]}}
                }},
                {'$project': {
                    'neighborhood': '$_id',
                    'growth_rate': {
                        '$multiply': [
                            {'$divide': [
                                {'$subtract': ['$recent_avg', '$older_avg']},
                                '$older_avg'
                            ]},
                            100
                        ]
                    }
                }},
                {'$sort': {'growth_rate': -1}},
                {'$limit': limit}
            ]
            
            return list(collection.aggregate(pipeline))
            
        except Exception as e:
            logger.error(f"Error finding trending neighborhoods: {e}")
            return []
    
    def get_investment_opportunities(self, city: str) -> List[Dict[str, Any]]:
        """
        Identify investment opportunities.
        
        Args:
            city: City name
            
        Returns:
            List of investment opportunities
        """
        try:
            collection = self.get_collection('properties')
            
            pipeline = [
                {'$match': {'city': city}},
                {'$group': {
                    '_id': '$neighborhood',
                    'avg_price': {'$avg': '$price'},
                    'total_properties': {'$sum': 1},
                    'avg_size': {'$avg': '$size'}
                }},
                {'$project': {
                    'neighborhood': '$_id',
                    'avg_price': 1,
                    'total_properties': 1,
                    'price_per_sqm': {'$divide': ['$avg_price', '$avg_size']},
                    'growth_potential': {'$rand': {}},  # Placeholder for complex calculation
                    'roi_score': {'$multiply': [{'$rand': {}}, 10]}  # Placeholder
                }},
                {'$sort': {'roi_score': -1}}
            ]
            
            return list(collection.aggregate(pipeline))
            
        except Exception as e:
            logger.error(f"Error getting investment opportunities: {e}")
            return []
    
    def aggregate_market_metrics(self, city: str) -> Dict[str, Any]:
        """
        Aggregate comprehensive market metrics.
        
        Args:
            city: City name
            
        Returns:
            Market metrics dictionary
        """
        try:
            collection = self.get_collection('properties')
            
            pipeline = [
                {'$match': {'city': city}},
                {'$group': {
                    '_id': None,
                    'total_value': {'$sum': '$price'},
                    'avg_days_on_market': {'$avg': 45},  # Placeholder
                    'market_velocity': {'$avg': 0.85}    # Placeholder
                }}
            ]
            
            result = list(collection.aggregate(pipeline))
            return result[0] if result else {}
            
        except Exception as e:
            logger.error(f"Error aggregating market metrics: {e}")
            return {}
    
    # Database Maintenance
    def cleanup_old_data(self, days_old: int = 365) -> int:
        """
        Clean up old data from database.
        
        Args:
            days_old: Number of days to keep
            
        Returns:
            Number of documents deleted
        """
        try:
            threshold_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Clean old price history
            collection = self.get_collection('price_history')
            result = collection.delete_many({'date': {'$lt': threshold_date}})
            
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return 0
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive database statistics.
        
        Returns:
            Database statistics
        """
        try:
            stats = self.database.command('dbStats')
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database statistics: {e}")
            return {}
    
    def get_index_stats(self, collection_name: str) -> List[Dict[str, Any]]:
        """
        Get index statistics for a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            List of index statistics
        """
        try:
            collection = self.get_collection(collection_name)
            return list(collection.index_stats())
            
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return []
    
    def _validate_property_data(self, property_data: Dict[str, Any]) -> bool:
        """
        Validate property data before saving.
        
        Args:
            property_data: Property data dictionary
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required fields
            required_fields = ['id', 'title', 'price']
            for field in required_fields:
                if field not in property_data:
                    logger.warning(f"Property missing required field: {field}")
                    return False
            
            # Check data types
            if not isinstance(property_data['price'], (int, float)):
                logger.warning("Property price must be numeric")
                return False
            
            # Check price is positive
            if property_data['price'] <= 0:
                logger.warning("Property price must be positive")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating property data: {e}")
            return False