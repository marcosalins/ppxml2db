# Product Context: ppxml2db

## Problem Statement
PortfolioPerformance (PP) is a powerful open-source portfolio tracking application that stores data in XML format. However, this XML format is not designed for human readability or easy manipulation, as it uses XStream's internal serialization format. This makes it difficult for users to:
- Create custom reports
- Perform advanced data analysis
- Automate data entry or modifications
- Add features not supported by PP natively

## Solution
ppxml2db addresses these challenges by:
1. Providing a conversion path between PP's XML format and SQLite databases
2. Enabling SQL-based access to portfolio data
3. Supporting round-trip conversions to ensure data integrity
4. Matching PP's internal object model in the database schema

## User Experience Goals
- Simple command-line interface for import/export operations
- Reliable data conversion with minimal differences
- Flexible SQL access for custom queries and reports
- Support for programmatic modifications with clean export back to PP

## Use Cases

### Data Analysis
Users can run complex SQL queries against their portfolio data to gain insights not available through PP's native interface:
- Custom performance metrics
- Advanced asset allocation analysis
- Tax-related calculations
- Correlation analysis between assets

### Data Modification
Users can programmatically:
- Import transactions from custom sources
- Batch update security information
- Add custom categorization
- Apply complex data transformations
- Automatically tag or categorize assets

### Integration
- Bridge PP data with other financial tools
- Enable custom data pipelines
- Support backup and versioning strategies
- Facilitate data migration

## Value Proposition
ppxml2db transforms PP from a standalone application to a component in a more flexible financial data ecosystem, significantly extending its capabilities while preserving its core strengths.
