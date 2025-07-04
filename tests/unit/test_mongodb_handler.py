"""
Tests for MongoDB Handler - Phase 3 of TDD Development.
Following TDD approach - write tests first, then implement.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from src.database import MongoDBHandler, DatabaseConnectionError, DatabaseOperationError
from src.config import DevelopmentConfig


@pytest.mark.unit
class TestMongoDBHandler:
    """Test MongoDB handler core functionality."""
    
    def test_connection_establishment(self):
        """Test MongoDB connection establishment."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = Mock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_client.return_value.admin.command.return_value = True
            
            handler = MongoDBHandler(config)
            
            assert handler.config == config
            assert handler.client is not None
            assert handler.database is not None
            assert handler.connected is True
    
    def test_connection_failure_handling(self):
        """Test MongoDB connection failure handling."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_client.side_effect = Exception("Connection failed")
            
            with pytest.raises(DatabaseConnectionError):
                MongoDBHandler(config)
    
    def test_database_selection(self):
        """Test database selection from configuration."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = Mock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_client.return_value.admin.command.return_value = True
            
            handler = MongoDBHandler(config)
            
            # Should use database name from config
            expected_db_name = config.get_database_name()
            mock_client.return_value.__getitem__.assert_called_with(expected_db_name)
    
    def test_collection_access(self):
        """Test collection access functionality."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            
            handler = MongoDBHandler(config)
            
            # Test getting collection
            collection = handler.get_collection('properties')
            assert collection == mock_collection
            mock_db.__getitem__.assert_called_with('properties')
    
    def test_index_creation(self):
        """Test index creation on collections."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            
            handler = MongoDBHandler(config)
            
            # Test creating indexes
            result = handler.create_indexes()
            assert result is True
            
            # Should have called create_index on collections
            assert mock_collection.create_index.called
    
    def test_connection_pool_management(self):
        """Test connection pool management."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_client.return_value.admin.command.return_value = True
            
            handler = MongoDBHandler(config)
            
            # Test connection health check
            health = handler.health_check()
            assert 'connected' in health
            assert 'collections' in health
            assert 'indexes' in health
    
    def test_database_ping(self):
        """Test database ping functionality."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_client.return_value.admin.command.return_value = True
            
            handler = MongoDBHandler(config)
            
            # Test ping
            result = handler.ping()
            assert result is True
            mock_client.return_value.admin.command.assert_called_with('ping')
    
    def test_close_connection(self):
        """Test closing database connection."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_client.return_value.admin.command.return_value = True
            
            handler = MongoDBHandler(config)
            assert handler.connected is True
            
            handler.close()
            assert handler.connected is False
            mock_client.return_value.close.assert_called_once()


@pytest.mark.unit
class TestPropertyOperations:
    """Test property-related database operations."""
    
    def test_save_single_property(self, sample_property_data):
        """Test saving a single property."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            mock_collection.insert_one.return_value.inserted_id = "obj_id_123"
            
            handler = MongoDBHandler(config)
            
            # Test saving property
            result = handler.save_property(sample_property_data)
            assert result is True
            mock_collection.insert_one.assert_called_once()
    
    def test_save_multiple_properties(self, sample_properties_list):
        """Test saving multiple properties."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            mock_collection.insert_many.return_value.inserted_ids = ["id1", "id2", "id3"]
            
            handler = MongoDBHandler(config)
            
            # Test batch saving
            result = handler.save_properties(sample_properties_list)
            assert result is True
            mock_collection.insert_many.assert_called_once()
    
    def test_upsert_existing_property(self, sample_property_data):
        """Test upserting (update or insert) existing property."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            mock_collection.replace_one.return_value.modified_count = 1
            mock_collection.replace_one.return_value.acknowledged = True
            
            handler = MongoDBHandler(config)
            
            # Test upsert
            result = handler.upsert_property(sample_property_data)
            assert result is True
            mock_collection.replace_one.assert_called_once()
    
    def test_find_properties_by_filters(self):
        """Test finding properties by filters."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            
            # Mock cursor with sample data
            mock_cursor = MagicMock()
            mock_cursor.__iter__.return_value = iter([{"id": "prop_1"}, {"id": "prop_2"}])
            mock_cursor.skip.return_value = mock_cursor
            mock_cursor.limit.return_value = mock_cursor
            mock_collection.find.return_value = mock_cursor
            
            handler = MongoDBHandler(config)
            
            # Test finding with filters
            filters = {"city": "Rio de Janeiro", "price": {"$gte": 500000}}
            results = handler.find_properties(filters)
            
            assert len(list(results)) == 2
            mock_collection.find.assert_called_once_with(filters)
    
    def test_find_properties_pagination(self):
        """Test finding properties with pagination."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            
            mock_cursor = MagicMock()
            mock_cursor.skip.return_value = mock_cursor
            mock_cursor.limit.return_value = mock_cursor
            mock_cursor.__iter__.return_value = iter([{"id": "prop_1"}])
            mock_collection.find.return_value = mock_cursor
            
            handler = MongoDBHandler(config)
            
            # Test pagination
            results = handler.find_properties({}, page=2, limit=10)
            
            mock_cursor.skip.assert_called_with(10)  # (page-1) * limit
            mock_cursor.limit.assert_called_with(10)
    
    def test_property_data_validation(self):
        """Test property data validation before saving."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_client.return_value.admin.command.return_value = True
            
            handler = MongoDBHandler(config)
            
            # Test invalid property data
            invalid_property = {"title": "No price or ID"}
            
            result = handler.save_property(invalid_property)
            assert result is False
    
    def test_remove_duplicate_properties(self):
        """Test removing duplicate properties."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            # Mock for aggregation to find duplicates
            mock_collection.aggregate.return_value = [
                {"_id": "prop_1", "count": 3, "docs": ["doc1", "doc2", "doc3"]},
                {"_id": "prop_2", "count": 2, "docs": ["doc4", "doc5"]}
            ]
            # Mock delete_many to return 2 (doc2,doc3) + 1 (doc5) = 3 deletes per call
            mock_collection.delete_many.return_value.deleted_count = 2  # First call removes 2 docs
            mock_collection.delete_many.side_effect = [
                MagicMock(deleted_count=2),  # First call: remove 2 docs for prop_1
                MagicMock(deleted_count=1),  # Second call: remove 1 doc for prop_2
            ]
            
            handler = MongoDBHandler(config)
            
            # Test duplicate removal
            result = handler.remove_duplicates()
            assert result == 3  # 2 + 1 = 3 total deletions
            mock_collection.delete_many.assert_called()


