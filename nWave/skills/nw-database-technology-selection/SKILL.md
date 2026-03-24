---
name: nw-database-technology-selection
description: "Compares database technologies across RDBMS, NoSQL, CAP/ACID/BASE, and OLTP vs OLAP dimensions. Use when selecting a database, evaluating data storage options, or designing data persistence."
user-invocable: false
disable-model-invocation: true
---

# Database Technology Selection

## Selection Decision Framework

Start with these questions:
1. Primary access patterns? (point lookups, range queries, graph traversals, full-text search)
2. Consistency guarantees? (strong ACID vs eventual consistency)
3. Expected scale? (data volume, concurrent users, read/write ratio)
4. Query complexity? (key-value, complex joins, aggregations, graph traversals)
5. Latency targets? (sub-ms caching, ms OLTP, second-range analytics)
6. Compliance requirements? (GDPR, CCPA, HIPAA, data residency)

## RDBMS Selection Guide

### PostgreSQL
Strengths: Full ACID, advanced cost-based optimizer, rich indexes (B-tree, Hash, GiST, GIN, BRIN), JSONB | Best for: complex queries, mixed OLTP/analytics, geospatial (PostGIS), JSON+relational hybrid | Scaling: read replicas, partitioning, PgBouncer, Citus for horizontal | Watch: write-heavy needs tuning, vertical scaling limits

### Oracle
Strengths: RAC clustering, Data Guard, Flashback, mature optimizer, partitioning | Best for: enterprise OLTP, mission-critical with vendor support, large-scale DW | Scaling: RAC horizontal, partitioning, Active Data Guard read replicas | Watch: licensing cost, vendor lock-in

### SQL Server
Strengths: BI integration (SSRS/SSAS/SSIS), Always On AG, TDE built-in, columnstore indexes | Best for: Microsoft ecosystem, BI-heavy, hybrid OLTP/analytics | Scaling: Always On AG for HA, read-scale replicas, partitioning | Watch: Windows-centric, licensing model

### MySQL
Strengths: Simplicity, wide adoption, InnoDB ACID, good read performance, easy replication | Best for: web apps, read-heavy, simple transactional systems | Scaling: primary-replica, Group Replication, MySQL Router | Watch: less sophisticated optimizer than PostgreSQL, limited window functions in older versions

## NoSQL Selection Guide

### Document Stores (MongoDB, Couchbase)
JSON-like documents, flexible schemas | Best for: CMS, catalogs, user profiles, rapid prototyping | Query: MongoDB aggregation pipeline, Couchbase N1QL | Indexing: compound (ESR rule: Equality-Sort-Range), text, geospatial | Trade-offs: flexible schema vs consistency enforcement, $lookup joins expensive

### Key-Value (Redis, DynamoDB)
Simple key-value pairs, values can be complex structures | Best for: caching, sessions, leaderboards, shopping carts | Redis: in-memory sub-ms, FT.SEARCH/FT.AGGREGATE | DynamoDB: single-digit ms at any scale, Query on partition+sort key | Trade-offs: Redis limited by RAM, DynamoDB requires careful partition key design

### Column-Family (Cassandra, HBase)
Wide columns grouped into column families, partitioned by partition key | Best for: write-heavy, time-series, IoT, event logging, audit trails | Cassandra CQL: SQL-like, must include partition key, no joins | Linear horizontal scaling, SAI indexing 43% throughput gain over SASI | Trade-offs: query flexibility limited to partition key, query-first schema design, strong consistency causes up to 95% perf degradation

### Graph (Neo4j, ArangoDB)
Nodes and edges with properties, index-free adjacency | Best for: social networks, recommendations, fraud detection, knowledge graphs | Neo4j Cypher (pattern matching), ArangoDB AQL (multi-model) | Relationship traversals far more efficient than recursive SQL CTEs | Trade-offs: not suited for aggregation-heavy analytics, scaling more complex

## ACID vs BASE

### ACID (Relational DBs, MongoDB with transactions)
Atomicity: all-or-nothing | Consistency: valid state transitions | Isolation: concurrent transactions don't interfere (levels: READ UNCOMMITTED/COMMITTED, REPEATABLE READ, SERIALIZABLE) | Durability: committed data survives failures | Use when: financial transactions, inventory, order processing, data correctness non-negotiable

### BASE (Cassandra, DynamoDB, eventual consistency)
Basically Available | Soft state (may change without input) | Eventually consistent | Use when: availability > immediate consistency (social feeds, recommendations, activity streams)

## CAP Theorem Decision Guide

During network partition, choose:
- **CP** (MongoDB, HBase): Block writes to maintain consistency
- **AP** (Cassandra, DynamoDB): Accept writes, resolve conflicts later
- **CA** (Single-node RDBMS): Not truly distributed, avoids partition tolerance

PACELC extension: even without partitions, latency vs consistency trade-off exists.

## OLTP vs OLAP

### OLTP
Many short atomic transactions (INSERT/UPDATE/DELETE) | Normalized 3NF | Simple queries, few rows, ms response | High write concurrency, ACID required | DBs: PostgreSQL, MySQL, Oracle, SQL Server

### OLAP
Complex analytical queries with aggregations | Denormalized star/snowflake | Complex SELECTs with JOINs, GROUP BY, window functions, seconds-minutes response | Read-heavy, fewer concurrent users | DBs: Snowflake, Redshift, BigQuery, Druid, ClickHouse

### Hybrid HTAP
Combines OLTP+OLAP in single system | Examples: TiDB, CockroachDB, SingleStore, SQL Server with columnstore | Trade-off: convenience vs potential performance compromise for both workloads
