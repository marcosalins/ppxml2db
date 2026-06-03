# Project: forex_db_corrector.py Implementation

## Goal
Create a Python script (`forex_db_corrector.py`) to identify and correct discrepancies in how forex transactions are recorded in a Portfolio Performance (PP) database. The script will compare DB records against IB Flex XMLs and update the `xact` table in the DB if errors are found (limited to `xact.type`, `xact.currency`, `xact.amount`).

## Subtasks

- [ ] **Task 1: Create `progress.md` File** (Completed by this task)
- [ ] **Task 2: Script Skeleton and Setup (`forex_db_corrector.py`)**
    - Create basic file structure, imports, constants.
    - Implement argument parsing (`--pp-xml`, `--output-pp-xml`, `--export-db-path`, `--debug`).
    - Setup logging.
    - Outline `main()` function.
- [ ] **Task 3: Implement Helper Function Integration/Adaptation**
    - Copy/adapt `load_config(config_path)`.
    - Copy/adapt `map_ib_currency_to_pp(ib_currency, forex_config)`.
    - Copy/adapt `discover_ib_xml_files(base_dir)`.
    - Copy/adapt `get_currency_account(conn, ib_account_id, currency_code, account_mappings, fallback_strategy)`.
    - Implement `decimal_to_cents(decimal_value)`.
- [ ] **Task 4: Implement Step 1 - Temporary DB Generation**
    - Implement `generate_temp_db(pp_xml_path, temp_db_dir)`:
        - Call `wrapper.py --exec import <pp_xml_path>`.
        - Move/copy generated DB to `temp_db_dir`.
- [ ] **Task 5: Implement Core Logic - `find_matching_transaction_pair()`**
    - Implement `find_matching_transaction_pair(conn, xml_trade_element, config)`:
        - Match using date + amount (cents) + currency pair.
- [ ] **Task 6: Implement Core Logic - `correct_transaction_directionality()`**
    - Implement `correct_transaction_directionality(conn, xml_trade_element, db_out_leg_row, db_in_leg_row, config)`:
        - Determine expected DB state from XML.
        - Perform SQL UPDATEs on `xact` table if discrepancies found.
- [ ] **Task 7: Implement Core Logic - `correct_forex_transactions_in_db()`**
    - Implement `correct_forex_transactions_in_db(db_path, ib_flex_base_dir, config)`:
        - Orchestrate XML discovery, parsing, matching, and correction calls.
- [ ] **Task 8: Implement Step 4 - Optional DB Export**
    - Implement `export_corrected_db(temp_db_path, export_path)`.
- [ ] **Task 9: Implement Step 5 - Generate Corrected PP XML**
    - Implement `generate_corrected_pp_xml(temp_db_path, output_xml_path)`:
        - Call `db2ppxml.py <temp_db_path> <output_xml_path>`.
- [ ] **Task 10: Final Integration and Testing**
    - Integrate all functions within `main()`.
    - Refine error handling and logging.
    - Perform basic testing.
