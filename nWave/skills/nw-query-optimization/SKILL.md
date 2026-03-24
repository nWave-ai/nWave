---
name: nw-query-optimization
description: "SQL and NoSQL query optimization with indexing strategies, execution plan analysis, and JOIN algorithms. Load when tuning slow queries, analyzing execution plans, or designing database indexing strategies."
user-invocable: false
disable-model-invocation: true
---

# Query Optimization

## Cost-Based Optimization

Modern relational DBs use cost-based optimizers (CBO): generate plan candidates -> estimate cost via statistics (row counts, distributions, selectivity) -> select lowest I/O/CPU/memory plan. Stale statistics lead to suboptimal plans.

### Execution Plan Analysis

Validate optimization with EXPLAIN before and after changes.

```sql
-- PostgreSQL (add ANALYZE for actual runtime stats)
EXPLAIN ANALYZE SELECT order_id, total FROM orders WHERE customer_id = 12345;
-- MySQL: EXPLAIN FORMAT=JSON ... | SQL Server: SET STATISTICS IO ON
```

Key indicators: **Seq Scan/Table Scan** = missing index | **Index Scan/Seek** = efficient | **Hash Join** = large equality joins | **Nested Loop** = small/indexed inner | **Merge Join** = pre-sorted inputs | **Sort** = watch disk spills

## Indexing Strategies

### B-Tree (Default)
Supports: equality, range, sorting, prefix matching | O(log n) lookup | General-purpose, all major DBs default

### Hash
Equality only | O(1) lookup | High-cardinality exact-match | No range/sorting/pattern support

### Covering Indexes
Include all query columns in index -> eliminates table access (index-only scan) | Trade-off: larger index, slower writes

```sql
-- Covering index for: SELECT name, email FROM users WHERE status = 'active'
CREATE INDEX idx_users_status_covering ON users(status) INCLUDE (name, email);
```

### PostgreSQL Specialized
- **GiST**: Geometric data, full-text search, nearest-neighbor
- **GIN**: Arrays, full-text search, JSONB queries
- **BRIN**: Large tables with physically correlated data (timestamps), minimal storage
- **SP-GiST**: Non-balanced structures, point-based geometric queries

### Compound Index Design
Order by: 1. Equality conditions first (highest selectivity) | 2. Sort columns second | 3. Range conditions last

### MongoDB ESR Rule
Equality-Sort-Range ordering for compound indexes:
```javascript
// Query: status = "A", qty > 20, sorted by item
// Optimal index:
db.collection.createIndex({ status: 1, item: 1, qty: 1 })
//                          E(quality)  S(ort)   R(ange)
```

## SQL Optimization Patterns

### Select Only Needed Columns
```sql
-- Bad: SELECT * retrieves unnecessary data, prevents covering indexes
SELECT * FROM orders WHERE customer_id = 12345;

-- Good: Specify columns, enables covering index
SELECT order_id, order_date, total FROM orders WHERE customer_id = 12345;
```

### Other Key Patterns
- **CTEs**: Improve readability but not always performance -- PostgreSQL may materialize CTEs (pre-v12), MySQL inlines them
- **Window functions**: Use `SUM() OVER`, `RANK() OVER (PARTITION BY ...)` for analytics without self-joins
- **Pagination**: Prefer keyset (`WHERE id > last_seen ORDER BY id LIMIT N`) over OFFSET for deep pages
- **Parameterized queries**: Prevent SQL injection AND enable plan caching (`cursor.execute("... WHERE id = %s", (id,))`)

## JOIN Algorithm Selection

| Algorithm | Best When | Cost |
|-----------|-----------|------|
| Nested Loop | Small outer table, indexed inner table | O(n * m) worst, O(n * log m) with index |
| Hash Join | Large tables, equality joins, no useful indexes | O(n + m) build + probe |
| Merge Join | Both inputs already sorted (index order) | O(n + m) after sort |

## Cardinality Estimation

Optimizer predicts row counts using: **Histograms** (value distribution) | **Density vectors** (non-histogram columns) | **Statistics objects** via ANALYZE (PostgreSQL) / UPDATE STATISTICS (SQL Server)

When estimation is wrong (correlated columns, skewed data, multi-table joins): 1. Run ANALYZE/UPDATE STATISTICS | 2. Create multi-column statistics | 3. Query hints as last resort

## NoSQL Query Optimization

### MongoDB
Place `$match`/`$project` early in pipelines | Use `$lookup` sparingly (left outer joins) | Compound indexes following ESR | Validate with `explain("executionStats")`

### Cassandra
Always include partition key | Design tables around query patterns (query-first) | Use SAI over SASI (43% throughput gain) | Avoid ALLOW FILTERING (full cluster scan) | Materialized views add write overhead

### DynamoDB
Use Query not Scan | Design partition keys for even distribution | GSIs for alternative access patterns | Single-table design with composite sort keys

### Redis
FT.SEARCH for complex queries (RediSearch module) | Design key naming for efficient SCAN | Use pipelining for batch ops

## Anti-Patterns to Detect

- **SELECT ***: Wastes I/O, prevents covering indexes
- **Missing indexes** on WHERE/JOIN/ORDER BY columns: full table scans
- **N+1 queries**: Fetch in loops instead of JOINs/batch
- **Implicit type conversions**: Prevents index use (WHERE varchar_col = 123)
- **Functions on indexed columns**: `WHERE UPPER(name) = 'JOHN'` blocks index; use function-based indexes
- **Missing pagination**: Unbounded result sets
- **Hot partitions** (NoSQL): Low-cardinality partition keys concentrate load
- **ALLOW FILTERING** (Cassandra): Expensive full-cluster scans
- **Large partitions** (Cassandra): >100MB degrades performance
