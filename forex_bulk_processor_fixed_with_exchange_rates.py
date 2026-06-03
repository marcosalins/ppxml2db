#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fixed Forex Bulk Processor for Portfolio Performance - WITH EXCHANGE RATES

This script properly accumulates forex transactions from multiple IB XML files by:

1. Creating the database once from the initial PP XML file
2. Adding forex transactions from each IB XML file to the same database
3. Creating xact_unit records with proper exchange rate information
4. Exporting the final accumulated database to PP XML at the end

Usage:
  python forex_bulk_processor_fixed.py [--pp-xml portfolio.xml] [--debug]
"""

import argparse
import glob
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# --- Configuration ---
SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_PP_XML = Path("D:/Projetos/Finance_data/IDE/vs_code/ib_pp_importer/portfolio_management.xml")
TRANSACTION_DATA_DIR = Path("D:/Projetos/Finance_data/Portfolio performance/transaction data")
WRAPPER_PATH = SCRIPT_DIR / "wrapper.py"
DEFAULT_CONFIG_PATH = SCRIPT_DIR / "forex_config.json"
TRACKING_DB_PATH = SCRIPT_DIR / "forex_import_tracking.db"
LOG_FILE_PATH = SCRIPT_DIR / "forex_bulk_processor_fixed.log"
DB_DIR = SCRIPT_DIR / "pp_databases"

# --- Currency Mapping ---
def map_ib_currency_to_pp(ib_currency):
    """Map IB currency codes to Portfolio Performance currency codes"""
    currency_mapping = {
        'CNH': 'CNY',  # Chinese Yuan Offshore -> Chinese Yuan
        'GBP': 'GBX',  # British Pound -> British Pence
    }
    return currency_mapping.get(ib_currency, ib_currency)

# --- Logging Setup ---
def setup_logging(debug=False):
    """Setup logging configuration"""
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s | %(levelname)-5s | %(message)s')
    
    # Setup file handler
    file_handler = logging.FileHandler(LOG_FILE_PATH, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Setup logger
    logger = logging.getLogger('forex_bulk_processor_fixed')
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# --- Database Functions ---
def init_tracking_database():
    """Initialize the tracking database for processed files"""
    conn = sqlite3.connect(TRACKING_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            file_size INTEGER NOT NULL,
            file_mtime REAL NOT NULL,
            processed_at TEXT NOT NULL,
            success BOOLEAN NOT NULL,
            error_message TEXT,
            transactions_count INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

def is_file_processed(file_path):
    """Check if a file has already been successfully processed"""
    conn = sqlite3.connect(TRACKING_DB_PATH)
    cursor = conn.cursor()
    
    # Get file stats
    file_stat = os.stat(file_path)
    file_size = file_stat.st_size
    file_mtime = file_stat.st_mtime
    
    cursor.execute('''
        SELECT success FROM processed_files 
        WHERE file_path = ? AND file_size = ? AND file_mtime = ?
    ''', (str(file_path), file_size, file_mtime))
    
    result = cursor.fetchone()
    conn.close()
    
    return result and result[0]  # Return True if found and successful

def mark_file_processed(file_path, success, error_message=None, transactions_count=0):
    """Mark a file as processed in the tracking database"""
    conn = sqlite3.connect(TRACKING_DB_PATH)
    cursor = conn.cursor()
    
    # Get file stats
    file_stat = os.stat(file_path)
    file_size = file_stat.st_size
    file_mtime = file_stat.st_mtime
    
    # Current timestamp
    processed_at = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO processed_files 
        (file_path, file_size, file_mtime, processed_at, success, error_message, transactions_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (str(file_path), file_size, file_mtime, processed_at, success, error_message, transactions_count))
    
    conn.commit()
    conn.close()

# --- File Discovery Functions ---
def discover_ib_xml_files():
    """Discover all IB XML files in the transaction data directory"""
    logger = logging.getLogger('forex_bulk_processor_fixed')
    
    if not TRANSACTION_DATA_DIR.exists():
        logger.error(f"Transaction data directory not found: {TRANSACTION_DATA_DIR}")
        return []
    
    xml_files = []
    
    # Find all directories starting with "IB"
    ib_dirs = [d for d in TRANSACTION_DATA_DIR.iterdir() 
               if d.is_dir() and d.name.startswith("IB")]
    
    logger.info(f"Found {len(ib_dirs)} IB directories: {[d.name for d in ib_dirs]}")
    
    # Find all XML files in these directories
    for ib_dir in ib_dirs:
        xml_pattern = str(ib_dir / "*.xml")
        dir_xml_files = glob.glob(xml_pattern)
        xml_files.extend([Path(f) for f in dir_xml_files])
        logger.debug(f"Found {len(dir_xml_files)} XML files in {ib_dir.name}")
    
    # Sort alphabetically
    xml_files.sort(key=lambda x: str(x))
    
    logger.info(f"Total IB XML files discovered: {len(xml_files)}")
    return xml_files

def filter_unprocessed_files(xml_files):
    """Filter out files that have already been processed"""
    logger = logging.getLogger('forex_bulk_processor_fixed')
    
    unprocessed = []
    for xml_file in xml_files:
        if not is_file_processed(xml_file):
            unprocessed.append(xml_file)
        else:
            logger.debug(f"Skipping already processed file: {xml_file.name}")
    
    logger.info(f"New files to process: {len(unprocessed)} out of {len(xml_files)} total")
    return unprocessed

# --- Backup Functions ---
def create_backup(pp_xml_path):
    """Create a backup of the PP XML file"""
    logger = logging.getLogger('forex_bulk_processor_fixed')
    
    if not pp_xml_path.exists():
        logger.error(f"PP XML file not found: {pp_xml_path}")
        return None
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{pp_xml_path.stem}_backup_{timestamp}{pp_xml_path.suffix}"
    backup_path = pp_xml_path.parent / backup_name
    
    try:
        shutil.copy2(pp_xml_path, backup_path)
        logger.info(f"Backup created: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return None

# --- Database Import/Export Functions ---
def import_pp_xml_to_db_once(pp_xml_path, debug=False):
    """Import PP XML to database once using wrapper.py"""
    logger = logging.getLogger('forex_bulk_processor_fixed')
    
    # Extract basename without extension
    db_basename = Path(pp_xml_path).stem
    db_path = DB_DIR / f"{db_basename}.db"

    # Build import command
    import_cmd = [
        sys.executable,
        str(WRAPPER_PATH),
        "--exec",
        "import",
        str(pp_xml_path),
    ]
    if debug:
        import_cmd.append("--debug")

    # Run command
    try:
        logger.info(f"Importing PP XML to database: {db_path}")
        result = subprocess.run(import_cmd, check=True, capture_output=True, text=True)
        logger.info(f"Successfully imported {pp_xml_path} to {db_path}")
        return db_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to import PP XML: {e}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        raise RuntimeError(f"Failed to import PP XML: {pp_xml_path}")

def export_db_to_pp_xml_final(db_path, output_xml_path, debug=False):
    """Export database to PP XML using db2ppxml.py directly"""
    logger = logging.getLogger('forex_bulk_processor_fixed')
    
    # Build export command - call db2ppxml.py directly
    export_cmd = [
        sys.executable,
        str(SCRIPT_DIR / 'db2ppxml.py'),
        str(db_path),
        str(output_xml_path),
    ]
    if debug:
        export_cmd.append("--debug")

    # Run command
    try:
        logger.info(f"Exporting database to PP XML: {output_xml_path}")
        result = subprocess.run(export_cmd, check=True, capture_output=True, text=True)
        logger.info(f"Successfully exported database to {output_xml_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to export to PP XML: {e}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        raise RuntimeError(f"Failed to export to PP XML: {output_xml_path}")

# --- Forex Processing Functions (copied from forex_processor.py) ---
def load_config(config_path):
    """Load and validate the configuration file"""
    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        # Validate required fields
        if "account_mappings" not in config:
            raise ValueError("Configuration must contain 'account_mappings' section")

        if "fallback_strategy" not in config:
            config["fallback_strategy"] = "error"

        return config
    except FileNotFoundError:
        logger = logging.getLogger('forex_bulk_processor_fixed')
        logger.error(f"Configuration file not found: {config_path}")
        raise

def get_max_xmlid(conn):
    """Gets the maximum _xmlid value from the xact table"""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(_xmlid) FROM xact")
    result = cursor.fetchone()[0]
    return result if result is not None else 0

def get_max_order(conn):
    """Gets the maximum _order value from the xact table"""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(_order) FROM xact")
    result = cursor.fetchone()[0]
    return result if result is not None else 0

def transaction_already_exists(conn, trade_id):
    """Check if a transaction with this IB Trade ID already exists"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM xact WHERE note LIKE ? AND source = 'IB Flex Import'",
        (f"%Trade ID: {trade_id}%",)
    )
    count = cursor.fetchone()[0]
    return count > 0

