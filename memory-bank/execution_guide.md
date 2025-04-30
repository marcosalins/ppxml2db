# ppxml2db Execution Guide

This guide provides detailed instructions on how to set up and use the ppxml2db toolkit for converting PortfolioPerformance XML files to SQLite databases and vice versa.

## Prerequisites

Before using ppxml2db, ensure you have the following installed on your system:

1. **Python 3.x** - The primary programming language used for the conversion scripts
2. **SQLite** - The database engine used to store and query the data
3. **Make** - (Optional but recommended) Used for database initialization
4. **PortfolioPerformance** - Version 0.70.3 or newer, required for generating "XML with 'id' attributes"
5. **POSIX-like environment** - For using the Makefile (Linux, macOS, or Windows Subsystem for Linux)

## Setup

1. **Clone or download the repository**:
   ```
   git clone <repository-url>
   cd ppxml2db
   ```

2. **Verify Python installation**:
   ```
   python3 --version
   ```
   Ensure you're running Python 3.x.

3. **Verify SQLite installation**:
   ```
   sqlite3 --version
   ```

## Basic Workflow

### Step 1: Creating an Empty Database

Use the Makefile to create an empty database with all the necessary tables:

```
make -B init DB=portfolio.db
```

This command initializes a new SQLite database named `portfolio.db` with all the required tables defined in the SQL files.

### Step 2: Exporting XML from PortfolioPerformance

1. Open PortfolioPerformance application
2. Load your portfolio file
3. From the menu, select: **File → Save as → XML with "id" attributes**
4. Save the file (e.g., as `portfolio.xml`)

### Step 3: Importing XML to Database

Use the `ppxml2db.py` script to import the XML file into your database:

```
python3 ppxml2db.py portfolio.xml portfolio.db
```

This command parses the XML file and inserts the data into the SQLite database.

### Step 4: Querying the Database

You can now run SQL queries against the database:

```
echo "SELECT COUNT(*) FROM security;" | sqlite3 portfolio.db
```

Or open an interactive SQLite session:

```
sqlite3 portfolio.db
```

Then run queries at the SQLite prompt:

```sql
.tables                          -- List all tables
SELECT * FROM security LIMIT 5;  -- View first 5 securities
.schema security                 -- View table schema
```

Type `.quit` to exit the SQLite prompt.

### Step 5: Exporting Database Back to XML

To convert the database back to XML format (e.g., after making changes):

```
python3 db2ppxml.py portfolio.db portfolio_modified.xml
```

### Step 6: Verifying the Conversion

Compare the original and exported XML files to check for differences:

```
diff -u portfolio.xml portfolio_modified.xml
```

## Common Usage Examples

### Example 1: Counting Securities by Type

```
echo "SELECT type, COUNT(*) FROM security GROUP BY type;" | sqlite3 portfolio.db
```

### Example 2: Finding Transactions Above a Certain Amount

```
echo "SELECT * FROM xact WHERE units > 1000;" | sqlite3 portfolio.db
```

### Example 3: Updating Security Information

```
echo "UPDATE security SET name = 'New Company Name' WHERE isin = 'US0378331005';" | sqlite3 portfolio.db
```

After making changes, export back to XML:

```
python3 db2ppxml.py portfolio.db portfolio_updated.xml
```

## Complete Example Workflow

This workflow demonstrates the entire process using a sample file:

```bash
# 1. Create an empty database
make -B init DB=kommer.db

# 2. Assume you have exported kommer.xml from PortfolioPerformance

# 3. Import the XML into the database
python3 ppxml2db.py kommer.xml kommer.db

# 4. Run a query to see how many securities are in the portfolio
echo "SELECT COUNT(*) FROM security;" | sqlite3 kommer.db

# 5. Export the database back to XML
python3 db2ppxml.py kommer.db kommer_modified.xml

# 6. Check for differences
diff -u kommer.xml kommer_modified.xml
```

## Troubleshooting

### Common Issues

1. **"XML with 'id' attributes" format required**:
   Ensure you're exporting from PortfolioPerformance using the "XML with 'id' attributes" option, available in PP 0.70.3 and newer.

2. **Database initialization fails**:
   - Verify you have SQLite installed
   - Ensure the correct path to the database file
   - Check that you have write permissions in the target directory

3. **Import/Export errors**:
   - Check that your XML file is valid and not corrupted
   - Verify that the database schema matches what the scripts expect
   - Look for error messages that identify specific issues

4. **Round-trip differences**:
   - Some minor differences are expected, especially with empty event elements
   - Focus on whether the semantic content is preserved

## Support

If you encounter issues or have questions:
1. Check the README.md file for known issues
2. Submit detailed bug reports to the project's issue tracker, including:
   - A small, standalone XML file demonstrating the problem
   - The specific commands you ran
   - Any error messages received
