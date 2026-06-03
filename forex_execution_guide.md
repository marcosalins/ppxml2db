# Forex Transaction Processor - Execution Guide

This guide provides step-by-step instructions for using the Forex Transaction Processor to import forex transactions from Interactive Brokers into Portfolio Performance.

## Prerequisites

Before starting, ensure you have:

- Python 3.6 or higher installed
- Portfolio Performance application installed
- Portfolio Performance XML file with your portfolio data
- Interactive Brokers Flex Statement in XML format
- Currency accounts already set up in Portfolio Performance

## Setup Instructions

1. **File Organization**
   
   Place all required files in your ppxml2db directory:
   - `wrapper.py` (existing file)
   - `ppxml2db.py` (existing file)
   - `db2ppxml.py` (existing file)
   - `forex_processor.py` (new file)
   - `forex_config.json` (new file)

2. **Configure Account Mappings**
   
   Edit `forex_config.json` to match your account naming convention:
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
       }
     },
     "fallback_strategy": "error"
   }
   ```
   
   Adjust the patterns to match how your accounts are named in Portfolio Performance.

## Execution Steps

### Step 1: Export Your Portfolio from Portfolio Performance

1. Open Portfolio Performance
2. Go to File → Save As...
3. Save your portfolio as an XML file (e.g., `portfolio.xml`)

### Step 2: Export Flex Statement from Interactive Brokers

1. Log in to Interactive Brokers Account Management
2. Navigate to Reports → Flex Queries
3. Create a new Flex Query or use an existing one
   - Ensure "Trades" section is included
   - Set the date range as needed
4. Run the Flex Query and download the XML file (e.g., `ibflex.xml`)

### Step 3: Process Forex Transactions

1. Open a command prompt or terminal
2. Navigate to your ppxml2db directory
3. Run the processor with:

   ```bash
   python forex_processor.py --pp-xml path/to/portfolio.xml --ib-flex path/to/ibflex.xml --output-xml path/to/updated_portfolio.xml
   ```
   
   Replace the paths with the actual locations of your files.

4. The script will:
   - Import your Portfolio Performance XML
   - Process the IB Flex XML for forex transactions
   - Create transaction pairs for each forex transaction
   - Export the updated database to a new Portfolio Performance XML

### Step 4: Import Updated XML into Portfolio Performance

1. Open Portfolio Performance
2. Go to File → Open...
3. Select your updated XML file (`updated_portfolio.xml`)
4. Verify that the forex transactions appear as transfers between your currency accounts

## Common Use Cases

### Processing a Specific Date Range

If you want to process forex transactions for a specific period:

1. Generate an IB Flex Statement for that exact date range
2. Run the processor with that Flex Statement XML

### Using Custom Configuration

To use a custom configuration file:

```bash
python forex_processor.py --pp-xml portfolio.xml --ib-flex ibflex.xml --output-xml updated_portfolio.xml --config my_custom_config.json
```

### Debug Mode

If you encounter issues, run in debug mode for detailed logging:

```bash
python forex_processor.py --pp-xml portfolio.xml --ib-flex ibflex.xml --output-xml updated_portfolio.xml --debug
```

## Troubleshooting

### Missing Account Error

If you see an error about missing accounts:

1. Check your `forex_config.json` and ensure the patterns match your PP account names
2. Verify that all required currency accounts exist in Portfolio Performance
3. If needed, modify the `fallback_strategy` to "skip" to ignore problematic transactions

### XML Parsing Error

If you encounter XML parsing errors:

1. Verify your IB Flex Statement is properly formatted
2. Check that your Portfolio Performance XML is valid
3. Try opening and resaving the XML files to ensure correct encoding

### Database Issues

If there are database-related errors:

1. Run with `--debug` for more detailed error messages
2. Ensure your wrapper.py is properly configured and working
3. Check permissions on the directory for database files

## Advanced: Custom Account Mapping

If you have more complex account names, you can adjust the patterns in `forex_config.json`:

```json
{
  "account_mappings": {
    "U1234567": {
      "pattern": "IB_{currency}_Trading",
      "description": "IB Trading accounts"
    },
    "U7654321": {
      "pattern": "Investment_{currency}",
      "description": "Investment accounts"
    }
  }
}
```

The `{currency}` placeholder will be replaced with the actual currency code (USD, HKD, etc.).
