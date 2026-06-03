import argparse
import json
import logging
import shutil
import sqlite3
import subprocess
import sys  # For python version check if needed, or for exit
import xml.etree.ElementTree as ET
from pathlib import Path
import decimal
from decimal import Decimal, ROUND_HALF_UP  # For currency calculations
from datetime import datetime, timedelta  # For datetime operations

# Global constants
SCRIPT_DIR = Path(__file__).resolve().parent
IB_FLEX_XML_BASE_DIR = Path("D:/Projetos/Finance_data/Portfolio performance/transaction data")
TEMP_DB_DIR_NAME = "temp_db"
# Config file names (assuming they are in SCRIPT_DIR)
ACCOUNT_MAPPINGS_FILE = SCRIPT_DIR / "account_mappings.json"
FOREX_CONFIG_FILE = SCRIPT_DIR / "forex_config.json"

# Set up logger
logger = logging.getLogger(__name__)


def setup_logging(debug=False):
    """Set up logging configuration with file output."""
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Ensure logs directory exists
    logs_dir = SCRIPT_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create timestamped log file
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"forex_db_corrector_{timestamp}.log"
    
    # Configure logging to both file and console
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - output to: {log_file}")
    return logger


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Correct forex transactions in Portfolio Performance XML files'
    )
    
    parser.add_argument(
        '--pp-xml',
        required=True,
        type=str,
        help='Path to the source Portfolio Performance XML file'
    )
    
    parser.add_argument(
        '--output-pp-xml',
        required=True,
        type=str,
        help='Path for the corrected output Portfolio Performance XML file'
    )
    
    parser.add_argument(
        '--export-db-path',
        type=str,
        help='Path to export the corrected temporary database'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    return parser.parse_args()


def load_config(config_path):
    """Load and validate the configuration file"""
    try:
        with open(config_path, "r") as f:
            data = json.load(f)

        # Validate based on file type
        if config_path.name == ACCOUNT_MAPPINGS_FILE.name:
            # This file provides direct IB Account ID to PP Account UUID mappings under "accounts" key.
            # The script's get_currency_account will look for a *different* "account_mappings" key
            # for IB.CUR -> PPName mappings, which won't be found in this file, leading to fallback.
            # So, for this file, we just ensure it's a dict.
            # The critical "account_mappings" key (for IB.CUR->PPName) is not expected to be mandatory here.
            
            # Check if 'data' itself is a dictionary (basic JSON validity)
            if not isinstance(data, dict):
                logger.error(f"Validation error in {config_path.name}: Root of JSON must be a dictionary. Found: {type(data)}")
                return None

            # Optional: If you want to validate the "accounts" key specifically from user's file:
            # user_specific_accounts_section = data.get("accounts", {})
            # if not isinstance(user_specific_accounts_section, dict):
            #    logger.error(f"Validation error in {config_path.name}: 'accounts' section, if present, must be a dictionary.")
            #    return None
            # No error if "account_mappings" (for IB.CUR->PPName) is missing.

        elif config_path.name == FOREX_CONFIG_FILE.name:
            # User's forex_config.json has "account_mappings" (for patterns) and "fallback_strategy".
            # It does NOT have "currency_mappings" or "fallback_account_strategy" (note singular vs plural).
            
            required_keys = ["account_mappings", "fallback_strategy"]
            for req_key in required_keys:
                if req_key not in data:
                    logger.error(f"Configuration error in {config_path.name}: Must contain '{req_key}' section.")
                    return None
            
            if not isinstance(data["account_mappings"], dict): # This is the pattern section
                logger.error(f"Validation error in {config_path.name}: 'account_mappings' (pattern section) must be a dictionary.")
                return None
            # Further validation for patterns inside data["account_mappings"] if needed (e.g., each entry has "pattern")
            for acc_id, pattern_info in data["account_mappings"].items():
                if not isinstance(pattern_info, dict) or "pattern" not in pattern_info:
                    logger.error(f"Validation error in {config_path.name}: Each entry under 'account_mappings' must be a dictionary with a 'pattern' key. Problem with: '{acc_id}'")
                    return None
                if not isinstance(pattern_info["pattern"], str):
                     logger.error(f"Validation error in {config_path.name}: Pattern for '{acc_id}' must be a string.")
                     return None

            if not isinstance(data["fallback_strategy"], str):
                logger.error(f"Validation error in {config_path.name}: 'fallback_strategy' must be a string.")
                return None
            
            # "currency_mappings" is optional; if present, it should be a dict.
            if "currency_mappings" in data and not isinstance(data["currency_mappings"], dict):
                logger.error(f"Validation error in {config_path.name}: 'currency_mappings', if present, must be a dictionary.")
                return None

        return data
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON configuration: {e}")
        return None
    except ValueError as e:
        logger.error(f"Configuration validation error: {e}")
        return None


def generate_temp_db(source_pp_xml_path_str: str, temp_db_parent_dir_path: Path) -> Path | None:
    """
    Generate a temporary database from the source PP XML file.
    
    Args:
        source_pp_xml_path_str: String path to the source PP XML file
        temp_db_parent_dir_path: Path object for directory where temp DB should be stored
        
    Returns:
        Path to the temporary database file if successful, None otherwise
    """
    try:
        # 1. Path Handling
        source_pp_xml_path = Path(source_pp_xml_path_str)
        temp_db_path = temp_db_parent_dir_path / (source_pp_xml_path.stem + "_to_correct.db")
        
        # Delete existing temp DB if it exists
        if temp_db_path.exists():
            logger.info(f"Deleting existing temp DB: {temp_db_path}")
            temp_db_path.unlink(missing_ok=True)
        
        # Ensure temp DB parent directory exists
        temp_db_parent_dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured temp DB parent directory exists: {temp_db_parent_dir_path}")
        
        # 2. Call wrapper.py
        # Expected output path from wrapper.py
        wrapper_output_db_path = SCRIPT_DIR / "pp_databases" / (source_pp_xml_path.stem + ".db")
        
        # Construct and execute command
        cmd = ["python", str(SCRIPT_DIR / "wrapper.py"), "--exec", "import", source_pp_xml_path_str]
        logger.info(f"Calling wrapper.py with command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        # Check result
        if result.returncode != 0:
            logger.error(f"wrapper.py failed with return code {result.returncode}")
            logger.error(f"stderr: {result.stderr}")
            return None
        
        # Log stdout for debugging
        if result.stdout:
            logger.info(f"wrapper.py stdout: {result.stdout}")
        
        # 3. Move/Copy Database
        # Check if wrapper output exists
        if not wrapper_output_db_path.exists():
            logger.error(f"Expected database not found after wrapper.py execution: {wrapper_output_db_path}")
            return None
        
        # Move the generated DB to temp location
        logger.info(f"Moving generated DB from {wrapper_output_db_path} to {temp_db_path}")
        shutil.move(str(wrapper_output_db_path), str(temp_db_path))
        
        logger.info(f"Successfully generated temporary database: {temp_db_path}")
        return temp_db_path
        
    except Exception as e:
        logger.error(f"Error generating temporary database: {e}")
        return None


def correct_forex_transactions_in_db(db_path_str: str, ib_flex_base_dir: Path, config: dict) -> bool:
    """
    Main function to correct forex transaction directionality in the database.
    
    Args:
        db_path_str: Path to the SQLite database
        ib_flex_base_dir: Path object for the IB Flex XML base directory
        config: Configuration dictionary
        
    Returns:
        bool: True if processing completes successfully, False if major error occurs
    """
    logger.info(f"Starting forex transaction correction process for database: {db_path_str}")
    
    # Database connection with proper error handling
    try:
        conn = sqlite3.connect(db_path_str)
        conn.row_factory = sqlite3.Row
        logger.info("Successfully connected to database")
    except sqlite3.Error as e:
        logger.error(f"Failed to connect to database {db_path_str}: {e}")
        return False
    
    try:
        # Discover IB Flex XML files
        xml_files = discover_ib_xml_files(ib_flex_base_dir)
        if not xml_files:
            logger.warning("No IB XML files found in base directory")
            return True  # Nothing to process, but not an error
        
        logger.info(f"Found {len(xml_files)} XML files to process")
        
        # Initialize correction counter
        total_corrections_made = 0
        
        # Iterate and process XML files
        for xml_file_path in xml_files:
            logger.info(f"Processing XML file: {xml_file_path}")
            
            try:
                # Parse the XML file
                tree = ET.parse(xml_file_path)
                root = tree.getroot()
                logger.debug(f"Successfully parsed XML file: {xml_file_path}")
                
                # Iterate through Trade elements within the XML
                trades_processed = 0
                for trade_element in root.findall(".//Trade"):
                    # Check if this is a forex trade
                    asset_category = trade_element.get("assetCategory")
                    symbol = trade_element.get("symbol", "")
                    
                    if asset_category == "CASH" and "." in symbol:
                        logger.debug(f"Processing forex trade: {symbol}")
                        
                        # Find matching transaction pair
                        db_out_leg, db_in_leg = find_matching_transaction_pair(conn, trade_element, config)
                        
                        if db_out_leg and db_in_leg:
                            # Attempt to correct transaction directionality
                            corrected = correct_transaction_directionality(conn, trade_element, db_out_leg, db_in_leg, config)
                            if corrected:
                                total_corrections_made += 1
                                logger.debug(f"Correction applied for trade {trade_element.get('tradeID', 'unknown')}")
                        else:
                            logger.debug(f"No matching transaction pair found for trade {trade_element.get('tradeID', 'unknown')}")
                        
                        trades_processed += 1
                    else:
                        # Skip non-forex trades
                        logger.debug(f"Skipping non-forex trade: asset_category={asset_category}, symbol={symbol}")
                
                logger.info(f"Completed processing {xml_file_path}: {trades_processed} forex trades processed")
                
            except ET.ParseError as e:
                logger.error(f"XML parsing error for file {xml_file_path}: {e}")
                continue  # Continue to next file
            except Exception as e:
                logger.error(f"Unexpected error processing file {xml_file_path}: {e}")
                continue  # Continue to next file
        
        # Commit changes if any corrections were made
        if total_corrections_made > 0:
            conn.commit()
            logger.info(f"Committed {total_corrections_made} corrections to database")
        else:
            logger.info("No corrections were needed")
        
        logger.info(f"Successfully completed forex transaction correction process. Total corrections made: {total_corrections_made}")
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error during forex transaction correction: {e}")
        return False
        
    finally:
        # Ensure database connection is closed
        try:
            conn.close()
            logger.debug("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")


def find_matching_transaction_pair(conn: sqlite3.Connection, xml_trade_element: ET.Element, config: dict) -> tuple[sqlite3.Row | None, sqlite3.Row | None]:
    """
    Find matching TRANSFER_OUT and TRANSFER_IN transaction pair from Portfolio Performance database
    that corresponds to the given XML trade element.
    
    Args:
        conn: SQLite database connection
        xml_trade_element: XML Trade element from Interactive Brokers
        config: Configuration dictionary containing forex_config and account_mappings
        
    Returns:
        Tuple of (db_out_leg_row, db_in_leg_row) or (None, None) if not found
    """
    # 1. LOG RAW ATTRIBUTES OF THE TRADE ELEMENT BEING PROCESSED
    trade_id = xml_trade_element.get('tradeID')
    account_id = xml_trade_element.get('accountId')
    symbol = xml_trade_element.get('symbol')
    trade_date = xml_trade_element.get('tradeDate')
    quantity = xml_trade_element.get('quantity')
    trade_price = xml_trade_element.get('tradePrice')
    proceeds = xml_trade_element.get('proceeds')
    ib_commission = xml_trade_element.get('ibCommission')
    currency = xml_trade_element.get('currency')
    buy_sell = xml_trade_element.get('buySell')
    
    logger.debug(f"=== Processing trade element ===")
    logger.debug(f"Trade ID: {trade_id}")
    logger.debug(f"Account ID: {account_id}")
    logger.debug(f"Symbol: {symbol}")
    logger.debug(f"Trade Date: {trade_date}")
    logger.debug(f"Quantity: {quantity}")
    logger.debug(f"Trade Price: {trade_price}")
    logger.debug(f"Proceeds: {proceeds}")
    logger.debug(f"IB Commission: {ib_commission}")
    logger.debug(f"Currency: {currency}")
    logger.debug(f"Buy/Sell: {buy_sell}")
    
    # Check for required attributes
    if not all([trade_date, symbol, quantity, proceeds]):
        logger.debug(f"Missing required attributes in XML trade element for trade ID {trade_id}")
        return (None, None)
    
    # Extract from_currency and to_currency (derive from symbol and buy_sell)
    try:
        base_curr_xml, counter_curr_xml = symbol.split('.')
        logger.debug(f"Extracted base currency: {base_curr_xml}, counter currency: {counter_curr_xml}")
        
        # Determine from/to currencies based on buy/sell
        if buy_sell == 'SELL':
            from_currency = base_curr_xml  # Selling base currency
            to_currency = counter_curr_xml  # Receiving counter currency
        elif buy_sell == 'BUY':
            from_currency = counter_curr_xml  # Selling counter currency
            to_currency = base_curr_xml  # Receiving base currency
        else:
            logger.debug(f"Unknown buy/sell value: {buy_sell}")
            from_currency = base_curr_xml
            to_currency = counter_curr_xml
            
        logger.debug(f"Derived from_currency: {from_currency}, to_currency: {to_currency}")
        
    except ValueError:
        logger.debug(f"Invalid symbol format: {symbol}")
        return (None, None)
    
    # Convert trade date to ISO format and UTC datetime
    try:
        # Assuming trade_date is in YYYYMMDD format
        trade_date_iso = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}T00:00:00Z"
        trade_datetime_utc = datetime.fromisoformat(trade_date_iso.replace('Z', '+00:00'))
        logger.debug(f"Trade date ISO: {trade_date_iso}")
        logger.debug(f"Trade datetime UTC: {trade_datetime_utc}")
    except Exception as e:
        logger.debug(f"Error parsing trade date {trade_date}: {e}")
        return (None, None)
    
    # Calculate absolute amounts
    try:
        abs_quantity = abs(float(quantity))
        abs_proceeds = abs(float(proceeds))
        logger.debug(f"Absolute quantity: {abs_quantity}")
        logger.debug(f"Absolute proceeds: {abs_proceeds}")
    except (ValueError, TypeError) as e:
        logger.debug(f"Error converting amounts: {e}")
        return (None, None)
    
    # 2. GET CURRENCY ACCOUNT UUIDs WITH LOGGING
    logger.debug(f"=== Getting currency accounts ===")
    
    # Get account mappings and fallback strategy
    account_mappings = config.get('forex_config', {}).get('account_mappings', {})
    fallback_strategy = config.get('forex_config', {}).get('fallback_strategy', 'skip')
    
    # Get from_currency account
    logger.debug(f"Getting currency account for IB account: {account_id}, currency: {from_currency}")
    
    if account_id in account_mappings:
        pattern = account_mappings[account_id]['pattern']
        from_account_name = pattern.replace('{currency}', from_currency)
        logger.debug(f"Generated from_account_name from pattern: {from_account_name}")
        
        # Query database directly for account UUID
        cursor = conn.cursor()
        cursor.execute("SELECT uuid FROM account WHERE name = ? AND currency = ?",
                       (from_account_name, from_currency))
        result = cursor.fetchone()
        from_currency_account_uuid = result[0] if result else None
        
        if result:
            logger.debug(f"Found from_currency account UUID: {from_currency_account_uuid}")
        else:
            logger.debug(f"No account found in database for name='{from_account_name}' and currency='{from_currency}'")
    else:
        logger.debug(f"No pattern found for IB account: {account_id}")
        if fallback_strategy == "error":
            logger.error(f"No mapping found for IB account {account_id} with currency {from_currency}")
        else:
            logger.warning(f"No mapping found for IB account {account_id} with currency {from_currency}, skipping")
        from_currency_account_uuid = None
    
    logger.debug(f"From currency account UUID: {from_currency_account_uuid}")
    
    # Get to_currency account
    logger.debug(f"Getting currency account for IB account: {account_id}, currency: {to_currency}")
    
    if account_id in account_mappings:
        pattern = account_mappings[account_id]['pattern']
        to_account_name = pattern.replace('{currency}', to_currency)
        logger.debug(f"Generated to_account_name from pattern: {to_account_name}")
        
        # Query database directly for account UUID
        cursor = conn.cursor()
        cursor.execute("SELECT uuid FROM account WHERE name = ? AND currency = ?",
                       (to_account_name, to_currency))
        result = cursor.fetchone()
        to_currency_account_uuid = result[0] if result else None
        
        if result:
            logger.debug(f"Found to_currency account UUID: {to_currency_account_uuid}")
        else:
            logger.debug(f"No account found in database for name='{to_account_name}' and currency='{to_currency}'")
    else:
        logger.debug(f"No pattern found for IB account: {account_id}")
        if fallback_strategy == "error":
            logger.error(f"No mapping found for IB account {account_id} with currency {to_currency}")
        else:
            logger.warning(f"No mapping found for IB account {account_id} with currency {to_currency}, skipping")
        to_currency_account_uuid = None
    
    logger.debug(f"To currency account UUID: {to_currency_account_uuid}")
    
    # Check if either account UUID is None
    if from_currency_account_uuid is None:
        logger.debug(f"From currency account UUID is None for account {account_id} and currency {from_currency}")
        return (None, None)
        
    if to_currency_account_uuid is None:
        logger.debug(f"To currency account UUID is None for account {account_id} and currency {to_currency}")
        return (None, None)
    
    # Map currencies to PP format
    from_currency_pp = map_ib_currency_to_pp(from_currency, config['forex_config'])
    to_currency_pp = map_ib_currency_to_pp(to_currency, config['forex_config'])
    logger.debug(f"Mapped from_currency to PP: {from_currency} -> {from_currency_pp}")
    logger.debug(f"Mapped to_currency to PP: {to_currency} -> {to_currency_pp}")
    
    # Calculate target amounts in cents
    if buy_sell == 'SELL':
        target_amount_from_currency = decimal_to_cents(abs_quantity)  # Base currency amount
        target_amount_to_currency = decimal_to_cents(abs_proceeds)    # Counter currency amount
    else:  # BUY
        target_amount_from_currency = decimal_to_cents(abs_proceeds)  # Counter currency amount
        target_amount_to_currency = decimal_to_cents(abs_quantity)    # Base currency amount
    
    logger.debug(f"Target amount from currency ({from_currency_pp}): {target_amount_from_currency} cents")
    logger.debug(f"Target amount to currency ({to_currency_pp}): {target_amount_to_currency} cents")
    
    # Ensure row factory is set for Row objects
    if conn.row_factory != sqlite3.Row:
        conn.row_factory = sqlite3.Row
    
    # 3. SEARCH FOR OUT LEG WITH DETAILED LOGGING
    logger.debug(f"=== Searching for OUT leg ===")
    
    out_leg_query = """
        SELECT * FROM xact
        WHERE account = ?
        AND currency = ?
        AND amount = ?
        AND type = 'TRANSFER_OUT'
        AND date LIKE ?
        ORDER BY date
    """
    
    formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
    out_leg_params = (from_currency_account_uuid, from_currency_pp, target_amount_from_currency, formatted_date + '%')
    
    logger.debug(f"OUT leg query: {out_leg_query}")
    logger.debug(f"OUT leg params: {out_leg_params}")
    
    try:
        cursor = conn.cursor()
        cursor.execute(out_leg_query, out_leg_params)
        db_potential_out_legs = cursor.fetchall()
        
        logger.debug(f"Found {len(db_potential_out_legs)} potential OUT legs")
        
        if db_potential_out_legs:
            for i, leg in enumerate(db_potential_out_legs):
                logger.debug(f"Potential OUT leg {i+1}: uuid={leg['uuid']}, type={leg['type']}, "
                           f"date={leg['date']}, account={leg['account']}, "
                           f"security={leg['security'] or 'N/A'}, amount={leg['amount']}, "
                           f"note={leg['note'] or 'N/A'}")
        else:
            logger.debug("No potential OUT legs found")
                 # Also search for incorrectly typed OUT transactions (should be OUT but is IN)
        if not db_potential_out_legs:
            logger.debug("No correctly typed OUT legs found, searching for incorrectly typed transactions...")
            wrong_out_query = """
                SELECT * FROM xact
                WHERE account = ?
                AND currency = ?
                AND amount = ?
                AND type = 'TRANSFER_IN'
                AND date LIKE ?
                ORDER BY date
            """
            cursor.execute(wrong_out_query, out_leg_params)
            db_potential_out_legs = cursor.fetchall()
            if db_potential_out_legs:
                logger.debug(f"Found {len(db_potential_out_legs)} incorrectly typed OUT legs (currently TRANSFER_IN)")
                for i, leg in enumerate(db_potential_out_legs):
                    logger.debug(f"Incorrectly typed OUT leg {i+1}: uuid={leg['uuid']}, type={leg['type']}, "
                               f"date={leg['date']}, account={leg['account']}, "
                               f"security={leg['security'] or 'N/A'}, amount={leg['amount']}, "
                               f"note={leg['note'] or 'N/A'}")
   
    except sqlite3.Error as e:
        logger.debug(f"Database error searching for OUT legs: {e}")
        return (None, None)
    
    # 4. SEARCH FOR IN LEG WITH DETAILED LOGGING
    logger.debug(f"=== Searching for IN leg ===")
    
    in_leg_query = """
        SELECT * FROM xact
        WHERE account = ?
        AND currency = ?
        AND amount = ?
        AND type = 'TRANSFER_IN'
        AND date LIKE ?
        ORDER BY date
    """
    
    in_leg_params = (to_currency_account_uuid, to_currency_pp, target_amount_to_currency, formatted_date + '%')
    
    logger.debug(f"IN leg query: {in_leg_query}")
    logger.debug(f"IN leg params: {in_leg_params}")
    
    try:
        cursor.execute(in_leg_query, in_leg_params)
        db_potential_in_legs = cursor.fetchall()
        
        logger.debug(f"Found {len(db_potential_in_legs)} potential IN legs")
        
        if db_potential_in_legs:
            for i, leg in enumerate(db_potential_in_legs):
                logger.debug(f"Potential IN leg {i+1}: uuid={leg['uuid']}, type={leg['type']}, "
                           f"date={leg['date']}, account={leg['account']}, "
                           f"security={leg['security'] or 'N/A'}, amount={leg['amount']}, "
                           f"note={leg['note'] or 'N/A'}")
        else:
            logger.debug("No potential IN legs found")
        if not db_potential_in_legs:
            logger.debug("No correctly typed IN legs found, searching for incorrectly typed transactions...")
            wrong_in_query = """
                SELECT * FROM xact
                WHERE account = ?
                AND currency = ?
                AND amount = ?
                AND type = 'TRANSFER_OUT'
                AND date LIKE ?
                ORDER BY date
            """
            cursor.execute(wrong_in_query, in_leg_params)
            db_potential_in_legs = cursor.fetchall()
            if db_potential_in_legs:
                logger.debug(f"Found {len(db_potential_in_legs)} incorrectly typed IN legs (currently TRANSFER_OUT)")
                for i, leg in enumerate(db_potential_in_legs):
                    logger.debug(f"Incorrectly typed IN leg {i+1}: uuid={leg['uuid']}, type={leg['type']}, "
                            f"date={leg['date']}, account={leg['account']}, "
                            f"security={leg['security'] or 'N/A'}, amount={leg['amount']}, "
                            f"note={leg['note'] or 'N/A'}")    
    except sqlite3.Error as e:
        logger.debug(f"Database error searching for IN legs: {e}")
        return (None, None)
    
    # 5. FILTERING/SELECTION OF BEST LEGS
    logger.debug(f"=== Selecting best legs ===")
    
    # Simple selection: take the first of each if available
    selected_out_leg = None
    selected_in_leg = None
    
    if db_potential_out_legs:
        selected_out_leg = db_potential_out_legs[0]
        logger.debug(f"Selected OUT leg: uuid={selected_out_leg['uuid']} (first match)")
    else:
        logger.debug("No suitable OUT leg found among potentials")
        
    if db_potential_in_legs:
        selected_in_leg = db_potential_in_legs[0]
        logger.debug(f"Selected IN leg: uuid={selected_in_leg['uuid']} (first match)")
    else:
        logger.debug("No suitable IN leg found among potentials")
    
    # 6. FINAL RESULT WITH SPECIFIC FAILURE REASONS
    if selected_out_leg is None and selected_in_leg is None:
        logger.debug(f"Failed to find matching pair for trade ID {trade_id}: "
                    f"Out leg not found for account {from_currency_account_uuid} and currency {from_currency_pp} with amount {target_amount_from_currency}, "
                    f"and In leg not found for account {to_currency_account_uuid} and currency {to_currency_pp} with amount {target_amount_to_currency}")
        return (None, None)
    elif selected_out_leg is None:
        logger.debug(f"Failed to find matching pair for trade ID {trade_id}: "
                    f"Out leg not found for account {from_currency_account_uuid} and currency {from_currency_pp} with amount {target_amount_from_currency}")
        return (None, None)
    elif selected_in_leg is None:
        logger.debug(f"Failed to find matching pair for trade ID {trade_id}: "
                    f"In leg not found for account {to_currency_account_uuid} and currency {to_currency_pp} with amount {target_amount_to_currency}")
        return (None, None)
    else:
        logger.debug(f"Successfully found matching transaction pair for trade ID {trade_id}: "
                    f"OUT leg UUID={selected_out_leg['uuid']}, IN leg UUID={selected_in_leg['uuid']}")
        return (selected_out_leg, selected_in_leg)


def correct_transaction_directionality(conn: sqlite3.Connection, xml_trade_element: ET.Element, db_out_leg_row: sqlite3.Row, db_in_leg_row: sqlite3.Row, config: dict) -> bool:
    """
    Correct transaction directionality by comparing current DB state with expected state from XML.
    
    Args:
        conn: SQLite database connection
        xml_trade_element: XML Trade element from Interactive Brokers
        db_out_leg_row: Current OUT leg row from database
        db_in_leg_row: Current IN leg row from database
        config: Configuration dictionary containing forex_config and account_mappings
        
    Returns:
        True if corrections were made, False otherwise
    """
    # Extract data from XML trade element
    buy_sell_xml = xml_trade_element.get("buySell")
    symbol_str = xml_trade_element.get("symbol")
    quantity_str = xml_trade_element.get("quantity")
    proceeds_str = xml_trade_element.get("proceeds")
    trade_id = xml_trade_element.get("tradeID")
    
    if not all([buy_sell_xml, symbol_str, quantity_str, proceeds_str]):
        logger.error(f"Missing required attributes in XML trade element for trade ID {trade_id}")
        return False
    
    # Extract base and counter currencies from symbol
    try:
        base_curr_xml, counter_curr_xml = symbol_str.split('.')
    except ValueError:
        logger.error(f"Invalid symbol format for trade ID {trade_id}: {symbol_str}")
        return False
    
    # Determine expected DB state based on XML
    if buy_sell_xml == 'SELL':
        expected_out_curr_xml = base_curr_xml
        expected_out_amount_xml = abs(Decimal(quantity_str))
        expected_in_curr_xml = counter_curr_xml
        expected_in_amount_xml = abs(Decimal(proceeds_str))
    elif buy_sell_xml == 'BUY':
        expected_out_curr_xml = counter_curr_xml
        expected_out_amount_xml = abs(Decimal(proceeds_str))
        expected_in_curr_xml = base_curr_xml
        expected_in_amount_xml = abs(Decimal(quantity_str))
    else:
        logger.error(f"Unknown buySell value for trade ID {trade_id}: {buy_sell_xml}")
        return False
    
    # Map expected XML currencies to PP currencies
    try:
        expected_out_curr_pp = map_ib_currency_to_pp(expected_out_curr_xml, config['forex_config'])
        expected_in_curr_pp = map_ib_currency_to_pp(expected_in_curr_xml, config['forex_config'])
    except Exception as e:
        logger.error(f"Currency mapping failed for trade ID {trade_id}: {e}")
        return False
    
    # Check if currency mapping actually worked
    if expected_out_curr_pp == expected_out_curr_xml and expected_out_curr_xml not in config['forex_config'].get('currency_mappings', {}):
        logger.error(f"Currency mapping failed for OUT currency {expected_out_curr_xml} in trade ID {trade_id}")
        return False
    
    if expected_in_curr_pp == expected_in_curr_xml and expected_in_curr_xml not in config['forex_config'].get('currency_mappings', {}):
        logger.error(f"Currency mapping failed for IN currency {expected_in_curr_xml} in trade ID {trade_id}")
        return False
    
    # Convert expected XML amounts to cents
    try:
        expected_out_amount_cents = decimal_to_cents(expected_out_amount_xml)
        expected_in_amount_cents = decimal_to_cents(expected_in_amount_xml)
    except Exception as e:
        logger.error(f"Error converting amounts to cents for trade ID {trade_id}: {e}")
        return False
    
    # Compare current DB state with expected state and identify need for correction
    needs_correction = False
    
    # Check the db_out_leg_row
    if (db_out_leg_row['type'] != 'TRANSFER_OUT' or
        db_out_leg_row['currency'] != expected_out_curr_pp or
        db_out_leg_row['amount'] != expected_out_amount_cents):
        needs_correction = True
        logger.info(f"OUT leg mismatch for trade ID {trade_id}:")
        logger.info(f"  Current: type={db_out_leg_row['type']}, currency={db_out_leg_row['currency']}, amount={db_out_leg_row['amount']}")
        logger.info(f"  Expected: type=TRANSFER_OUT, currency={expected_out_curr_pp}, amount={expected_out_amount_cents}")
    
    # Check the db_in_leg_row
    if (db_in_leg_row['type'] != 'TRANSFER_IN' or
        db_in_leg_row['currency'] != expected_in_curr_pp or
        db_in_leg_row['amount'] != expected_in_amount_cents):
        needs_correction = True
        logger.info(f"IN leg mismatch for trade ID {trade_id}:")
        logger.info(f"  Current: type={db_in_leg_row['type']}, currency={db_in_leg_row['currency']}, amount={db_in_leg_row['amount']}")
        logger.info(f"  Expected: type=TRANSFER_IN, currency={expected_in_curr_pp}, amount={expected_in_amount_cents}")
    
    # Perform SQL UPDATEs if needs_correction is True
    if needs_correction:
        logger.info(f"Applying corrections for trade ID {trade_id}")
        cursor = conn.cursor()
        
        try:
            # Update the identified OUT leg in DB
            cursor.execute(
                "UPDATE xact SET type = 'TRANSFER_OUT', amount = ?, currency = ? WHERE uuid = ?",
                (expected_out_amount_cents, expected_out_curr_pp, db_out_leg_row['uuid'])
            )
            logger.info(f"Updated OUT leg UUID {db_out_leg_row['uuid']}: type=TRANSFER_OUT, amount={expected_out_amount_cents}, currency={expected_out_curr_pp}")
            
            # Update the identified IN leg in DB
            cursor.execute(
                "UPDATE xact SET type = 'TRANSFER_IN', amount = ?, currency = ? WHERE uuid = ?",
                (expected_in_amount_cents, expected_in_curr_pp, db_in_leg_row['uuid'])
            )
            logger.info(f"Updated IN leg UUID {db_in_leg_row['uuid']}: type=TRANSFER_IN, amount={expected_in_amount_cents}, currency={expected_in_curr_pp}")
            
            # Commit the changes
            conn.commit()
            logger.info(f"Successfully applied corrections for trade ID {trade_id}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Database error while updating trade ID {trade_id}: {e}")
            conn.rollback()
            return False
    else:
        logger.info(f"No correction needed for trade ID {trade_id} - DB state matches XML")
        return False


def export_corrected_db(temp_db_path: Path, export_path_str: str) -> bool:
    """Export the corrected database to the specified path.
    
    Args:
        temp_db_path: Path to the temporary corrected database
        export_path_str: String path where to export the database
        
    Returns:
        bool: True if export successful, False otherwise
    """
    try:
        # Convert export_path_str to a Path object
        export_path = Path(export_path_str)
        
        # Ensure the parent directory of export_path exists
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Log that the database is being exported
        logging.info(f"Exporting corrected database from {temp_db_path} to {export_path}")
        
        # Copy the temporary database to the export path using copy2 to preserve metadata
        shutil.copy2(str(temp_db_path), str(export_path))
        
        # Log success and return True
        logging.info(f"Successfully exported corrected database to {export_path}")
        return True
        
    except (IOError, OSError) as e:
        # Log error message with exception details and return False
        logging.error(f"Failed to export database from {temp_db_path} to {export_path_str}: {e}")
        return False


def generate_corrected_pp_xml(temp_db_path: Path, output_xml_path_str: str) -> bool:
    """
    Generate corrected PP XML from the temporary database.
    
    Args:
        temp_db_path: Path to the temporary (corrected) database
        output_xml_path_str: String path for the output PP XML file
        
    Returns:
        bool: True if XML generation is successful, False otherwise
    """
    try:
        # Convert output path string to Path object
        output_xml_path = Path(output_xml_path_str)
        
        # Ensure the parent directory exists
        try:
            output_xml_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured output directory exists: {output_xml_path.parent}")
        except OSError as e:
            logger.error(f"Failed to create output directory {output_xml_path.parent}: {e}")
            return False
        
        # Construct the command to call db2ppxml.py
        db2ppxml_script = SCRIPT_DIR / "db2ppxml.py"
        cmd = ["python", str(db2ppxml_script), str(temp_db_path), str(output_xml_path)]
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        # Execute the command
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        # Check the return code
        if result.returncode != 0:
            logger.error(f"db2ppxml.py failed with return code {result.returncode}")
            if result.stderr:
                logger.error(f"Error output: {result.stderr}")
            return False
        
        # Log stdout for debugging/info
        if result.stdout:
            logger.info(f"db2ppxml.py output: {result.stdout}")
        
        # Verify that the output file was created and is not empty
        if not output_xml_path.exists():
            logger.error(f"Output file was not created: {output_xml_path}")
            return False
        
        if output_xml_path.stat().st_size == 0:
            logger.error(f"Output file is empty: {output_xml_path}")
            return False
        
        logger.info(f"Successfully generated corrected PP XML: {output_xml_path}")
        logger.info(f"Output file size: {output_xml_path.stat().st_size} bytes")
        return True
        
    except subprocess.SubprocessError as e:
        logger.error(f"Subprocess error while calling db2ppxml.py: {e}")
        return False
    except IOError as e:
        logger.error(f"I/O error during XML generation: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during XML generation: {e}")
        return False


def map_ib_currency_to_pp(ib_currency, forex_config):
    """Map Interactive Brokers currency to Portfolio Performance format."""
    if 'currency_mappings' not in forex_config:
        logger.warning(f"No currency_mappings found in config, returning original currency: {ib_currency}")
        return ib_currency
    
    currency_mappings = forex_config['currency_mappings']
    mapped_currency = currency_mappings.get(ib_currency, ib_currency)
    
    if mapped_currency != ib_currency:
        logger.debug(f"Mapped currency {ib_currency} -> {mapped_currency}")
    
    return mapped_currency


def discover_ib_xml_files(base_dir):
    """Discover Interactive Brokers XML files in base directory."""
    base_path = Path(base_dir)
    
    if not base_path.exists():
        logger.error(f"Base directory not found: {base_path}")
        return []
    
    xml_files = []
    
    # Find all directories starting with "IB"
    ib_dirs = [d for d in base_path.iterdir()
               if d.is_dir() and d.name.startswith("IB")]
    
    logger.info(f"Found {len(ib_dirs)} IB directories: {[d.name for d in ib_dirs]}")
    
    # Find all XML files in these directories
    for ib_dir in ib_dirs:
        xml_pattern = ib_dir / "*.xml"
        dir_xml_files = list(ib_dir.glob("*.xml"))
        xml_files.extend(dir_xml_files)
        logger.debug(f"Found {len(dir_xml_files)} XML files in {ib_dir.name}")
    
    # Sort alphabetically
    xml_files.sort(key=lambda x: str(x))
    
    logger.info(f"Total IB XML files discovered: {len(xml_files)}")
    return xml_files


def get_currency_account(conn, ib_account_id, currency_code, account_mappings, fallback_strategy):
    """Find the appropriate account UUID for a given IB account ID and currency"""
    
    # Check if we have a mapping for this specific IB account and currency
    account_key = (ib_account_id, currency_code)
    if account_key in account_mappings:
        pp_account_name = account_mappings[account_key]
        logger.debug(f"Found direct mapping for {account_key}: {pp_account_name}")
    else:
        # Try wildcard mapping with "*" for account ID
        wildcard_key = ("*", currency_code)
        if wildcard_key in account_mappings:
            pp_account_name = account_mappings[wildcard_key]
            logger.debug(f"Found wildcard mapping for {wildcard_key}: {pp_account_name}")
        else:
            # No mapping found, use fallback strategy
            if fallback_strategy == "error":
                logger.error(f"No mapping found for IB account {ib_account_id} with currency {currency_code}")
                return None
            elif fallback_strategy == "skip":
                logger.warning(f"No mapping found for IB account {ib_account_id} with currency {currency_code}, skipping")
                return None
            else:
                logger.warning(f"Unknown fallback strategy: {fallback_strategy}, treating as 'skip'")
                return None
    
    # Map IB currency to PP currency for database lookup
    pp_currency = map_ib_currency_to_pp(currency_code, {'currency_mappings': {}})  # Use empty mappings to avoid recursion
    
    # Query database for account UUID
    cursor = conn.cursor()
    cursor.execute(
        "SELECT uuid FROM account WHERE name = ? AND currency = ?",
        (pp_account_name, pp_currency)
    )
    result = cursor.fetchone()
    
    if result:
        logger.debug(f"Found account UUID: {result[0]} for {pp_account_name} ({pp_currency})")
        return result[0]
    else:
        logger.warning(f"No account found in database for name='{pp_account_name}' and currency='{pp_currency}'")
        return None


def decimal_to_cents(decimal_value):
    """Convert decimal value to cents."""
    if not isinstance(decimal_value, Decimal):
        decimal_value = Decimal(str(decimal_value))
    
    # Multiply by 100 and round to nearest integer using ROUND_HALF_UP
    cents_value = decimal_value * 100
    rounded_cents = cents_value.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    
    return int(rounded_cents)


def main():
    """Main function to execute the forex database correction process."""
    # Parse arguments
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting forex database correction process")
    
    # Load configurations
    logger.info("Loading configuration files...")
    account_mappings = load_config(ACCOUNT_MAPPINGS_FILE)
    if account_mappings is None:
        logger.error(f"Failed to load account mappings from {ACCOUNT_MAPPINGS_FILE}")
        return 1
        
    forex_config = load_config(FOREX_CONFIG_FILE)
    if forex_config is None:
        logger.error(f"Failed to load forex config from {FOREX_CONFIG_FILE}")
        return 1
        
    config_data = {
        "account_mappings": account_mappings,
        "forex_config": forex_config
    }
    logger.info("Configuration files loaded successfully")
    
    # Set up temp database directory
    temp_db_dir = SCRIPT_DIR / TEMP_DB_DIR_NAME
    
    # Step 1: Generate temp database
    logger.info("Step 1: Generating temporary database...")
    temp_db_path = generate_temp_db(args.pp_xml, temp_db_dir)
    if temp_db_path is None:
        logger.error("Failed to generate temporary database")
        return 1
    logger.info(f"Temporary database generated successfully: {temp_db_path}")
    
    # Steps 2 & 3: Correct forex transactions in database
    logger.info("Steps 2 & 3: Correcting forex transactions in database...")
    correction_success = correct_forex_transactions_in_db(str(temp_db_path), IB_FLEX_XML_BASE_DIR, config_data)
    if not correction_success:
        logger.error("Failed to correct forex transactions in database")
        return 1
    logger.info("Forex transactions corrected successfully")
    
    # Step 4: Export database (if requested)
    if args.export_db_path:
        logger.info("Step 4: Exporting corrected database...")
        export_success = export_corrected_db(temp_db_path, args.export_db_path)
        if not export_success:
            logger.warning(f"Failed to export corrected database to {args.export_db_path}")
        else:
            logger.info(f"Database exported successfully to {args.export_db_path}")
    
    # Step 5: Generate corrected PP XML
    logger.info("Step 5: Generating corrected PP XML...")
    xml_success = generate_corrected_pp_xml(temp_db_path, args.output_pp_xml)
    if not xml_success:
        logger.error("Failed to generate corrected PP XML")
        return 1
    logger.info(f"Corrected PP XML generated successfully: {args.output_pp_xml}")
    
    logger.info("Forex database correction process completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())