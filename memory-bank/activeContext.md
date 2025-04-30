# Active Context: ppxml2db

## Current Focus
- Initial setup and familiarization with the ppxml2db project
- Understanding the core functionality and architecture
- Documenting the project structure and workflows
- Establishing a foundation for future development

## Recent Changes
- Creation of memory bank documentation
- No code changes made yet

## Next Steps
- Examine the Python conversion scripts in detail (ppxml2db.py and db2ppxml.py)
- Analyze the database schema defined in SQL files
- Understand the data model and how it maps between XML and database
- Run a test conversion to observe the process in action
- Identify areas for potential improvement or extension

## Active Decisions and Considerations
- Understanding the trade-offs between exact XML preservation and clean database schema
- Considering how to handle unsupported features (Investment Plans, Exchange Rates, etc.)
- Evaluating the approach to round-trip conversions and known edge cases
- Determining the appropriate testing methodology for conversion quality

## Important Patterns and Preferences
- Database schema closely mirrors PortfolioPerformance's object model
- Command-line interface for core operations
- Separation of concerns between import and export processes
- Individual SQL files for each table definition
- Focus on preserving data semantics rather than XML structure

## Learnings and Project Insights
- The project addresses the challenge of working with PortfolioPerformance's proprietary XML format
- XStream serialization format is not designed for human readability or direct manipulation
- The database schema serves as both a practical solution and a proof-of-concept for potential PP integration
- Round-trip conversion is critical for validating the accuracy of transformations
- The solution enables a wide range of custom analyses, reports, and modifications not possible with PP alone