def get_currency_account(conn, ib_account_id, currency_code, config):
    """Find the appropriate account UUID for a given IB account ID and currency"""
    logger = logging.getLogger('forex_bulk_processor_fixed')
    
    # Get the pattern for this IB account
    if ib_account_id not in config["account_mappings"]:
        if config["fallback_strategy"] == "error":
            raise ValueError(f"No mapping found for IB account ID: {ib_account_id}")
        elif config["fallback_strategy"] == "skip":
            return None

    pattern = config["account_mappings"][ib_account_id]["pattern"]
    
    # Map IB currency to PP currency
    pp_currency = map_ib_currency_to_pp(currency_code)
    
    # Try both naming patterns due to database inconsistency
    account_name_pp = pattern.replace("{currency}", pp_currency)  # For GBX accounts
    account_name_ib = pattern.replace("{currency}", currency_code)  # For CNH accounts

    logger.debug(f"Looking for account: '{account_name_pp}' or '{account_name_ib}' with currency='{pp_currency}' (IB currency: {currency_code})")

    cursor = conn.cursor()
    
    # Try Pattern 1 first (PP currency in name)
    cursor.execute(
        "SELECT uuid FROM account WHERE name = ? AND currency = ?",
        (account_name_pp, pp_currency),
    )
    result = cursor.fetchone()

    if result:
        logger.debug(f"Found account UUID (PP pattern): {result[0]}")
        return result[0]

    # Try Pattern 2 (IB currency in name)
    cursor.execute(
        "SELECT uuid FROM account WHERE name = ? AND currency = ?",
        (account_name_ib, pp_currency),
    )
    result = cursor.fetchone()

    if result:
        logger.debug(f"Found account UUID (IB pattern): {result[0]}")
        return result[0]

    # If not found, try a more flexible search
    cursor.execute(
        "SELECT uuid FROM account WHERE name LIKE ? AND currency = ?",
        (f"%{ib_account_id}%{currency_code}", pp_currency),
    )
    result = cursor.fetchone()

    if result:
        logger.debug(f"Found account UUID via flexible search: {result[0]}")
        return result[0]

    # If still not found, handle according to fallback strategy
    if config["fallback_strategy"] == "error":
        raise ValueError(
            f"No account found for IB account {ib_account_id} with currency {currency_code} (mapped to {pp_currency})"
        )

    return None

