You are to build a Python wrapper script to automate and simplify the use of a system originally built around a script called `ppxml2db.py`, which is used to import and export data between a "PP XML" file and a database file. This system was cloned from another GitHub repository and currently requires several manual steps as described in its `execution_guide`.

**Project Goals:**
- Automate the workflow described in the execution_guide, removing manual steps.
- Provide a single command-line interface (CLI) wrapper for users to easily import an XML file into a database or export the database back to XML.

**Wrapper Features:**

1. **Main Operations (`--exec`):**
   - The wrapper must accept a mandatory argument `--exec` which can be either `import` or `export`.
     - `import`: Imports a PP XML file into a database.
     - `export`: Exports the database back to a PP XML file.

2. **Import Functionality (`--exec import`):**
   - Accept an optional XML file argument. If not provided, default to:  
     `C:\Users\malin\OneDrive\pp_file\total_portfolio.xml`
   - Automatically handle the database file creation and management; users do not provide the DB name or path.
   - Before importing, check if a DB already exists for the given XML:
     - If yes: replace the content of the existing DB with the content from the new XML.
     - If no: create an empty DB and load content from the XML.
   - All manual steps listed in the execution guide for creating the DB and importing XML should be handled by the wrapper.

3. **Export Functionality (`--exec export`):**
   - Accept a mandatory DB name argument.
   - Accept an optional XML file argument. If not provided, overwrite the original XML file used for import.
   - All manual steps listed in the execution guide for exporting the DB back to XML should be handled by the wrapper.

4. **General Requirements:**
   - The wrapper should invoke `ppxml2db.py` as needed to carry out the import or export.
   - All internal management of DB files should be abstracted away from the user (auto-name, auto-locate, etc.).
   - The script should handle errors gracefully and provide clear command-line feedback.

**Summary Workflow:**

- User runs:  
  `python wrapper.py --exec import [optional: path/to/input.xml]`
    - Wrapper checks for DB existence, creates or overwrites as needed, and loads XML.

- User runs:  
  `python wrapper.py --exec export --db db_name [optional: path/to/output.xml]`
    - Wrapper exports DB to XML, defaulting to overwriting the source XML if output not specified.

**Reference:**
- Review the original `execution_guide` and ensure all steps are automated.
- Also it a must to read all md files from the memory-bank folder to have a better understand of this project.
- Use the default paths and file names described above unless overridden by user input.

**Deliverables:**
- A single Python script (`wrapper.py`) implementing the described behavior.
- Clear inline comments explaining the code logic.
- Usage documentation for the CLI.

---

If you need further clarifications, please specify how database files are named and stored, and any additional requirements for error handling or logging.