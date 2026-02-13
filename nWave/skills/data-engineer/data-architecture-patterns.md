---
name: data-architecture-patterns
description: Data architecture patterns (warehouse, lake, lakehouse, mesh), ETL/ELT pipelines, streaming architectures, scaling strategies, and schema design patterns
---

# Data Architecture Patterns

## Architecture Selection Decision Tree

```
What data types do you have?
  Structured only -> Data Warehouse
  Mixed (structured + semi-structured + unstructured) ->
    Do you need SQL analytics on all data? -> Data Lakehouse
    Is data science/ML the primary use case? -> Data Lake
    Is your organization large with autonomous domain teams? -> Data Mesh
```

## Data Warehouse

### Characteristics
- Schema: Structured, schema-on-write
- Data types: Primarily structured (tables, rows, columns)
- Governance: Centralized, strong governance by design
- Query: SQL-based analytics, BI reporting
- Architecture: Centralized single source of truth

### Schema Patterns

**Star Schema**:
- Central fact table (measures/metrics) surrounded by dimension tables (descriptors)
- Denormalized dimensions for query performance
- Best for: BI dashboards, standard reporting

```
         dim_date
            |
dim_customer--fact_sales--dim_product
            |
         dim_store
```

**Snowflake Schema**:
- Normalized dimensions (dimension tables reference other dimension tables)
- Reduces storage but increases JOIN complexity
- Best for: Environments where storage cost matters more than query speed

### Kimball vs Inmon Methodology

**Kimball (Bottom-Up)**:
- Build data marts first, integrate later
- Star schema oriented, business-process driven
- Faster initial delivery, iterative approach
- Best for: Organizations wanting quick wins, department-level analytics

**Inmon (Top-Down)**:
- Build enterprise data warehouse first, derive data marts
- Normalized (3NF) enterprise model
- Higher upfront effort, comprehensive architecture
- Best for: Large enterprises needing single source of truth from day one

### Technology Examples
Snowflake, Amazon Redshift, Google BigQuery, Azure Synapse Analytics

## Data Lake

### Characteristics
- Schema: Schema-on-read, flexible structure
- Data types: All formats (structured, semi-structured, unstructured)
- Storage: Raw data preserved in native format
- Query: SQL (Athena, Spark SQL), programmatic (PySpark, Pandas)
- Risk: "Data swamp" without proper governance and cataloging

### Organization Pattern
```
data-lake/
  raw/           # Landing zone - original format
  curated/       # Cleaned, validated, standardized
  processed/     # Transformed for specific use cases
  archive/       # Historical data, cold storage
```

### Anti-Patterns
- No metadata catalog -> data becomes undiscoverable
- No access controls -> security and compliance risk
- No data quality checks -> garbage in, garbage out
- Storing everything without retention policy -> cost grows unbounded

### Technology Examples
Amazon S3 + Athena/Glue, Azure Data Lake Storage + Synapse, HDFS + Hive

## Data Lakehouse

### Characteristics
- Combines warehouse reliability with lake flexibility
- Schema enforcement on write with schema evolution support
- ACID transactions on data lake storage
- Supports both BI/SQL analytics and ML/data science workloads

### Medallion Architecture (Bronze / Silver / Gold)

```
Bronze (Raw)          Silver (Validated)       Gold (Business-Ready)
- Raw ingestion       - Cleaned, validated     - Aggregated
- Schema-on-read      - Deduplicated           - Business logic applied
- Full history        - Schema enforced        - Star/snowflake schema
- Audit trail         - Standardized formats   - Ready for BI/reporting
```

**Bronze Layer**:
- Raw data as-is from source systems
- Append-only for auditability
- Partitioned by ingestion date
- Minimal transformations (format conversion only)

**Silver Layer**:
- Data quality rules applied (null checks, range validation, referential integrity)
- Deduplication on business keys
- Schema standardization (consistent naming, types)
- Slowly Changing Dimensions (SCD) applied

**Gold Layer**:
- Business-level aggregations
- Dimensional models (star/snowflake schema)
- Pre-computed metrics and KPIs
- Optimized for query performance (partitioned, indexed)

### Technology Examples
Databricks (Delta Lake), Apache Iceberg, Apache Hudi

## Data Mesh

### Core Principles (Martin Fowler)
1. **Domain-oriented ownership**: Data owned by domain teams, not central data team
2. **Data as a product**: Each domain publishes discoverable, trustworthy, self-describing data products
3. **Self-serve data platform**: Infrastructure team provides platform for domain teams to build data products
4. **Federated computational governance**: Global standards (interoperability, security) with domain autonomy

### When to Use Data Mesh
- Large organization with multiple autonomous domain teams
- Central data team is a bottleneck
- Domain expertise is needed to model and maintain data correctly
- Organization has platform engineering maturity

### When to Avoid
- Small team (< 50 engineers)
- Simple data architecture needs
- No platform engineering capability
- Unclear domain boundaries

## ETL vs ELT Pipeline Design

