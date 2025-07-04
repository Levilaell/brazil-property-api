// MongoDB Initialization Script for Brazil Property API
// This script sets up the initial database structure and indexes

// Switch to the application database
db = db.getSiblingDB('brazil_property_dev');

// Create application user
db.createUser({
  user: 'brazil_property_user',
  pwd: 'brazil_property_pass',
  roles: [
    {
      role: 'readWrite',
      db: 'brazil_property_dev'
    }
  ]
});

// Create collections with validation
db.createCollection('properties', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['id', 'title', 'price', 'city', 'created_at'],
      properties: {
        id: {
          bsonType: 'string',
          description: 'Property ID - required'
        },
        title: {
          bsonType: 'string',
          description: 'Property title - required'
        },
        price: {
          bsonType: 'number',
          minimum: 0,
          description: 'Property price - required and must be positive'
        },
        city: {
          bsonType: 'string',
          description: 'City - required'
        },
        neighborhood: {
          bsonType: 'string',
          description: 'Neighborhood'
        },
        size: {
          bsonType: 'number',
          minimum: 0,
          description: 'Property size in square meters'
        },
        bedrooms: {
          bsonType: 'int',
          minimum: 0,
          description: 'Number of bedrooms'
        },
        bathrooms: {
          bsonType: 'int',
          minimum: 0,
          description: 'Number of bathrooms'
        },
        type: {
          bsonType: 'string',
          enum: ['apartment', 'house', 'condo', 'commercial', 'land'],
          description: 'Property type'
        },
        status: {
          bsonType: 'string',
          enum: ['active', 'sold', 'rented', 'inactive'],
          description: 'Property status'
        },
        source: {
          bsonType: 'string',
          description: 'Data source (zap, vivareal, etc.)'
        },
        url: {
          bsonType: 'string',
          description: 'Original property URL'
        },
        images: {
          bsonType: 'array',
          items: {
            bsonType: 'string'
          },
          description: 'Array of image URLs'
        },
        features: {
          bsonType: 'array',
          items: {
            bsonType: 'string'
          },
          description: 'Property features'
        },
        location: {
          bsonType: 'object',
          properties: {
            lat: {
              bsonType: 'number',
              minimum: -90,
              maximum: 90
            },
            lng: {
              bsonType: 'number',
              minimum: -180,
              maximum: 180
            },
            address: {
              bsonType: 'string'
            }
          }
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation timestamp - required'
        },
        updated_at: {
          bsonType: 'date',
          description: 'Last update timestamp'
        }
      }
    }
  }
});

db.createCollection('price_history', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['property_id', 'price', 'date', 'city'],
      properties: {
        property_id: {
          bsonType: 'string',
          description: 'Property ID - required'
        },
        price: {
          bsonType: 'number',
          minimum: 0,
          description: 'Price at this date - required'
        },
        date: {
          bsonType: 'date',
          description: 'Price date - required'
        },
        city: {
          bsonType: 'string',
          description: 'City - required'
        },
        neighborhood: {
          bsonType: 'string',
          description: 'Neighborhood'
        },
        price_per_sqm: {
          bsonType: 'number',
          minimum: 0,
          description: 'Price per square meter'
        }
      }
    }
  }
});

db.createCollection('market_analysis', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['city', 'analysis_date', 'metrics'],
      properties: {
        city: {
          bsonType: 'string',
          description: 'City - required'
        },
        neighborhood: {
          bsonType: 'string',
          description: 'Neighborhood (optional for city-wide analysis)'
        },
        analysis_date: {
          bsonType: 'date',
          description: 'Analysis date - required'
        },
        metrics: {
          bsonType: 'object',
          description: 'Market metrics - required'
        },
        updated_at: {
          bsonType: 'date',
          description: 'Last update timestamp'
        }
      }
    }
  }
});

// Create indexes for performance
print('Creating indexes...');

// Properties collection indexes
db.properties.createIndex({ 'id': 1 }, { unique: true });
db.properties.createIndex({ 'city': 1 });
db.properties.createIndex({ 'neighborhood': 1 });
db.properties.createIndex({ 'price': 1 });
db.properties.createIndex({ 'size': 1 });
db.properties.createIndex({ 'bedrooms': 1 });
db.properties.createIndex({ 'type': 1 });
db.properties.createIndex({ 'status': 1 });
db.properties.createIndex({ 'source': 1 });
db.properties.createIndex({ 'created_at': -1 });
db.properties.createIndex({ 'updated_at': -1 });

// Compound indexes for common queries
db.properties.createIndex({ 'city': 1, 'neighborhood': 1 });
db.properties.createIndex({ 'city': 1, 'type': 1 });
db.properties.createIndex({ 'city': 1, 'price': 1 });
db.properties.createIndex({ 'city': 1, 'bedrooms': 1 });
db.properties.createIndex({ 'price': 1, 'size': 1 });
db.properties.createIndex({ 'status': 1, 'created_at': -1 });

// Geospatial index for location-based queries
db.properties.createIndex({ 'location': '2dsphere' });

// Text index for search functionality
db.properties.createIndex({ 
  'title': 'text', 
  'neighborhood': 'text', 
  'features': 'text' 
}, {
  weights: {
    'title': 10,
    'neighborhood': 5,
    'features': 1
  },
  name: 'property_text_search'
});

// Price history collection indexes
db.price_history.createIndex({ 'property_id': 1, 'date': -1 });
db.price_history.createIndex({ 'city': 1, 'date': -1 });
db.price_history.createIndex({ 'city': 1, 'neighborhood': 1, 'date': -1 });
db.price_history.createIndex({ 'date': -1 });

// Market analysis collection indexes
db.market_analysis.createIndex({ 'city': 1, 'analysis_date': -1 });
db.market_analysis.createIndex({ 'city': 1, 'neighborhood': 1, 'analysis_date': -1 });
db.market_analysis.createIndex({ 'analysis_date': -1 });
db.market_analysis.createIndex({ 'updated_at': -1 });

print('Database initialization completed successfully!');
print('Collections created: properties, price_history, market_analysis');
print('Indexes created for optimal query performance');
print('Application user created: brazil_property_user');