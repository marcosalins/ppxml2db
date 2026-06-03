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

## Wrapper Script (`wrapper.py`)

The `wrapper.py` script provides a simplified command-line interface for the core conversion processes (`ppxml2db.py` and `db2ppxml.py`). It automates several steps, making the import and export workflows more user-friendly.

### Purpose

-   To streamline the process of importing PortfolioPerformance XML data into an SQLite database.
-   To streamline the process of exporting data from an SQLite database back into PortfolioPerformance XML format.
-   To automate database creation, deletion, and schema initialization.
-   To provide clear command-line arguments for specifying input/output files and modes.

### Functionality

-   **Argument Parsing**: Uses `argparse` to handle command-line arguments for selecting mode (`import` or `export`), specifying input/output files, database names, and enabling debug mode.
-   **Mode Selection**:
    -   `--exec import`: Triggers the import workflow.
    -   `--exec export`: Triggers the export workflow.
-   **Import Workflow (`handle_import`)**:
    -   Determines input XML file path (uses default if not provided).
    -   Derives the target SQLite database name and path (within `pp_databases/`).
    -   Ensures the `pp_databases` directory exists.
    -   **Deletes any existing database file** with the same name to ensure a clean import.
    -   Creates a new, empty SQLite database file.
    -   Calls `initialize_database_schema` to apply all `.sql` files found in the root directory to the new database.
    -   Executes `ppxml2db.py` as a subprocess, passing the input XML and target database paths.
    -   Optionally passes the `--debug` flag to `ppxml2db.py`.
-   **Export Workflow (`handle_export`)**:
    -   Requires the database basename (`--db` argument).
    -   Constructs the full path to the source SQLite database within `pp_databases/`.
    -   Determines the output XML file path (uses default `<db_basename>.xml` in `pp_databases/` if not provided).
    -   Ensures the output directory exists.
    -   Executes `db2ppxml.py` as a subprocess, passing the source database and target XML paths.
-   **Database Schema Initialization (`initialize_database_schema`)**:
    -   Finds all `.sql` files in the script's root directory.
    -   Connects to the specified database.
    -   Reads and executes the SQL commands from each file (ignoring comments and empty lines).
    -   Commits changes upon successful execution of all schema files.
-   **Subprocess Execution (`run_subprocess`)**:
    -   A helper function to run external Python scripts (`ppxml2db.py`, `db2ppxml.py`).
    -   Captures and prints stdout/stderr.
    -   Provides basic error handling for `FileNotFoundError` and `CalledProcessError`.

### Key Components & Configuration

-   **`DEFAULT_IMPORT_XML`**: Default path for the input XML file if none is specified during import.
-   **`DB_SUBDIRECTORY`**: Name of the subdirectory where databases are stored (`pp_databases`).
-   **`PPXML2DB_SCRIPT` / `DB2PPXML_SCRIPT`**: Paths to the core conversion scripts.
-   **`SQL_SCHEMA_PATTERN`**: Glob pattern to find schema files (`*.sql` in the root).

### Usage

**Import:**

```bash
# Import using default input XML (C:/Users/malin/OneDrive/pp_file/total_portfolio.xml)
python wrapper.py --exec import

# Import specific XML file
python wrapper.py --exec import path/to/your_portfolio.xml

# Import with debug output from ppxml2db.py
python wrapper.py --exec import path/to/your_portfolio.xml --debug
```
*Note: The import process will create a database named `<input_xml_stem>.db` in the `pp_databases` directory, overwriting any existing file with that name.*

**Export:**

```bash
# Export database 'my_portfolio.db' to default XML ('pp_databases/my_portfolio.xml')
python wrapper.py --exec export --db my_portfolio

# Export database 'another_portfolio.db' to a specific XML file
python wrapper.py --exec export --db another_portfolio path/to/output/exported_data.xml
```
*Note: The `--db` argument requires only the basename (e.g., `my_portfolio`), not the full path or `.db` extension.*

### Dependencies

-   Python 3
-   SQLite3 (usually included with Python)
-   `ppxml2db.py` script in the same directory.
-   `db2ppxml.py` script in the same directory.
-   `.sql` schema files in the same directory (for database initialization during import).

### Assumptions

-   The `wrapper.py`, `ppxml2db.py`, `db2ppxml.py`, and `.sql` schema files reside in the same directory.
-   The `pp_databases` subdirectory is intended for storing the generated SQLite databases and default XML exports.
-   The user has appropriate permissions to read input files, create/delete files in the `pp_databases` directory, and write output files.
## Known Limitations
- Investment Plans not supported
- Exchange Rates not supported
- Consumer Price Index objects not supported
- Some features or additional properties may be unsupported
- Edge case with empty vs. missing events elements
