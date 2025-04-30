# Technical Context: ppxml2db

## Technologies Used

### Programming Languages
- **Python 3**: Primary implementation language for both conversion scripts
- **SQL**: Used for database schema definition and queries

### Data Storage
- **SQLite**: Lightweight, file-based database used as the target format
- **XML**: Source/target format using XStream serialization

### Development Environment
- **Make**: Used for automation of database initialization and potentially other tasks
- **POSIX-like environment**: Recommended for utilizing the Makefile (Linux, macOS, WSL)

## Dependencies

### Python Dependencies
- Standard library modules:
  - XML parsing libraries (likely `xml.etree.ElementTree` or similar)
  - SQLite integration (`sqlite3`)
  - File handling utilities

### External Dependencies
- **PortfolioPerformance**: Version 0.70.3 or newer required (for "XML with 'id' attributes" format)
- **SQLite**: For database operations

## Technical Constraints

### PortfolioPerformance XML Format
- Custom XML format based on XStream serialization
- Not designed for human readability or direct manipulation
- Requires "XML with 'id' attributes" variant as introduced in PP 0.70.3
- Contains internal object references that must be preserved

### Database Design
- Schema closely mirrors PP's internal object model
- Tables defined individually in separate SQL files
- Relationships must preserve PP's object references

### Round-Trip Requirements
- Changes during import/export cycles should be minimal
- Known edge case with empty `<events/>` elements (null vs. empty list)
- Focus on preserving data semantics rather than exact XML representation

## Development Setup

### Required Tools
- Python 3.x
- SQLite
- Make (for utilizing the Makefile)
- Text editor or IDE
- PortfolioPerformance application (for generating/using XML files)

### Setup Process
1. Clone the repository
2. Ensure Python 3 is installed
3. Ensure SQLite is installed
4. (Optional) Install Make for database initialization

### Basic Workflow
1. Create an empty database: `make -B init DB=filename.db`
2. Import XML to database: `python3 ppxml2db.py source.xml target.db`
3. Export database to XML: `python3 db2ppxml.py source.db target.xml`
4. Compare files for differences: `diff -u original.xml exported.xml`

## Tool Usage Patterns

### Database Initialization
```
make -B init DB=dbname.db
```

### XML to Database Conversion
```
python3 ppxml2db.py input.xml output.db
```

### Database to XML Conversion
```
python3 db2ppxml.py input.db output.xml
```

### Data Querying
```
echo "SQL_QUERY" | sqlite3 database.db
```

## Known Limitations
- Investment Plans not supported
- Exchange Rates not supported
- Consumer Price Index objects not supported
- Some features or additional properties may be unsupported
- Edge case with empty vs. missing events elements
