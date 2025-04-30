# System Patterns: ppxml2db

## Architecture Overview
The ppxml2db system is structured around a bidirectional conversion workflow between PortfolioPerformance XML files and an SQLite database:

```
PortfolioPerformance XML ⟷ SQLite Database
       (ppxml2db.py)        (db2ppxml.py)
```

## Core Components

### 1. Database Schema
The database schema is defined through individual SQL files, with each file representing a distinct table/entity in the PortfolioPerformance data model:

- **Account-related**: `account.sql`, `account_attr.sql`
- **Security-related**: `security.sql`, `security_attr.sql`, `security_event.sql`, `security_prop.sql` 
- **Transaction-related**: `xact.sql`, `xact_unit.sql`, `xact_cross_entry.sql`
- **Price-related**: `price.sql`, `latest_price.sql`
- **Taxonomy-related**: `taxonomy.sql`, `taxonomy_assignment.sql`, `taxonomy_category.sql`, `taxonomy_data.sql`
- **Watchlist-related**: `watchlist.sql`, `watchlist_security.sql`
- **Configuration-related**: `config_entry.sql`, `config_set.sql`
- **Other entities**: `property.sql`, `attribute_type.sql`, `bookmark.sql`

The tables are designed to mirror PortfolioPerformance's internal object model, ensuring proper representation of the application's data structures.

### 2. Import Process (ppxml2db.py)
The import process handles:
- XML parsing using Python's XML libraries
- Extraction of data from the proprietary XStream format
- Insertion of data into the corresponding database tables
- Preservation of relationships between entities

### 3. Export Process (db2ppxml.py)
The export process handles:
- Querying the database for all stored entities
- Construction of XML elements in the XStream format
- Assembling the elements into the complete XML hierarchy
- Writing the XML document with proper structure and formatting

### 4. Database Utilities (dbhelper.py)
Provides common database operations and utilities for both import and export processes.

## Design Patterns

### Entity-Relationship Model
The database schema implements an entity-relationship model that closely mirrors PortfolioPerformance's internal object structure, with:
- Primary keys
- Foreign key relationships
- Property tables for flexible attribute storage

### Data Flow Pattern
The conversion processes follow a sequential data flow:
1. Parse/Read source format
2. Transform data between representations
3. Write to target format

### Command-Line Interface
Both tools use a simple command-line interface pattern, accepting source and target file paths as arguments.

## Implementation Paths

### XML to Database
1. Parse XML with focus on XStream's object references
2. Extract entities and relationships from the hierarchical structure
3. Map XML elements to database tables
4. Insert data while maintaining referential integrity

### Database to XML
1. Query tables in a structured order to rebuild the object hierarchy
2. Reconstruct XStream references between objects
3. Generate XML elements with proper attributes and structure
4. Assemble and format the complete XML document

## Error Handling
- Validation of input formats
- Database transaction management to ensure consistency
- Reporting of conversion issues
