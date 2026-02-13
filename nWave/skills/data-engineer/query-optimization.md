---
name: query-optimization
description: SQL and NoSQL query optimization techniques, indexing strategies, execution plan analysis, JOIN algorithms, cardinality estimation, and database-specific query patterns
---

# Query Optimization

## Cost-Based Optimization

Modern relational databases use cost-based optimizers (CBO) that:
1. Generate multiple execution plan candidates
2. Estimate cost using statistics (row counts, value distributions, index selectivity)
3. Select the plan with lowest estimated I/O, CPU, and memory cost

The optimizer relies on accurate statistics. Stale statistics lead to suboptimal plans.

### Execution Plan Analysis

Always validate optimization with EXPLAIN before and after changes.

```sql
-- PostgreSQL
EXPLAIN ANALYZE SELECT order_id, total FROM orders WHERE customer_id = 12345;

-- MySQL
EXPLAIN FORMAT=JSON SELECT order_id, total FROM orders WHERE customer_id = 12345;

-- SQL Server
SET STATISTICS IO ON;
-- Then examine execution plan in SSMS
```

Key indicators in execution plans:
- **Seq Scan / Table Scan**: Full table scan — often indicates missing index
- **Index Scan / Index Seek**: Using index — usually efficient
- **Hash Join**: Building hash table for join — efficient for large datasets with equality joins
- **Nested Loop**: Row-by-row comparison — efficient for small datasets or when index exists
- **Merge Join**: Synchronized scan of sorted inputs — efficient when sort order is available
- **Sort**: In-memory or disk sort — watch for disk spills on large datasets

## Indexing Strategies

### B-Tree Indexes (Default)
- Support: equality (=), range (<, >, <=, >=, BETWEEN), sorting, prefix pattern matching
- Structure: Balanced tree, O(log n) lookup
- Use for: General-purpose indexing, most query patterns
- All major databases use B-tree as default

### Hash Indexes
- Support: equality (=) only
- Structure: Hash table, O(1) lookup for equality
- Use for: Exact-match lookups on high-cardinality columns
- Limitations: No range queries, no sorting, no pattern matching

### Covering Indexes
- Include all columns needed by a query in the index itself
- Eliminates table access entirely (index-only scan)
- Trade-off: Larger index size, slower writes

```sql
-- Covering index for: SELECT name, email FROM users WHERE status = 'active'
CREATE INDEX idx_users_status_covering ON users(status) INCLUDE (name, email);
```

### PostgreSQL Specialized Indexes
- **GiST**: Geometric data, full-text search, nearest-neighbor
- **GIN**: Array types, full-text search, JSONB queries
- **BRIN**: Large tables with physically correlated data (timestamps). Minimal storage overhead
- **SP-GiST**: Non-balanced structures, point-based geometric queries

### Compound Index Design
Order fields by selectivity and query pattern:
1. Equality conditions first (highest selectivity)
2. Sort columns second
3. Range conditions last

### MongoDB ESR Rule
For compound indexes, follow Equality-Sort-Range ordering:
```javascript
// Query: status = "A", qty > 20, sorted by item
// Optimal index:
db.collection.createIndex({ status: 1, item: 1, qty: 1 })
//                          E(quality)  S(ort)   R(ange)
```

## SQL Optimization Patterns

### Select Only Needed Columns
```sql
-- Bad: SELECT * retrieves unnecessary data
SELECT * FROM orders WHERE customer_id = 12345;

-- Good: Specify columns, enables covering index
SELECT order_id, order_date, total FROM orders WHERE customer_id = 12345;
```

### Use CTEs for Readability (Not Always Performance)
```sql
-- CTEs improve readability but may not optimize like subqueries in all databases
WITH active_customers AS (
    SELECT customer_id, name
    FROM customers
    WHERE status = 'active'
)
SELECT ac.name, COUNT(o.order_id) as order_count
FROM active_customers ac
JOIN orders o ON ac.customer_id = o.customer_id
GROUP BY ac.name;
```

### Window Functions for Analytics
```sql
-- Running total and rank without self-join
SELECT
    order_date,
    total,
    SUM(total) OVER (ORDER BY order_date) as running_total,
    RANK() OVER (PARTITION BY customer_id ORDER BY total DESC) as rank_by_customer
FROM orders;
```

### Pagination
```sql
-- Offset-based (simple but slow for deep pages)
SELECT * FROM products ORDER BY id LIMIT 20 OFFSET 100;

-- Keyset pagination (efficient for deep pages)
SELECT * FROM products WHERE id > 1234 ORDER BY id LIMIT 20;
```

### Parameterized Queries (Security + Performance)
```python
# Python - prevents SQL injection AND enables plan caching
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

## JOIN Algorithm Selection

The optimizer chooses based on data characteristics:

| Algorithm | Best When | Cost |
|-----------|-----------|------|
| Nested Loop | Small outer table, indexed inner table | O(n * m) worst, O(n * log m) with index |
| Hash Join | Large tables, equality joins, no useful indexes | O(n + m) build + probe |
| Merge Join | Both inputs already sorted (index order) | O(n + m) after sort |

## Cardinality Estimation

The optimizer predicts row counts using:
- **Histograms**: Model value distribution in equal-frequency buckets
- **Density vectors**: Estimate selectivity for non-histogram columns
- **Statistics objects**: Maintained by ANALYZE (PostgreSQL) / UPDATE STATISTICS (SQL Server)

When cardinality estimation is wrong (common with correlated columns, skewed data, or multi-table joins), the optimizer picks bad plans. Fix by:
1. Running ANALYZE / UPDATE STATISTICS
2. Creating multi-column statistics
3. Using query hints as last resort

## NoSQL Query Optimization

### MongoDB
- Place `$match` and `$project` early in aggregation pipelines to reduce documents processed
- Use `$lookup` sparingly — it performs left outer joins across collections
- Create compound indexes following the ESR rule
- Use `explain("executionStats")` to validate query performance

### Cassandra
- Always include partition key in queries — scans across partitions are expensive
- Design tables around query patterns (query-first modeling)
- Use SAI (Storage Attached Index) over legacy SASI — 43% throughput improvement
- Avoid ALLOW FILTERING — it forces full cluster scans
- Materialized views provide denormalized query access but add write overhead

### DynamoDB
- Use Query (not Scan) — Query operates on partition key, Scan reads entire table
- Design partition keys for even distribution (avoid hot partitions)
- Use GSIs (Global Secondary Indexes) for alternative access patterns
- Single-table design: store multiple entity types in one table using composite sort keys

### Redis
- Use FT.SEARCH for complex queries (requires RediSearch module)
- Design key naming conventions for efficient SCAN patterns
- Use pipelining for batch operations to reduce round trips

## Anti-Patterns to Detect

- **SELECT ***: Wastes I/O, prevents covering indexes
- **Missing indexes on WHERE/JOIN/ORDER BY columns**: Causes full table scans
- **N+1 queries**: Fetching related data in loops instead of JOINs or batch queries
- **Implicit type conversions**: Prevents index usage (e.g., WHERE varchar_col = 123)
- **Functions on indexed columns**: `WHERE UPPER(name) = 'JOHN'` prevents index use. Use function-based indexes instead
- **Missing pagination**: Returning unbounded result sets
- **Hot partitions** (NoSQL): Low-cardinality partition keys concentrate load on few nodes
- **ALLOW FILTERING** (Cassandra): Forces expensive full-cluster scans
- **Large partition sizes** (Cassandra): Partitions exceeding 100MB degrade performance
