---
name: database-technology-selection
description: Database comparison catalogs, RDBMS vs NoSQL selection criteria, CAP/ACID/BASE theory, OLTP vs OLAP, and technology-specific characteristics
---

# Database Technology Selection

## Selection Decision Framework

Start with these questions:
1. What are the primary access patterns? (point lookups, range queries, graph traversals, full-text search)
2. What consistency guarantees are required? (strong ACID vs eventual consistency)
3. What is the expected scale? (data volume, concurrent users, read/write ratio)
4. What query complexity is needed? (simple key-value, complex joins, aggregations, graph traversals)
5. What latency targets exist? (sub-millisecond caching, millisecond OLTP, second-range analytics)
6. Are there compliance requirements? (GDPR, CCPA, HIPAA, data residency)

## RDBMS Selection Guide

### PostgreSQL
- Strengths: Full ACID, advanced query optimizer (cost-based), rich index types (B-tree, Hash, GiST, GIN, BRIN), JSONB support, strong community
- Best for: Complex queries, mixed OLTP/analytics, geospatial (PostGIS), JSON + relational hybrid
- Scaling: Read replicas, table partitioning, connection pooling (PgBouncer). Sharding via Citus for horizontal scale
- Considerations: Write-heavy workloads may need tuning. Vertical scaling limits at extreme scale

### Oracle
- Strengths: Enterprise features (RAC clustering, Data Guard), Flashback technology, mature optimizer, partitioning
- Best for: Enterprise OLTP, mission-critical systems requiring vendor support, large-scale data warehousing
- Scaling: RAC for horizontal scaling, partitioning for large tables, Active Data Guard for read replicas
- Considerations: Licensing cost, vendor lock-in

### SQL Server
- Strengths: BI integration (SSRS, SSAS, SSIS), Always On availability groups, TDE built-in, columnstore indexes
- Best for: Microsoft ecosystem, BI-heavy workloads, hybrid OLTP/analytics with columnstore
- Scaling: Always On AG for HA, read-scale replicas, partitioning
- Considerations: Windows-centric (Linux support improving), licensing model

### MySQL
- Strengths: Simplicity, wide adoption, InnoDB ACID compliance, good read performance, replication ease
- Best for: Web applications, read-heavy workloads, simple transactional systems
- Scaling: Primary-replica replication, Group Replication, MySQL Router for load balancing
- Considerations: Less sophisticated optimizer than PostgreSQL. Limited window function support in older versions

## NoSQL Selection Guide

### Document Stores (MongoDB, Couchbase)
- Data model: JSON-like documents with flexible schemas
- Best for: Content management, catalogs, user profiles with varying structures, rapid prototyping
- Query: MongoDB Query API with aggregation pipeline, Couchbase N1QL (SQL++)
- Indexing: Compound indexes (follow ESR rule: Equality, Sort, Range), text indexes, geospatial
- Trade-offs: Flexible schema vs. data consistency enforcement. Joins ($lookup) are expensive

### Key-Value Stores (Redis, DynamoDB)
- Data model: Simple key-value pairs. Values can be complex structures
- Best for: Caching, session management, real-time leaderboards, shopping carts
- Query: Redis (GET/SET + FT.SEARCH/FT.AGGREGATE modules), DynamoDB (Query on partition+sort key, Scan)
- Performance: Redis is in-memory (sub-millisecond). DynamoDB provides single-digit ms at any scale
- Trade-offs: Redis limited by available RAM. DynamoDB requires careful partition key design to avoid hot partitions

### Column-Family Stores (Cassandra, HBase)
- Data model: Wide columns grouped into column families, partitioned by partition key
- Best for: Write-heavy workloads, time-series data, IoT, event logging, audit trails
- Query: Cassandra CQL (SQL-like but must include partition key). No joins
- Performance: Linear horizontal scaling. Netflix runs 2500+ clusters. SAI indexing provides 43% throughput gain over SASI
- Trade-offs: Query flexibility limited to partition key patterns. Schema must be designed query-first. Strong consistency can cause up to 95% performance degradation

### Graph Databases (Neo4j, ArangoDB)
- Data model: Nodes and edges with properties. Index-free adjacency
- Best for: Social networks, recommendation engines, fraud detection, knowledge graphs, network topology
- Query: Neo4j Cypher (pattern matching), ArangoDB AQL (multi-model: document + graph)
- Performance: Optimized for relationship traversals. Variable-length path queries far more efficient than recursive SQL CTEs
- Trade-offs: Not suited for aggregation-heavy analytics. Scaling more complex than document/column stores

## ACID vs BASE

### ACID (Relational databases, MongoDB with transactions)
- Atomicity: All-or-nothing transactions
- Consistency: Database moves between valid states
- Isolation: Concurrent transactions don't interfere (isolation levels: READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ, SERIALIZABLE)
- Durability: Committed data survives failures
- Use when: Financial transactions, inventory management, order processing, anywhere data correctness is non-negotiable

### BASE (Cassandra, DynamoDB, eventual consistency systems)
- Basically Available: System guarantees availability
- Soft state: State may change over time without input (due to eventual consistency)
- Eventually consistent: System converges to consistent state given time
- Use when: High availability is more important than immediate consistency (social media feeds, product recommendations, activity streams)

## CAP Theorem Decision Guide

In distributed systems, during a network partition you must choose:
- CP (Consistency + Partition Tolerance): MongoDB, HBase. Blocks writes during partitions to maintain consistency
- AP (Availability + Partition Tolerance): Cassandra, DynamoDB. Accepts writes during partitions, resolves conflicts later
- CA (Consistency + Availability): Single-node RDBMS. Not truly distributed — avoids partition tolerance

The PACELC extension: even without partitions, there is a latency vs consistency trade-off.

## OLTP vs OLAP Selection

### OLTP (Online Transaction Processing)
- Workload: Many short atomic transactions (INSERT, UPDATE, DELETE)
- Schema: Normalized (3NF) to minimize redundancy
- Query: Simple, affecting few rows, millisecond response
- Concurrency: High write concurrency, ACID required
- Databases: PostgreSQL, MySQL, Oracle, SQL Server

### OLAP (Online Analytical Processing)
- Workload: Complex analytical queries with aggregations
- Schema: Denormalized (star/snowflake schema) for query performance
- Query: Complex SELECTs with JOINs, GROUP BY, window functions. Seconds to minutes response
- Concurrency: Read-heavy, fewer concurrent users
- Databases: Snowflake, Amazon Redshift, Google BigQuery, Apache Druid, ClickHouse

### Hybrid HTAP
- Combines OLTP and OLAP in single system
- Examples: TiDB, CockroachDB, SingleStore, SQL Server with columnstore indexes
- Trade-off: Convenience vs. potential performance compromise for both workload types
