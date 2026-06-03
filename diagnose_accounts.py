#!/usr/bin/env python3
"""
Diagnostic script to inspect Portfolio Performance database accounts
and help fix the forex_db_corrector.py account mapping issues.
"""

import sqlite3
import sys
from pathlib import Path

def inspect_database_accounts(db_path):
    """Inspect the accounts in the Portfolio Performance database."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("=" * 80)
        print("PORTFOLIO PERFORMANCE DATABASE ACCOUNT INSPECTION")
        print("=" * 80)
        
        # Get all accounts (without note column which may not exist)
        cursor.execute("SELECT uuid, name, currency FROM account ORDER BY name, currency")
        accounts = cursor.fetchall()
        
        if not accounts:
            print("No accounts found in database!")
            return
        
        print(f"\nFound {len(accounts)} accounts:\n")
        
        # Display all accounts
        for account in accounts:
            print(f"Name:     '{account['name']}'")
            print(f"Currency: {account['currency']}")
            print(f"UUID:     {account['uuid']}")
            print()
        
        # Look for IB-related accounts specifically
        print("\n" + "=" * 80)
        print("IB-RELATED ACCOUNTS (containing 'IB', 'Marcos', 'Mariana', 'Lia')")
        print("=" * 80)
        
        ib_keywords = ['IB', 'Marcos', 'Mariana', 'Lia', 'marcos', 'mariana', 'lia']
        ib_accounts = []
        
        for account in accounts:
            name = account['name'].lower()
            if any(keyword.lower() in name for keyword in ib_keywords):
                ib_accounts.append(account)
        
        if ib_accounts:
            print(f"\nFound {len(ib_accounts)} IB-related accounts:\n")
            for account in sorted(ib_accounts, key=lambda x: (x['name'], x['currency'])):
                print(f"Name:     '{account['name']}'")
                print(f"Currency: {account['currency']}")
                print(f"UUID:     {account['uuid']}")
                print()
                
            # Generate suggested patterns
            print("\n" + "=" * 60)
            print("SUGGESTED FOREX_CONFIG.JSON PATTERNS")
            print("=" * 60)
            
            # Try to deduce patterns
            account_holders = {}
            for account in ib_accounts:
                name = account['name']
                currency = account['currency']
                name_lower = name.lower()
                
                # Determine account holder
                if 'marcos' in name_lower:
                    if 'ms' in name_lower:
                        holder = 'Marcos_MS'
                    elif 'rrsp' in name_lower:
                        holder = 'U15692427'  # RRSP account
                    else:
                        holder = 'Marcos'
                elif 'mariana' in name_lower:
                    holder = 'Mariana'
                elif 'lia' in name_lower:
                    holder = 'Lia'
                else:
                    continue
                
                if holder not in account_holders:
                    account_holders[holder] = []
                account_holders[holder].append((name, currency))
            
            print("\nDetected account patterns:")
            for holder, accounts_list in sorted(account_holders.items()):
                print(f"\n{holder}:")
                for name, currency in sorted(accounts_list):
                    print(f"  {name} ({currency})")
                    
                    # Try to deduce pattern
                    if currency and name.endswith(' ' + currency):
                        pattern = name[:-len(' ' + currency)] + ' {currency}'
                        print(f"    Suggested pattern: '{pattern}'")
                    elif currency and name.endswith('-' + currency):
                        pattern = name[:-len('-' + currency)] + '-{currency}'
                        print(f"    Suggested pattern: '{pattern}'")
                    elif currency and name.endswith('_' + currency):
                        pattern = name[:-len('_' + currency)] + '_{currency}'
                        print(f"    Suggested pattern: '{pattern}'")
                    else:
                        print(f"    No clear pattern detected")
            
            print(f"\n\nSuggested forex_config.json update:")
            print('"account_mappings": {')
            
            for holder, accounts_list in sorted(account_holders.items()):
                if accounts_list:
                    sample_name, sample_currency = accounts_list[0]
                    
                    # Deduce pattern from first account
                    if sample_currency and sample_name.endswith(' ' + sample_currency):
                        pattern = sample_name[:-len(' ' + sample_currency)] + ' {currency}'
                    elif sample_currency and sample_name.endswith('-' + sample_currency):
                        pattern = sample_name[:-len('-' + sample_currency)] + '-{currency}'
                    elif sample_currency and sample_name.endswith('_' + sample_currency):
                        pattern = sample_name[:-len('_' + sample_currency)] + '_{currency}'
                    else:
                        pattern = sample_name.replace(sample_currency, '{currency}')
                    
                    print(f'  "{holder}": {{')
                    print(f'    "pattern": "{pattern}",')
                    print(f'    "description": "{holder}\'s accounts"')
                    print('  },')
            
            print('}')
        else:
            print("No IB-related accounts found!")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    
    return True

def main():
    if len(sys.argv) != 2:
        print("Usage: python diagnose_accounts.py <path_to_database.db>")
        print("\nExample:")
        print("  python diagnose_accounts.py temp_db/lia_test_to_correct.db")
        sys.exit(1)
    
    db_path = sys.argv[1]
    db_file = Path(db_path)
    
    if not db_file.exists():
        print(f"Database file not found: {db_path}")
        sys.exit(1)
    
    print(f"Inspecting database: {db_path}")
    success = inspect_database_accounts(db_path)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
