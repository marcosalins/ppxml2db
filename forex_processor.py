#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Forex Transaction Processor for Portfolio Performance

This script processes forex transactions from Interactive Brokers Flex XML reports
and integrates them into Portfolio Performance by:

1. Importing a Portfolio Performance XML file into a database using wrapper.py
2. Adding forex transactions as account transfers between currency accounts
3. Exporting the updated database back to a Portfolio Performance XML file

Usage:
  python forex_processor.py --pp-xml portfolio.xml --ib-flex flex_statement.xml --output-xml updated_portfolio.xml [--config config.json] [--debug]
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# --- Configuration ---
SCRIPT_DIR = Path(__file__).parent.resolve()
WRAPPER_PATH = SCRIPT_DIR / "wrapper.py"
DEFAULT_CONFIG_PATH = SCRIPT_DIR / "forex_config.json"
DB_DIR = SCRIPT_DIR / "pp_databases"

# --- Helper Functions ---


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

        # Validate fallback strategy
        if config["fallback_strategy"] not in ["error", "skip", "map"]:
            raise ValueError(
                f"Invalid fallback_strategy: {config['fallback_strategy']}"
            )

        return config
    except FileNotFoundError:
        print(f"Configuration file not found: {config_path}")
        print("Creating default configuration...")

        # Create default configuration
        default_config = {
            "account_mappings": {
                "Lia": {"pattern": "Lia_{currency}", "description": "Lia's accounts"},
                "Marcos": {
                    "pattern": "Marcos_{currency}",
                    "description": "Marcos's accounts",
                },
                "Mariana": {
                    "pattern": "Mariana_{currency}",
                    "description": "Mariana's accounts",
                },
            },
            "fallback_strategy": "error",
        }

        # Save default configuration
        os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=2)

        return default_config
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {e}")