def insert_transfer_out(conn, uuid_str, account_uuid, date_str, currency, amount, note, source, updated_at, xmlid, order, fees=0):
    """Inserts a TRANSFER_OUT transaction"""
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT INTO xact (
        uuid, acctype, account, date, currency, amount, security, shares, 
        note, source, updatedAt, type, fees, taxes, _xmlid, _order
    ) VALUES (?, 'account', ?, ?, ?, ?, NULL, 0, ?, ?, ?, 'TRANSFER_OUT', ?, 0, ?, ?)
    """,
        (uuid_str, account_uuid, date_str, currency, amount, note, source, updated_at, fees, xmlid, order),
    )
    return cursor.lastrowid

def insert_transfer_in(conn, uuid_str, account_uuid, date_str, currency, amount, note, source, updated_at, xmlid, order, fees=0):
    """Inserts a TRANSFER_IN transaction"""
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT INTO xact (
        uuid, acctype, account, date, currency, amount, security, shares, 
        note, source, updatedAt, type, fees, taxes, _xmlid, _order
    ) VALUES (?, 'account', ?, ?, ?, ?, NULL, 0, ?, ?, ?, 'TRANSFER_IN', ?, 0, ?, ?)
    """,
        (uuid_str, account_uuid, date_str, currency, amount, note, source, updated_at, fees, xmlid, order),
    )
    return cursor.lastrowid