@pytest.mark.unit
class TestPriceHistoryOperations:
    """Test price history database operations."""
    
    def test_save_price_history_entry(self):
        """Test saving price history entry."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            mock_collection.insert_one.return_value.inserted_id = "hist_id_123"
            
            handler = MongoDBHandler(config)
            
            price_entry = {
                "date": datetime.now(),
                "city": "Rio de Janeiro",
                "neighborhood": "Copacabana",
                "avg_price": 750000,
                "total_properties": 150
            }
            
            result = handler.save_price_history(price_entry)
            assert result is True
            mock_collection.insert_one.assert_called_once()
    
    def test_get_price_history_by_city(self):
        """Test getting price history by city."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            
            mock_cursor = MagicMock()
            mock_cursor.__iter__.return_value = iter([{"date": "2024-01-01", "avg_price": 750000}])
            mock_cursor.sort.return_value = mock_cursor
            mock_collection.find.return_value = mock_cursor
            
            handler = MongoDBHandler(config)
            
            # Test getting history by city
            history = handler.get_price_history("Rio de Janeiro")
            assert len(list(history)) == 1
            mock_collection.find.assert_called_with({"city": "Rio de Janeiro"})
    
    def test_get_price_history_by_neighborhood(self):
        """Test getting price history by neighborhood."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            
            mock_cursor = MagicMock()
            mock_cursor.__iter__.return_value = iter([{"date": "2024-01-01", "avg_price": 750000}])
            mock_cursor.sort.return_value = mock_cursor
            mock_collection.find.return_value = mock_cursor
            
            handler = MongoDBHandler(config)
            
            # Test getting history by neighborhood
            history = handler.get_price_history_by_neighborhood("Rio de Janeiro", "Copacabana")
            assert len(list(history)) == 1
            
            expected_filter = {"city": "Rio de Janeiro", "neighborhood": "Copacabana"}
            mock_collection.find.assert_called_with(expected_filter)
    
    def test_get_price_history_date_range(self):
        """Test getting price history within date range."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            
            mock_cursor = MagicMock()
            mock_cursor.__iter__.return_value = iter([{"date": "2024-01-01", "avg_price": 750000}])
            mock_cursor.sort.return_value = mock_cursor
            mock_collection.find.return_value = mock_cursor
            
            handler = MongoDBHandler(config)
            
            # Test date range query
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now()
            
            history = handler.get_price_history_range("Rio de Janeiro", start_date, end_date)
            assert len(list(history)) == 1
    
    def test_aggregate_price_trends(self):
        """Test aggregating price trends."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            
            # Mock aggregation result
            mock_collection.aggregate.return_value = [
                {"_id": "2024-01", "avg_price": 750000, "growth": 2.5}
            ]
            
            handler = MongoDBHandler(config)
            
            # Test price trends aggregation
            trends = handler.aggregate_price_trends("Rio de Janeiro", months=6)
            assert len(trends) == 1
            assert trends[0]["avg_price"] == 750000
            mock_collection.aggregate.assert_called_once()


@pytest.mark.unit
class TestMarketAnalysisOperations:
    """Test market analysis database operations."""
    
    def test_get_market_analysis_data(self):
        """Test getting market analysis data."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            
            # Mock aggregation pipeline result
            mock_collection.aggregate.return_value = [
                {
                    "_id": "Rio de Janeiro",
                    "avg_price": 825000,
                    "total_properties": 1250,
                    "price_growth": 4.2
                }
            ]
            
            handler = MongoDBHandler(config)
            
            # Test market analysis
            analysis = handler.get_market_analysis("Rio de Janeiro")
            assert analysis["avg_price"] == 825000
            assert analysis["total_properties"] == 1250
    
    def test_calculate_neighborhood_stats(self):
        """Test calculating neighborhood statistics."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            
            mock_collection.aggregate.return_value = [
                {
                    "_id": "Copacabana",
                    "avg_price": 750000,
                    "median_price": 720000,
                    "total_properties": 150
                }
            ]
            
            handler = MongoDBHandler(config)
            
            # Test neighborhood stats
            stats = handler.calculate_neighborhood_stats("Rio de Janeiro")
            assert len(stats) == 1
            assert stats[0]["_id"] == "Copacabana"
    
    def test_find_trending_neighborhoods(self):
        """Test finding trending neighborhoods."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            
            mock_collection.aggregate.return_value = [
                {"neighborhood": "Leblon", "growth_rate": 8.5},
                {"neighborhood": "Ipanema", "growth_rate": 6.2}
            ]
            
            handler = MongoDBHandler(config)
            
            # Test trending neighborhoods
            trending = handler.find_trending_neighborhoods("Rio de Janeiro", limit=5)
            assert len(trending) == 2
            assert trending[0]["growth_rate"] == 8.5
    
    def test_get_investment_opportunities(self):
        """Test getting investment opportunities."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            
            mock_collection.aggregate.return_value = [
                {
                    "neighborhood": "Santa Teresa",
                    "avg_price": 450000,
                    "growth_potential": 9.2,
                    "roi_score": 8.5
                }
            ]
            
            handler = MongoDBHandler(config)
            
            # Test investment opportunities
            opportunities = handler.get_investment_opportunities("Rio de Janeiro")
            assert len(opportunities) == 1
            assert opportunities[0]["roi_score"] == 8.5
    
    def test_aggregate_market_metrics(self):
        """Test aggregating market metrics."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            
            mock_collection.aggregate.return_value = [
                {
                    "total_value": 1000000000,
                    "avg_days_on_market": 45,
                    "market_velocity": 0.85
                }
            ]
            
            handler = MongoDBHandler(config)
            
            # Test market metrics
            metrics = handler.aggregate_market_metrics("Rio de Janeiro")
            assert metrics["market_velocity"] == 0.85