def run_subprocess(command_args, debug=False):
    """Executes a subprocess command and handles potential errors."""
    try:
        print(f"Executing: {' '.join(map(str, command_args))}")
        if debug:
            # With output shown directly
            result = subprocess.run(command_args, check=True)
        else:
            # Capture output
            result = subprocess.run(
                command_args, check=True, capture_output=True, text=True
            )
            if result.stdout and debug:
                print("Output:\n", result.stdout)
            if result.stderr and debug:
                print("Error Output:\n", result.stderr)
        return True
    except FileNotFoundError:
        print(f"Error: Script not found at {command_args[1]}", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as e:
        print(
            f"Error executing command: {' '.join(map(str, command_args))}",
            file=sys.stderr,
        )
        print(f"Return code: {e.returncode}", file=sys.stderr)
        if e.stdout:
            print(f"stdout:\n{e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"stderr:\n{e.stderr}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return False


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


def get_currency_account(conn, ib_account_id, currency_code, config):
    """
    Find the appropriate account UUID for a given IB account ID and currency

    Args:
        conn: Database connection
        ib_account_id: Account ID from IB Flex XML (e.g., "Lia")
        currency_code: Currency code (e.g., "USD")
        config: Configuration dictionary

    Returns:
        UUID of the matching PP account
    """
    # Get the pattern for this IB account
    if ib_account_id not in config["account_mappings"]:
        if config["fallback_strategy"] == "error":
            raise ValueError(f"No mapping found for IB account ID: {ib_account_id}")
        elif config["fallback_strategy"] == "skip":
            return None

    pattern = config["account_mappings"][ib_account_id]["pattern"]

    # Replace {currency} with the actual currency code
    account_name = pattern.replace("{currency}", currency_code)

    # Query the database for this account
    cursor = conn.cursor()
    cursor.execute(
        "SELECT uuid FROM account WHERE name = ? AND currency = ?",
        (account_name, currency_code),
    )
    result = cursor.fetchone()

    if result:
        return result[0]

    # If not found, try a more flexible search
    cursor.execute(
        "SELECT uuid FROM account WHERE name LIKE ? AND currency = ?",
        (f"%{ib_account_id}%{currency_code}", currency_code),
    )
    result = cursor.fetchone()

    if result:
        return result[0]

    # If still not found, handle according to fallback strategy
    if config["fallback_strategy"] == "error":
        raise ValueError(
            f"No account found for IB account {ib_account_id} with currency {currency_code}"
        )

    return None


def insert_transfer_out(
    conn,
    uuid_str,
    account_uuid,
    date_str,
    currency,
    amount,
    note,
    source,
    updated_at,
    xmlid,
    order,
    fees=0,
):
    """Inserts a TRANSFER_OUT transaction"""
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT INTO xact (
        uuid, acctype, account, date, currency, amount, security, shares, 
        note, source, updatedAt, type, fees, taxes, _xmlid, _order
    ) VALUES (?, 'account', ?, ?, ?, ?, NULL, 0, ?, ?, ?, 'TRANSFER_OUT', ?, 0, ?, ?)
    """,
        (
            uuid_str,
            account_uuid,
            date_str,
            currency,
            amount,
            note,
            source,
            updated_at,
            fees,
            xmlid,
            order,
        ),
    )
    return cursor.lastrowid


def insert_transfer_in(
    conn,
    uuid_str,
    account_uuid,
    date_str,
    currency,
    amount,
    note,
    source,
    updated_at,
    xmlid,
    order,
    fees=0,
):
    """Inserts a TRANSFER_IN transaction"""
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT INTO xact (
        uuid, acctype, account, date, currency, amount, security, shares, 
        note, source, updatedAt, type, fees, taxes, _xmlid, _order
    ) VALUES (?, 'account', ?, ?, ?, ?, NULL, 0, ?, ?, ?, 'TRANSFER_IN', ?, 0, ?, ?)
    """,
        (
            uuid_str,
            account_uuid,
            date_str,
            currency,
            amount,
            note,
            source,
            updated_at,
            fees,
            xmlid,
            order,
        ),
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


def import_pp_xml_to_db(pp_xml_path, debug=False):
    """Import PP XML to database using wrapper.py"""
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
    if not run_subprocess(import_cmd, debug):
        raise RuntimeError(f"Failed to import PP XML: {pp_xml_path}")

    print(f"Successfully imported {pp_xml_path} to {db_path}")
    return db_path


def export_db_to_pp_xml(db_path, output_xml_path, debug=False):
    """Export database to PP XML using wrapper.py"""
    # Extract db_basename from db_path
    db_basename = Path(db_path).stem

    # Build export command
    export_cmd = [
        sys.executable,
        str(WRAPPER_PATH),
        "--exec",
        "export",
        "--db",
        db_basename,
        str(output_xml_path),
    ]
    if debug:
        export_cmd.append("--debug")

    # Run command
    if not run_subprocess(export_cmd, debug):
        raise RuntimeError(f"Failed to export to PP XML: {output_xml_path}")

    print(f"Successfully exported database to {output_xml_path}")


def process_single_transaction(conn, transaction, config, next_xmlid, next_order):
    """Process a single forex transaction and return True if successful"""

    # Extract IB account ID
    ib_account_id = transaction.get("accountId")

    # Extract currencies from symbol (e.g., "USD.HKD")
    currencies = transaction.get("symbol").split(".")
    first_currency = currencies[0]  # First currency in symbol (e.g., USD)
    second_currency = currencies[1]  # Second currency in symbol (e.g., HKD)

    # Determine source and target currencies based on buySell flag
    # BUY = Buy first currency (e.g., USD) from second currency (e.g., HKD)
    # SELL = Sell first currency (e.g., USD) to second currency (e.g., HKD)
    buy_sell = transaction.get("buySell")

    if buy_sell == "BUY":
        # Buying first currency (e.g., USD) from second currency (e.g., HKD)
        source_currency = second_currency  # Source is second currency (e.g., HKD)
        target_currency = first_currency  # Target is first currency (e.g., USD)
    elif buy_sell == "SELL":
        # Selling first currency (e.g., USD) to second currency (e.g., HKD)
        source_currency = first_currency  # Source is first currency (e.g., USD)
        target_currency = second_currency  # Target is second currency (e.g., HKD)
    else:
        # Default behavior if buySell is not specified or has an unexpected value
        print(f"Warning: Unknown buySell value '{buy_sell}', defaulting to BUY")
        source_currency = second_currency
        target_currency = first_currency

    print(
        f"Processing forex transaction: {ib_account_id} {first_currency}.{second_currency} "
        f"(Trade ID: {transaction.get('tradeID')}, {buy_sell})"
    )
    print(f"  Direction: {source_currency} -> {target_currency}")

    # Find matching PP accounts
    source_account_uuid = get_currency_account(
        conn, ib_account_id, source_currency, config
    )
    target_account_uuid = get_currency_account(
        conn, ib_account_id, target_currency, config
    )

    # Skip if can't find accounts (will only happen if fallback_strategy is "skip")
    if not source_account_uuid or not target_account_uuid:
        print(
            f"Skipping forex transaction {transaction.get('tradeID')}: Account not found"
        )
        return False

    # Format date - convert IB date format (YYYYMMDD) to ISO format
    trade_date = transaction.get("tradeDate")
    formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}T00:00"

    # Extract and process amounts based on the transaction type (BUY/SELL)
    proceeds_amount = abs(float(transaction.get("proceeds")))  # Always make positive
    quantity_amount = abs(float(transaction.get("quantity")))  # Always make positive

    # For BUY transactions:
    # - source_currency is second_currency (e.g., HKD), amount from proceeds
    # - target_currency is first_currency (e.g., USD), amount from quantity
    #
    # For SELL transactions:
    # - source_currency is first_currency (e.g., USD), amount from quantity
    # - target_currency is second_currency (e.g., HKD), amount from proceeds
    if buy_sell == "BUY":
        source_amount = proceeds_amount
        target_amount = quantity_amount
    else:  # SELL or default
        source_amount = quantity_amount
        target_amount = proceeds_amount

    # Convert to cents with proper rounding (Portfolio Performance stores monetary values as integers in cents)
    # Use round() instead of int() to preserve all decimal places
    source_amount = round(source_amount * 100)
    target_amount = round(target_amount * 100)

    # Ensure we never end up with zero for very small values (minimum is 1 cent)
    # Check if original value was non-zero but rounded to zero
    original_source = source_amount / 100
    if source_amount == 0 and proceeds_amount > 0:
        source_amount = 1  # Set to minimum 1 cent
        print(
            f"  Warning: Source amount rounded up to 0.01 {source_currency} (original: {proceeds_amount})"
        )

    original_target = target_amount / 100
    if target_amount == 0 and quantity_amount > 0:
        target_amount = 1  # Set to minimum 1 cent
        print(
            f"  Warning: Target amount rounded up to 0.01 {target_currency} (original: {quantity_amount})"
        )

    # Create description with transaction details
    description = f"Forex {source_currency} to {target_currency} (Trade ID: {transaction.get('tradeID')})"

    # Generate UUIDs for transactions
    transfer_out_uuid = str(uuid.uuid4())
    transfer_in_uuid = str(uuid.uuid4())

    # Current timestamp in ISO format with Z suffix
    now = datetime.now().isoformat() + "Z"

    # Extract commission information
    commission_amount = 0
    commission_currency = transaction.get("ibCommissionCurrency")

    if transaction.get("ibCommission") and commission_currency:
        # Make commission positive (it's usually negative in IB exports)
        commission_amount = abs(float(transaction.get("ibCommission")))
        commission_amount_raw = commission_amount
        commission_amount = round(
            commission_amount * 100
        )  # Convert to cents with proper rounding
        print(
            f"  Commission: {commission_amount_raw} {commission_currency} ({commission_amount} cents)"
        )

    # Determine which transaction (TRANSFER_OUT or TRANSFER_IN) should get the commission
    source_fees = 0
    target_fees = 0

    if commission_amount > 0:
        if commission_currency == source_currency:
            source_fees = commission_amount
            print(f"  Applying commission to source account ({source_currency})")
        elif commission_currency == target_currency:
            target_fees = commission_amount
            print(f"  Applying commission to target account ({target_currency})")
        else:
            print(
                f"  Warning: Commission currency {commission_currency} doesn't match either transaction currency"
            )
            # In this case, we don't apply the commission

    # Debug output
    print(
        f"  Source account: {source_account_uuid} ({source_currency}) Amount: {source_amount} Fees: {source_fees / 100 if source_fees else 0}"
    )
    print(
        f"  Target account: {target_account_uuid} ({target_currency}) Amount: {target_amount} Fees: {target_fees / 100 if target_fees else 0}"
    )

    # Insert TRANSFER_OUT
    insert_transfer_out(
        conn,
        transfer_out_uuid,
        source_account_uuid,
        formatted_date,
        source_currency,
        source_amount,  # Now positive per requirements
        description,
        "IB Flex Import",
        now,
        next_xmlid,
        next_order,
        fees=source_fees,
    )

    # Insert TRANSFER_IN
    insert_transfer_in(
        conn,
        transfer_in_uuid,
        target_account_uuid,
        formatted_date,
        target_currency,
        target_amount,
        description,
        "IB Flex Import",
        now,
        next_xmlid + 1,
        next_order + 1,
        fees=target_fees,
    )

    # Create cross-entry link
    insert_cross_entry(
        conn,
        source_account_uuid,
        transfer_out_uuid,
        target_account_uuid,
        transfer_in_uuid,
    )

    print(f"  Created transfer pair with IDs: {next_xmlid}, {next_xmlid + 1}")
    return True


def process_forex_transactions(ib_flex_path, db_path, config_path, debug=False):
    """Process forex transactions from IB Flex XML file and update database"""

    # Load configuration
    config = load_config(config_path)

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Parse IB Flex XML
        tree = ET.parse(ib_flex_path)
        root = tree.getroot()

        # Find forex transactions
        forex_transactions = []
        for trade in root.findall(".//Trade"):
            if (
                trade.get("assetCategory") == "CASH"
                and trade.get("symbol")
                and "." in trade.get("symbol")
            ):
                forex_transactions.append(trade)

        print(f"Found {len(forex_transactions)} forex transactions")

        # Get next available IDs
        next_xmlid = get_max_xmlid(conn) + 1
        next_order = get_max_order(conn) + 1

        # Process each transaction
        processed_count = 0
        skipped_count = 0

        for transaction in forex_transactions:
            try:
                if process_single_transaction(
                    conn, transaction, config, next_xmlid, next_order
                ):
                    processed_count += 1
                    next_xmlid += 2
                    next_order += 2
                else:
                    skipped_count += 1
            except Exception as e:
                print(f"Error processing transaction {transaction.get('tradeID')}: {e}")
                if debug:
                    import traceback

                    traceback.print_exc()
                skipped_count += 1

        # Commit changes
        conn.commit()

        print(f"Successfully processed {processed_count} forex transactions")
        if skipped_count > 0:
            print(
                f"Skipped {skipped_count} transactions due to errors or missing accounts"
            )

    except Exception as e:
        conn.rollback()
        print(f"Error processing forex transactions: {e}")
        if debug:
            import traceback

            traceback.print_exc()
        raise
    finally:
        conn.close()


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Process forex transactions from IB Flex XML and integrate with Portfolio Performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pp-xml", required=True, help="Path to Portfolio Performance XML file"
    )
    parser.add_argument("--ib-flex", required=True, help="Path to IB Flex XML file")
    parser.add_argument(
        "--output-xml",
        required=True,
        help="Path for output Portfolio Performance XML file",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to configuration file for account mappings",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


def main():
    """Main execution function"""
    args = parse_arguments()

    try:
        print("=== Forex Transaction Processor ===")
        print(f"Input PP XML:  {args.pp_xml}")
        print(f"IB Flex XML:   {args.ib_flex}")
        print(f"Output XML:    {args.output_xml}")
        print(f"Config:        {args.config}")
        print(f"Debug mode:    {'Enabled' if args.debug else 'Disabled'}")
        print("")

        # Step 1: Import PP XML to DB using wrapper.py
        print("Step 1: Importing Portfolio Performance XML to database...")
        db_path = import_pp_xml_to_db(args.pp_xml, args.debug)

        # Step 2: Process IB Flex XML and update DB
        print("\nStep 2: Processing forex transactions from IB Flex XML...")
        process_forex_transactions(args.ib_flex, db_path, args.config, args.debug)

        # Step 3: Export updated DB to XML using wrapper.py
        print("\nStep 3: Exporting updated database to Portfolio Performance XML...")
        export_db_to_pp_xml(db_path, args.output_xml, args.debug)

        print(f"\nSuccess! Processed forex transactions and created {args.output_xml}")

    except Exception as e:
        print(f"\nError: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