def insert_cross_entry(conn, from_acc, from_xact, to_acc, to_xact):
    """Inserts a cross-entry link"""
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT INTO xact_cross_entry (
        type, from_acc, from_xact, to_acc, to_xact
    ) VALUES ('account-transfer', ?, ?, ?, ?)
    """,
        (from_acc, from_xact, to_acc, to_xact),
    )
    return cursor.lastrowid

def insert_xact_unit_record(conn, transaction_uuid, transaction_currency, transaction_amount, 
                           forex_currency, forex_amount, exchange_rate):
    """Create a xact_unit record for a forex transaction with exchange rate"""
    cursor = conn.cursor()
    
    # Insert the xact_unit record
    cursor.execute("""
        INSERT INTO xact_unit (
            xact, type, amount, currency, forex_amount, forex_currency, exchangeRate
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        transaction_uuid,
        "GROSS_VALUE",  # Standard type for forex transactions
        transaction_amount,
        transaction_currency,
        forex_amount,
        forex_currency,
        exchange_rate
    ))
    return cursor.lastrowid

def calculate_exchange_rate(from_amount, to_amount):
    """Calculate exchange rate from transaction amounts"""
    if from_amount == 0:
        return "1"
    
    # Exchange rate = to_amount / from_amount
    rate = to_amount / from_amount
    return str(rate)

def process_single_forex_transaction(conn, transaction, config, next_xmlid, next_order):
    """Process a single forex transaction and return True if successful"""
    logger = logging.getLogger('forex_bulk_processor_fixed')

    # Extract IB Trade ID
    trade_id = transaction.get("tradeID")
    
    # Check for duplicates first
    if transaction_already_exists(conn, trade_id):
        logger.debug(f"Skipping duplicate transaction {trade_id}")
        return False

    # Extract IB account ID
    ib_account_id = transaction.get("accountId")

    # Extract currencies from symbol (e.g., "USD.HKD")
    currencies = transaction.get("symbol").split(".")
    first_currency = currencies[0]
    second_currency = currencies[1]

    # Determine source and target currencies based on buySell flag
    buy_sell = transaction.get("buySell")

    if buy_sell == "BUY":
        source_currency = second_currency
        target_currency = first_currency
    elif buy_sell == "SELL":
        source_currency = first_currency
        target_currency = second_currency
    else:
        logger.warning(f"Unknown buySell value '{buy_sell}', defaulting to BUY")
        source_currency = second_currency
        target_currency = first_currency

    logger.debug(
        f"Processing forex transaction: {ib_account_id} {first_currency}.{second_currency} "
        f"(Trade ID: {trade_id}, {buy_sell})"
    )

    # Find matching PP accounts
    source_account_uuid = get_currency_account(conn, ib_account_id, source_currency, config)
    target_account_uuid = get_currency_account(conn, ib_account_id, target_currency, config)

    # Skip if can't find accounts
    if not source_account_uuid or not target_account_uuid:
        logger.warning(f"Skipping forex transaction {trade_id}: Account not found")
        return False

    # Format date
    trade_date = transaction.get("tradeDate")
    formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}T00:00"

    # Extract and process amounts
    proceeds_amount = abs(float(transaction.get("proceeds")))
    quantity_amount = abs(float(transaction.get("quantity")))

    if buy_sell == "BUY":
        source_amount = proceeds_amount
        target_amount = quantity_amount
    else:
        source_amount = quantity_amount
        target_amount = proceeds_amount

    # Convert to cents
    source_amount = round(source_amount * 100)
    target_amount = round(target_amount * 100)

    # Ensure minimum 1 cent
    if source_amount == 0 and proceeds_amount > 0:
        source_amount = 1
    if target_amount == 0 and quantity_amount > 0:
        target_amount = 1

    # Create description
    description = f"Forex {source_currency} to {target_currency} (Trade ID: {trade_id})"

    # Generate UUIDs
    transfer_out_uuid = str(uuid.uuid4())
    transfer_in_uuid = str(uuid.uuid4())

    # Current timestamp
    now = datetime.now().isoformat() + "Z"

    # Handle commissions - use mapped currencies for storage
    commission_amount = 0
    commission_currency = transaction.get("ibCommissionCurrency")
    source_fees = 0
    target_fees = 0

    if transaction.get("ibCommission") and commission_currency:
        commission_amount = abs(float(transaction.get("ibCommission")))
        commission_amount = round(commission_amount * 100)

        if commission_currency == source_currency:
            source_fees = commission_amount
        elif commission_currency == target_currency:
            target_fees = commission_amount

    # Map currencies for database storage
    source_pp_currency = map_ib_currency_to_pp(source_currency)
    target_pp_currency = map_ib_currency_to_pp(target_currency)

    # Insert transactions with mapped currencies
    insert_transfer_out(
        conn, transfer_out_uuid, source_account_uuid, formatted_date,
        source_pp_currency, source_amount, description, "IB Flex Import",
        now, next_xmlid, next_order, fees=source_fees,
    )

    insert_transfer_in(
        conn, transfer_in_uuid, target_account_uuid, formatted_date,
        target_pp_currency, target_amount, description, "IB Flex Import",
        now, next_xmlid + 1, next_order + 1, fees=target_fees,
    )

    # Create cross-entry link
    insert_cross_entry(
        conn, source_account_uuid, transfer_out_uuid,
        target_account_uuid, transfer_in_uuid,
    )

    # Create xact_unit records with exchange rate information
    logger.debug("Creating xact_unit records with exchange rates...")
    
    # Calculate exchange rates
    # For TRANSFER_OUT: rate = target_amount / source_amount
    # For TRANSFER_IN: rate = source_amount / target_amount
    out_exchange_rate = calculate_exchange_rate(source_amount, target_amount)
    in_exchange_rate = calculate_exchange_rate(target_amount, source_amount)
    
    # Create xact_unit for TRANSFER_OUT (source -> target)
    insert_xact_unit_record(
        conn, transfer_out_uuid, source_pp_currency, source_amount,
        target_pp_currency, target_amount, out_exchange_rate
    )
    
    # Create xact_unit for TRANSFER_IN (target <- source)
    insert_xact_unit_record(
        conn, transfer_in_uuid, target_pp_currency, target_amount,
        source_pp_currency, source_amount, in_exchange_rate
    )
    
    logger.debug(f"Created xact_unit records with exchange rates: {out_exchange_rate}, {in_exchange_rate}")
    logger.debug(f"Created transfer pair with IDs: {next_xmlid}, {next_xmlid + 1}")
    return True

