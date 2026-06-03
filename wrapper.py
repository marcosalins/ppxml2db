#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Wrapper script to simplify importing from PortfolioPerformance XML to SQLite
and exporting from SQLite back to PortfolioPerformance XML.

Automates database creation, schema initialization, and execution of
ppxml2db.py and db2ppxml.py.

Usage:

Import:
  python wrapper.py --exec import [path/to/input.xml] [--debug]
  (Defaults to C:\\Users\\malin\\OneDrive\\pp_file\\total_portfolio.xml if no input path provided)

Export:
  python wrapper.py --exec export --db <database_basename> --output [path/to/output.xml]
  (e.g., --db myportfolio for ./pp_databases/myportfolio.db)
  (Defaults output to ./pp_databases/<database_basename>.xml if no output path provided)
"""

import argparse
import os
import subprocess
import sqlite3
import glob
import sys
from pathlib import Path

# --- Configuration ---
DEFAULT_IMPORT_XML = Path("C:/Users/malin/OneDrive/pp_file/total_portfolio.xml")
DB_SUBDIRECTORY = "pp_databases"
SCRIPT_DIR = Path(__file__).parent.resolve()
DB_DIR = SCRIPT_DIR / DB_SUBDIRECTORY
PPXML2DB_SCRIPT = SCRIPT_DIR / "ppxml2db.py"
DB2PPXML_SCRIPT = SCRIPT_DIR / "db2ppxml.py"
SQL_SCHEMA_PATTERN = str(SCRIPT_DIR / "*.sql") # Use absolute path for glob

# --- Helper Functions ---

def run_subprocess(command_args):
    """Executes a subprocess command and handles potential errors."""
    try:
        print(f"Executing: {' '.join(map(str, command_args))}")
        result = subprocess.run(command_args, check=True, capture_output=True, text=True)
        print("Command successful.")
        if result.stdout:
            print("Output:\n", result.stdout)
        if result.stderr:
            # ppxml2db might print warnings/debug here if --debug is passed
            print("Stderr/Debug Output:\n", result.stderr)
        return True
    except FileNotFoundError:
        print(f"Error: Script not found at {command_args[1]}", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(map(str, command_args))}", file=sys.stderr)
        print(f"Return code: {e.returncode}", file=sys.stderr)
        if e.stdout:
            print(f"stdout:\n{e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"stderr:\n{e.stderr}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return False

def initialize_database_schema(db_path):
    """Applies all .sql schema files from the root directory to the database."""
    sql_files = sorted(glob.glob(SQL_SCHEMA_PATTERN)) # Ensure consistent order
    if not sql_files:
        print("Warning: No .sql schema files found in the script directory.", file=sys.stderr)
        return True # Not necessarily an error if schemas aren't needed/present

    print(f"Found schema files: {', '.join(os.path.basename(f) for f in sql_files)}")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print(f"Applying schema to {db_path}...")
        for sql_file_path in sql_files:
            print(f"  Executing schema from: {os.path.basename(sql_file_path)}")
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            # Filter out comments (starting with -- or #) and empty lines
            filtered_sql = "".join(
                line for line in lines
                if line.strip() and not line.strip().startswith('--') and not line.strip().startswith('#')
            )
            if filtered_sql: # Only execute if there's something left after filtering
                cursor.executescript(filtered_sql)
            else:
                print(f"  Skipping {os.path.basename(sql_file_path)} (empty or only comments).")
        conn.commit()
        print("Schema applied successfully.")
        return True
    except sqlite3.Error as e:
        print(f"Error applying schema from {sql_file_path}: {e}", file=sys.stderr)
        if conn:
            conn.rollback()
        return False
    except IOError as e:
        print(f"Error reading schema file {sql_file_path}: {e}", file=sys.stderr)
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def handle_import(input_xml_path_arg, debug=False):
    """Handles the import process."""
    input_xml_path = Path(input_xml_path_arg) if input_xml_path_arg else DEFAULT_IMPORT_XML

    if not input_xml_path.is_file():
        print(f"Error: Input XML file not found: {input_xml_path}", file=sys.stderr)
        sys.exit(1)

    # Derive DB name and path
    db_basename = input_xml_path.stem + ".db"
    db_path = DB_DIR / db_basename

    print(f"Input XML: {input_xml_path}")
    print(f"Target DB: {db_path}")

    # Ensure DB directory exists
    try:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Ensured database directory exists: {DB_DIR}")
    except OSError as e:
        print(f"Error creating database directory {DB_DIR}: {e}", file=sys.stderr)
        sys.exit(1)

    # Delete existing DB if it exists
    if db_path.exists():
        print(f"Database {db_path} already exists. Deleting...")
        try:
            db_path.unlink()
            print("Existing database deleted.")
        except OSError as e:
            print(f"Error deleting existing database {db_path}: {e}", file=sys.stderr)
            sys.exit(1)

    # Create new empty DB file and apply schema
    print(f"Creating new database file: {db_path}")
    try:
        # Connect to create the file, then close immediately.
        conn = sqlite3.connect(db_path)
        conn.close()
        print("Empty database file created.")
    except sqlite3.Error as e:
        print(f"Error creating empty database file {db_path}: {e}", file=sys.stderr)
        # Attempt cleanup if file was partially created
        if db_path.exists():
            try: db_path.unlink()
            except OSError: pass
        sys.exit(1)

    # Initialize schema
    if not initialize_database_schema(db_path):
        print("Failed to initialize database schema. Aborting import.", file=sys.stderr)
        # Attempt cleanup
        if db_path.exists():
            try: db_path.unlink()
            except OSError: pass
        sys.exit(1)

    # Run ppxml2db.py
    print("Running ppxml2db.py to import data...")
    import_command = [sys.executable, str(PPXML2DB_SCRIPT), str(input_xml_path), str(db_path)]
    # Pass debug flag if set
    if debug:
        import_command.append("--debug")
    if not run_subprocess(import_command):
        print("Import process failed during ppxml2db execution.", file=sys.stderr)
        sys.exit(1)

    print("Import process completed successfully.")

def handle_export(db_basename_arg, output_xml_path_arg, args):
    # Accept args as a parameter
    """Handles the export process."""
    # Handle database names with spaces by removing any quotes that might have been added
    db_basename_arg = db_basename_arg.strip('"\'')
    
    db_path = DB_DIR / (db_basename_arg + ".db")

    if not db_path.is_file():
        print(f"Error: Database file not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    # Determine output XML path
    if output_xml_path_arg:
        output_xml_path = Path(output_xml_path_arg)
    else:
        # Default output path next to the DB file
        output_xml_path = DB_DIR / (db_basename_arg + ".xml")
        print(f"No output XML path provided. Defaulting to: {output_xml_path}")

    # Ensure output directory exists (if specified in a subdirectory)
    try:
        output_xml_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error creating directory for output XML {output_xml_path.parent}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Source DB: {db_path}")
    print(f"Output XML: {output_xml_path}")

    # Run db2ppxml.py
    print("Running db2ppxml.py to export data...")
    export_command = [sys.executable, str(DB2PPXML_SCRIPT), str(db_path), str(output_xml_path)]
    
    # Pass debug flag to export script
    if args and hasattr(args, 'debug') and args.debug:
        export_command.append("--debug")
    
    # Pass treat_all_boolish_as_boolean flag if present
    if args and hasattr(args, 'treat_all_boolish_as_boolean') and args.treat_all_boolish_as_boolean:
        export_command.append("--treat-all-boolish-as-boolean")
    
    # Pass boolean_fields if specified
    if args and hasattr(args, 'boolean_fields') and args.boolean_fields:
        export_command.append("--boolean-fields")
        export_command.append(args.boolean_fields)
    
    if not run_subprocess(export_command):
        print("Export process failed during db2ppxml execution.", file=sys.stderr)
        sys.exit(1)

    print(f"Export process completed successfully. Output written to {output_xml_path}")

# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(
        description="Wrapper script for PortfolioPerformance XML/SQLite conversion.",
        formatter_class=argparse.RawDescriptionHelpFormatter # Preserve formatting in help
    )

    parser.add_argument(
        "--exec",
        required=True,
        choices=['import', 'export'],
        help="Execution mode: 'import' (XML to DB) or 'export' (DB to XML)."
    )

    # --- Import specific arguments ---
    import_group = parser.add_argument_group('Import Options (--exec import)')
    import_group.add_argument(
        'input_xml',
        nargs='?', # Optional positional argument
        type=str,
        help=f"Path to the input PortfolioPerformance XML file. Defaults to '{DEFAULT_IMPORT_XML}' if not provided."
    )

    # --- Export specific arguments ---
    export_group = parser.add_argument_group('Export Options (--exec export)')
    export_group.add_argument(
        '--db',
        type=str,
        help="Basename of the database file (without .db extension) located in the 'pp_databases' subdirectory (e.g., 'myportfolio'). Required for export."
    )
    # Changed from positional to named argument
    export_group.add_argument(
        '--output',
        dest='output_xml',
        type=str,
        help="Path for the output PortfolioPerformance XML file. Defaults to './pp_databases/<db_basename>.xml' if not provided."
    )

    # General debug flag
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging in the underlying import/export scripts."
    )
    
    # Add new boolean handling options
    parser.add_argument(
        "--treat-all-boolish-as-boolean",
        action="store_true",
        help="Treat all fields with boolean-like values as boolean elements in XML."
    )
    
    parser.add_argument(
        "--boolean-fields",
        help="Additional comma-separated list of taxonomy data field names to treat as boolean."
    )

    args = parser.parse_args()

    # Validate arguments based on mode
    if args.exec == 'export' and not args.db:
        parser.error("--db is required when --exec is 'export'")
    # Note: Input XML for import uses default if not provided, so no explicit check needed here.

    # Execute corresponding function
    if args.exec == 'import':
        handle_import(args.input_xml, args.debug)
    elif args.exec == 'export':
        # Pass arguments to handle_export
        handle_export(args.db, args.output_xml, args)
    else:
        # Should not happen due to 'choices' in argparse, but good practice
        print(f"Error: Invalid execution mode '{args.exec}'", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
