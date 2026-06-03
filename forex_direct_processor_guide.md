# Direct Forex Transaction Processor Guide

## Overview

The `forex_direct_processor.py` script is designed to process forex transactions from Interactive Brokers Flex XML reports and integrate them directly into Portfolio Performance XML files **without using a database**. 

This approach preserves all original XML structures, especially taxonomies, preventing corruption issues that can occur with the database import/export approach.

## Why Use This Script?

The original `forex_processor.py` script uses a database approach (import to SQLite, modify, export back to XML), which can sometimes cause issues with complex XML structures like taxonomies. This can lead to ClassCastException errors when opening the file in Portfolio Performance.

The direct processor works by:
1. Directly reading and parsing the Portfolio Performance XML
2. Reading forex transactions from the IB Flex report
3. Creating new transaction elements in the XML
4. Writing the updated XML to a new file

This preserves all original structures while adding only the required forex transactions.

## Prerequisites

- Python 3.6 or higher
- Original Portfolio Performance XML file
- Interactive Brokers Flex Query XML report containing forex transactions

## Configuration

The script uses the same `forex_config.json` configuration file as the original processor. This file maps IB account IDs to Portfolio Performance account patterns.

Example configuration:
```json
{
  "account_mappings": {
    "Lia": {
      "pattern": "Lia_{currency}",
      "description": "Lia's accounts"
    },
    "Marcos": {
      "pattern": "Marcos_{currency}",
      "description": "Marcos's accounts"
    },
    "Mariana": {
      "pattern": "Mariana_{currency}",
      "description": "Mariana's accounts"
    }
  },
  "fallback_strategy": "error"
}
```

## Usage

```
python forex_direct_processor.py --pp-xml portfolio.xml --ib-flex flex_statement.xml --output-xml updated_portfolio.xml [--config config.json] [--debug]
```

### Arguments

- `--pp-xml`: Path to your Portfolio Performance XML file
- `--ib-flex`: Path to the IB Flex XML report
- `--output-xml`: Path where the updated XML file will be saved
- `--config`: (Optional) Path to configuration file, defaults to forex_config.json in the script directory
- `--debug`: (Optional) Enable debug mode for more detailed output

## Example

```
python forex_direct_processor.py --pp-xml "My Portfolio.xml" --ib-flex "flex_statement.xml" --output-xml "My Portfolio Updated.xml"
```

## Features

- Correctly processes buy and sell forex transactions
- Handles commissions appropriately by matching to the correct currency
- Preserves all taxonomies and other complex structures in the Portfolio Performance file
- Creates properly linked account transfers with cross-entries
- Properly handles small decimal values by rounding to the nearest cent
- Ensures minimal values (1 cent) for very small transactions that would otherwise round to zero

## Troubleshooting

If you encounter issues:

1. Use the `--debug` flag to get more detailed error information
2. Check that your configuration file correctly maps IB account IDs to Portfolio Performance accounts
3. Verify that the Portfolio Performance accounts with the required currencies exist in your XML file
4. Ensure your IB Flex report includes forex transactions (assetCategory="CASH" with a symbol containing a ".")

## Comparison with Original Processor

| Feature | forex_processor.py | forex_direct_processor.py |
|---------|-------------------|------------------------|
| Method | Database import/export | Direct XML manipulation |
| Speed | Slower | Faster |
| Preserves taxonomies | May corrupt | Yes, fully preserves |
| Handles small amounts | Yes | Yes |
| Handles commissions | Yes | Yes |

## Common Issues and Solutions

### Missing Accounts

If the script can't find matching accounts in your Portfolio Performance file, it will skip those transactions. Make sure your configuration file properly maps IB account IDs to Portfolio Performance account patterns, and that these accounts exist in your XML file.

### XML Structure Issues

If you encounter XML structure issues, ensure you're using a valid Portfolio Performance XML file as input. The direct processor is designed to work with standard Portfolio Performance XML files without modifying their structure.