def process_ib_xml_file(ib_xml_path, db_path, config_path):
    """Process forex transactions from a single IB XML file and add to database"""
    logger = logging.getLogger('forex_bulk_processor_fixed')
    
    # Load configuration
    config = load_config(config_path)

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Parse IB Flex XML
        tree = ET.parse(ib_xml_path)
        root = tree.getroot()

        # Find forex transactions (exclude trade cancellations)
        forex_transactions = []
        for trade in root.findall(".//Trade"):
            if (
                trade.get("assetCategory") == "CASH"
                and trade.get("symbol")
                and "." in trade.get("symbol")
                and trade.get("transactionType") != "TradeCancel"  # Exclude cancellations
            ):
                forex_transactions.append(trade)

        logger.info(f"Found {len(forex_transactions)} forex transactions in {ib_xml_path.name}")

        if len(forex_transactions) == 0:
            conn.close()
            return 0

        # Get next available IDs
        next_xmlid = get_max_xmlid(conn) + 1
        next_order = get_max_order(conn) + 1

        # Process each transaction
        processed_count = 0
        skipped_count = 0

        for transaction in forex_transactions:
            try:
                if process_single_forex_transaction(conn, transaction, config, next_xmlid, next_order):
                    processed_count += 1
                    next_xmlid += 2
                    next_order += 2
                else:
                    skipped_count += 1
            except Exception as e:
                logger.error(f"Error processing transaction {transaction.get('tradeID')}: {e}")
                skipped_count += 1

        # Commit changes
        conn.commit()

        logger.info(f"Successfully processed {processed_count} forex transactions from {ib_xml_path.name}")
        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} transactions due to errors or duplicates")

        return processed_count

    except Exception as e:
        conn.rollback()
        logger.error(f"Error processing {ib_xml_path.name}: {e}")
        raise
    finally:
        conn.close()

