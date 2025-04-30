# Project Brief: ppxml2db

## Project Definition
ppxml2db is a toolkit that provides bidirectional conversion between PortfolioPerformance XML files and SQLite databases. The project aims to make PortfolioPerformance data more accessible for analysis, reporting, and programmatic modification.

## Core Goals
1. Convert PortfolioPerformance XML files to SQLite database format
2. Export database content back to PortfolioPerformance XML format
3. Achieve near-perfect round-trip conversion (import-export cycle)
4. Maintain database schema that closely matches PortfolioPerformance's internal object model
5. Enable custom data manipulation, reporting, and extensions through database access

## Target Users
- PortfolioPerformance users who need custom reports or data analysis
- Developers creating tools that interact with PortfolioPerformance data
- Users who want to automate modifications to their portfolio data
- Potential contributors to PortfolioPerformance who want to explore database backend integration

## Success Criteria
- Successful import of PortfolioPerformance XML files to database
- Successful export from database back to XML with minimal differences
- Ability to perform data queries and manipulations through SQL
- Preservation of all essential PortfolioPerformance data during conversions
- Support for future PortfolioPerformance versions and features
