# Forex Transaction Processor for Portfolio Performance

This tool processes forex transactions from Interactive Brokers (IB) Flex XML reports and integrates them into Portfolio Performance (PP) as account transfers between currency accounts.

## Overview

When trading forex on Interactive Brokers, the transactions appear in the Flex Statement XML as CASH category trades with currency pairs like "USD.HKD". Portfolio Performance doesn't automatically import these as transfers between currency accounts.

This tool:
1. Reads your Portfolio Performance XML file
2. Imports it to a SQLite database using the existing wrapper.py
3. Processes IB Flex XML to find forex transactions
4. Adds these as proper TRANSFER_IN/TRANSFER_OUT pairs between currency accounts
5. Exports the updated database back to a Portfolio Performance XML file

## Requirements

- Python 3.6+ 
- An existing Portfolio Performance XML file
- An Interactive Brokers Flex Statement XML file
- Currency accounts already set up in Portfolio Performance

## Installation

This tool is designed to work alongside the existing ppxml2db tools:

1. Place the `forex_processor.py` script in the same directory as your `wrapper.py`
2. Create a `forex_config.json` file or let the script generate a default one

## Usage

Basic usage:

```
python forex_processor.py --pp-xml portfolio.xml --ib-flex flex_statement.xml --output-xml updated_portfolio.xml
```

All options:

```
python forex_processor.py --pp-xml portfolio.xml --ib-flex flex_statement.xml --output-xml updated_portfolio.xml [--config custom_config.json] [--debug]
```

### Parameters:

- `--pp-xml`: Path to your Portfolio Performance XML file
- `--ib-flex`: Path to your Interactive Brokers Flex Statement XML file
- `--output-xml`: Path where the updated Portfolio Performance XML will be saved
- `--config`: (Optional) Path to a custom configuration file
- `--debug`: (Optional) Enable debug mode with detailed logging

## Configuration

The tool uses a configuration file (`forex_config.json`) to map IB account IDs to Portfolio Performance account naming patterns. The default configuration looks like:

```json
{
  "account_mappings": {
    "Lia": {
      "pattern": "Lia_{currency}",
      "description": "Lia's accounts"
    },
    "Marcos": {
      "pattern": "Marcos_{currency}",
      "description": "Marcos's primary accounts"
    },
    "Marcos_MS": {
      "pattern": "Marcos_MS_{currency}",
      "description": "Marcos's MS accounts"
    },
    "Mariana": {
      "pattern": "Mariana_{currency}",
      "description": "Mariana's accounts"
    }
  },
  "fallback_strategy": "error"
}
```

### Account Mappings

For each IB account ID (like "Lia" or "Marcos"), specify a pattern for how the corresponding Portfolio Performance accounts are named. The pattern should include `{currency}` which will be replaced with the actual currency code (USD, HKD, etc.).

### Fallback Strategy

What to do if an account can't be found:
- `"error"`: Raise an error and stop processing (default)
- `"skip"`: Skip the transaction and continue with others
- `"map"`: (Not implemented yet) Use a specific mapping for unknown accounts

## How It Works

For each forex transaction in the IB Flex XML:

1. It extracts the IB account ID (e.g., "Lia")
2. It identifies the currency pair (e.g., "USD.HKD")
3. It finds the matching Portfolio Performance accounts using the pattern in the config
4. It creates a TRANSFER_OUT from one currency account (e.g., Lia_HKD)
5. It creates a TRANSFER_IN to the other currency account (e.g., Lia_USD)
6. It links these transactions with a cross-entry record

## Troubleshooting

### Missing Accounts

If you get errors about missing accounts, make sure:
1. Your account naming in Portfolio Performance matches the patterns in the config file
2. You have created accounts for all required currencies

### Database Issues

If you encounter database errors:
1. Try running with `--debug` for more detailed error messages
2. Check that your wrapper.py script is properly configured and working

### XML Format Issues

If the tool fails to parse the XML files:
1. Verify your IB Flex Statement is properly formatted
2. Ensure your Portfolio Performance XML file is valid

## Examples

### Basic Example

```
python forex_processor.py --pp-xml "C:/Users/myuser/Documents/portfolio.xml" --ib-flex "C:/Users/myuser/Downloads/flex.xml" --output-xml "C:/Users/myuser/Documents/updated_portfolio.xml"
```

### With Custom Config

```
python forex_processor.py --pp-xml portfolio.xml --ib-flex flex.xml --output-xml updated_portfolio.xml --config my_custom_config.json
```

### Debug Mode

```
python forex_processor.py --pp-xml portfolio.xml --ib-flex flex.xml --output-xml updated_portfolio.xml --debug