# --- Main Processing Functions ---
def process_all_files(xml_files, pp_xml_path, debug=False):
    """Process all XML files and return statistics"""
    logger = logging.getLogger('forex_bulk_processor_fixed')
    
    total_files = len(xml_files)
    success_count = 0
    error_count = 0
    total_transactions = 0
    start_time = time.time()
    
    logger.info(f"Starting bulk processing of {total_files} files")

    # Step 1: Import PP XML to database once
    logger.info("Step 1: Importing PP XML to database...")
    db_path = import_pp_xml_to_db_once(pp_xml_path, debug)
    
    # Step 2: Process each IB XML file and add transactions to the same database
    logger.info("Step 2: Processing IB XML files and accumulating transactions...")
    
    for i, xml_file in enumerate(xml_files, 1):
        logger.info(f"Progress: {i}/{total_files} - {xml_file.name}")
        
        try:
            transactions_count = process_ib_xml_file(xml_file, db_path, DEFAULT_CONFIG_PATH)
            success_count += 1
            total_transactions += transactions_count
            mark_file_processed(xml_file, True, transactions_count=transactions_count)
            logger.info(f"Successfully processed {xml_file.name}: {transactions_count} transactions added")
        except Exception as e:
            error_count += 1
            error_message = str(e)
            mark_file_processed(xml_file, False, error_message)
            logger.error(f"Failed to process {xml_file.name}: {error_message}")

    # Step 3: Export final accumulated database to PP XML
    logger.info("Step 3: Exporting final accumulated database to PP XML...")
    try:
        export_db_to_pp_xml_final(db_path, pp_xml_path, debug)
        logger.info(f"Successfully exported final PP XML with all accumulated transactions")
    except Exception as e:
        logger.error(f"Failed to export final PP XML: {e}")
        error_count += 1

    elapsed_time = time.time() - start_time
    
    # Final report
    logger.info("=" * 60)
    logger.info("BULK PROCESSING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total files processed: {total_files}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Errors: {error_count}")
    logger.info(f"Total forex transactions added: {total_transactions}")
    logger.info(f"Processing time: {elapsed_time:.1f} seconds")
    
    if error_count > 0:
        logger.info(f"Error details logged in: {LOG_FILE_PATH}")
    
    return success_count, error_count

# --- Argument Parsing ---
def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Fixed bulk processor for forex transactions from multiple IB Flex XML files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--pp-xml",
        type=Path,
        default=DEFAULT_PP_XML,
        help=f"Path to Portfolio Performance XML file (default: {DEFAULT_PP_XML})"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    return parser.parse_args()

# --- Main Function ---
def main():
    """Main execution function"""
    args = parse_arguments()
    
    # Setup logging
    logger = setup_logging(args.debug)
    
    try:
        logger.info("=" * 60)
        logger.info("FIXED FOREX BULK PROCESSOR STARTING - WITH EXCHANGE RATES")
        logger.info("=" * 60)
        logger.info(f"PP XML file: {args.pp_xml}")
        logger.info(f"Transaction data directory: {TRANSACTION_DATA_DIR}")
        logger.info(f"Debug mode: {'Enabled' if args.debug else 'Disabled'}")
        
        # Validate PP XML file exists
        if not args.pp_xml.exists():
            logger.error(f"PP XML file not found: {args.pp_xml}")
            sys.exit(1)
        
        # Validate wrapper.py exists
        if not WRAPPER_PATH.exists():
            logger.error(f"wrapper.py not found: {WRAPPER_PATH}")
            sys.exit(1)

        # Validate config file exists
        if not DEFAULT_CONFIG_PATH.exists():
            logger.error(f"forex_config.json not found: {DEFAULT_CONFIG_PATH}")
            sys.exit(1)
        
        # Initialize tracking database
        init_tracking_database()
        logger.info("Tracking database initialized")
        
        # Create backup
        backup_path = create_backup(args.pp_xml)
        if not backup_path:
            logger.error("Failed to create backup. Aborting for safety.")
            sys.exit(1)
        
        # Discover XML files
        all_xml_files = discover_ib_xml_files()
        if not all_xml_files:
            logger.info("No IB XML files found. Nothing to process.")
            return
        
        # Filter unprocessed files
        new_xml_files = filter_unprocessed_files(all_xml_files)
        if not new_xml_files:
            logger.info("All files have already been processed. Nothing to do.")
            return
        
        # Process files with the fixed approach
        success_count, error_count = process_all_files(new_xml_files, args.pp_xml, args.debug)
        
        # Exit with appropriate code
        if error_count > 0:
            logger.warning(f"Completed with {error_count} errors")
            sys.exit(1)
        else:
            logger.info("All files processed successfully")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        if args.debug:
            import traceback
            logger.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