### ETL (Extract-Transform-Load)
```
Source -> [Extract] -> Staging -> [Transform] -> [Load] -> Target
```
- Transform before loading using dedicated engine (Informatica, Talend, SSIS)
- Best for: Complex transformations, constrained target systems, regulatory requirements (cannot store raw PII)
- Scaling: Limited by transformation engine capacity

### ELT (Extract-Load-Transform)
```
Source -> [Extract] -> [Load] -> Target -> [Transform in-place]
```
- Load raw data first, transform using target system's compute (dbt, Snowflake SQL, BigQuery SQL)
- Best for: Cloud data warehouses with elastic compute, preserving raw data, schema evolution
- Scaling: Scales with target system (cloud elastic compute)

### Pipeline Design Principles
- **Idempotency**: Re-running a pipeline produces the same result (use MERGE/upsert, not INSERT)
- **Incremental processing**: Process only new/changed data (use watermarks, change data capture)
- **Schema evolution**: Handle added/removed columns gracefully (use schema registry)
- **Data quality gates**: Validate data between pipeline stages (null rates, row counts, value ranges)
- **Observability**: Log pipeline metrics (rows processed, duration, errors, data freshness)

### Orchestration
- Apache Airflow: DAG-based workflow orchestration, Python-native, wide adoption
- Prefect: Modern alternative with dynamic workflows
- Dagster: Software-defined assets approach

## Streaming Architecture

### Apache Kafka
- Distributed event streaming platform
- Use as: Event bus, message broker, stream storage
- Key concepts: Topics, partitions, consumer groups, offsets
- Guarantees: At-least-once delivery (exactly-once with transactions)
- Retention: Configurable retention period or compacted topics

### Apache Flink
- Stateful stream processing engine
- Use as: Real-time analytics, event processing, CDC processing
- Key concepts: DataStreams, windows (tumbling, sliding, session), state management
- Guarantees: Exactly-once processing with checkpointing

### Kafka + Flink Pattern
```
Sources -> Kafka (event storage) -> Flink (stream processing) -> Sinks
```
- Kafka provides durable, scalable event buffer
- Flink provides stateful computation (aggregations, joins, pattern detection)
- Combined: end-to-end exactly-once semantics

### When to Use Streaming vs Batch
- **Streaming**: Real-time dashboards, fraud detection, IoT processing, event-driven architectures
- **Batch**: Overnight reporting, historical analysis, large-scale transformations, ML training
- **Lambda architecture**: Parallel batch + stream paths (complex, consider Kappa instead)
- **Kappa architecture**: Stream-only, reprocess from Kafka log (simpler, requires Kafka retention)

## Scaling Strategies

### Vertical Scaling (Scale Up)
- Add more CPU, RAM, storage to existing server
- Simpler operations, no application changes
- Hard limit: largest available hardware
- Use first: simple, effective for moderate growth

### Horizontal Scaling (Scale Out)

#### Read Replicas
- Replicate data to read-only copies
- Route read traffic to replicas, writes to primary
- Replication lag is the trade-off (eventual consistency for reads)
- Use for: Read-heavy workloads (reporting, search)

#### Partitioning (Within Single Server)
- **Range partitioning**: By value range (date ranges, alphabetical)
- **List partitioning**: By discrete values (region, category)
- **Hash partitioning**: By hash of partition key (even distribution)
- Benefits: Query pruning (only scan relevant partitions), maintenance (drop old partitions)

#### Sharding (Across Multiple Servers)
- Distribute data across multiple database instances
- Each shard holds a subset of data based on shard key
- Strategies: Range-based, hash-based, directory-based, geographic

**Shard Key Selection** (the most impactful decision):
- High cardinality: Many distinct values for even distribution
- Even access frequency: Avoid hot shards from skewed access patterns
- Query alignment: Most queries should target a single shard
- Avoid monotonically increasing keys (e.g., auto-increment) as shard keys — causes hot spots

**Challenges**:
- Cross-shard queries require scatter-gather
- Distributed transactions (2PC) are complex and slow
- Resharding is operationally expensive
- Application complexity increases

### Scaling Decision Guide
```
Current load exceeding single server?
  NO -> Optimize queries and indexes first
  YES -> Is it read-heavy?
    YES -> Add read replicas
    NO (write-heavy) -> Is data naturally partitionable?
      YES -> Partition within server first, then shard if needed
      NO -> Consider write-optimized databases (Cassandra, DynamoDB)
```

## Database Normalization vs Denormalization

### When to Normalize (3NF)
- OLTP workloads with frequent writes
- Data integrity is paramount
- Storage optimization matters
- Write performance over read performance

### When to Denormalize
- OLAP/analytics workloads (star schema)
- Read-heavy with predictable query patterns
- Query performance over write performance
- Acceptable data redundancy

### Practical Approach
- Start normalized (3NF) for transactional tables
- Add denormalized views/materialized views for reporting
- Denormalize selectively based on measured query performance issues
- Document denormalization decisions and their rationale