@pytest.mark.unit
class TestDatabaseMaintenance:
    """Test database maintenance operations."""
    
    def test_cleanup_old_data(self):
        """Test cleaning up old data."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            mock_collection.delete_many.return_value.deleted_count = 100
            
            handler = MongoDBHandler(config)
            
            # Test cleanup
            days_old = 365
            deleted_count = handler.cleanup_old_data(days_old)
            assert deleted_count == 100
            mock_collection.delete_many.assert_called()
    
    def test_database_statistics(self):
        """Test getting database statistics."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = Mock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_client.return_value.admin.command.return_value = True
            mock_db.command.return_value = {
                "storageSize": 1000000,
                "dataSize": 800000,
                "indexSize": 200000
            }
            
            handler = MongoDBHandler(config)
            
            # Test statistics
            stats = handler.get_database_statistics()
            assert stats["storageSize"] == 1000000
            assert stats["dataSize"] == 800000
    
    def test_index_performance_stats(self):
        """Test getting index performance statistics."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.return_value.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_client.return_value.admin.command.return_value = True
            mock_collection.index_stats.return_value = [
                {"name": "city_1", "accesses": {"ops": 1000, "since": "2024-01-01"}}
            ]
            
            handler = MongoDBHandler(config)
            
            # Test index stats
            stats = handler.get_index_stats("properties")
            assert len(stats) == 1
            assert stats[0]["accesses"]["ops"] == 1000
    
    def test_connection_health_check(self):
        """Test comprehensive connection health check."""
        config = DevelopmentConfig()
        
        with patch('src.database.mongodb_handler.MongoClient') as mock_client:
            mock_client.return_value.admin.command.return_value = True
            
            handler = MongoDBHandler(config)
            
            # Test health check
            health = handler.health_check()
            assert health["connected"] is True
            assert "response_time" in health
            assert "collections" in health