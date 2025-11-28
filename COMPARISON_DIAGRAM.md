# Visual Comparison: Pessimistic vs Optimistic Locking

## Pessimistic Locking Flow

```
Transaction A                    Transaction B
     |                                |
     | SELECT ... FOR UPDATE          |
     |----> LOCK ACQUIRED             |
     |                                |
     | Read sender balance            |
     | Read receiver balance          | SELECT ... FOR UPDATE
     |                                |----> BLOCKED (waiting for lock)
     | Validate                       |      ⏳ WAITING...
     |                                |      ⏳ WAITING...
     | Update sender balance          |      ⏳ WAITING...
     | Update receiver balance        |      ⏳ WAITING...
     |                                |      ⏳ WAITING...
     | COMMIT                         |
     |----> LOCK RELEASED             |
     |                                |----> LOCK ACQUIRED ✅
     ✅ SUCCESS                       |
                                      | Read sender balance
                                      | Read receiver balance
                                      | Validate
                                      | Update sender balance
                                      | Update receiver balance
                                      | COMMIT
                                      |----> LOCK RELEASED
                                      ✅ SUCCESS

Result: Both transactions succeed, but B waits for A
```

## Optimistic Locking Flow

```
Transaction A                    Transaction B
     |                                |
     | SELECT (no lock)               |
     | Read sender (version=1)        |
     | Read receiver (version=1)      | SELECT (no lock)
     |                                | Read sender (version=1)
     | Validate                       | Read receiver (version=1)
     |                                |
     | UPDATE WHERE version=1         | Validate
     |----> version=2 ✅              |
     |                                | UPDATE WHERE version=1
     | UPDATE WHERE version=1         |----> ❌ FAILED (version is now 2!)
     |----> version=2 ✅              |
     |                                | ROLLBACK
     | COMMIT                         |----> ConcurrencyError raised
     ✅ SUCCESS                       ❌ MUST RETRY

Result: A succeeds, B fails and must retry
```

## Retry Flow (Optimistic Locking)

```
Transaction B (Retry #1)
     |
     | SELECT (no lock)
     | Read sender (version=2)  ← Updated version!
     | Read receiver (version=2)
     |
     | Validate
     |
     | UPDATE WHERE version=2
     |----> version=3 ✅
     |
     | UPDATE WHERE version=2
     |----> version=3 ✅
     |
     | COMMIT
     ✅ SUCCESS on retry!
```

---

## Side-by-Side Comparison

### Scenario 1: Low Contention (1% conflict rate)

#### Pessimistic Locking
```
Time: 0ms  ─────────────────────────────────────────────────────
           Transaction 1: [LOCK][Process][COMMIT] ✅ 50ms
           Transaction 2:       [LOCK][Process][COMMIT] ✅ 50ms
           Transaction 3:             [LOCK][Process][COMMIT] ✅ 50ms
           
Total Time: 150ms
Throughput: 20 TPS
Conflicts: 0
```

#### Optimistic Locking
```
Time: 0ms  ─────────────────────────────────────────────────────
           Transaction 1: [Read][Process][COMMIT] ✅ 30ms
           Transaction 2: [Read][Process][COMMIT] ✅ 30ms
           Transaction 3: [Read][Process][COMMIT] ✅ 30ms
           
Total Time: 90ms (40% faster!)
Throughput: 33 TPS
Conflicts: 0-1 (rare, quick retry)
```

**Winner: Optimistic** ✅ - No blocking overhead

---

### Scenario 2: High Contention (20% conflict rate)

#### Pessimistic Locking
```
Time: 0ms  ─────────────────────────────────────────────────────
           Transaction 1: [LOCK][Process][COMMIT] ✅ 50ms
           Transaction 2:       [WAIT][LOCK][Process][COMMIT] ✅ 100ms
           Transaction 3:             [WAIT][LOCK][Process][COMMIT] ✅ 150ms
           
Total Time: 300ms
Throughput: 10 TPS
Conflicts: 0 (blocking prevents conflicts)
```

#### Optimistic Locking
```
Time: 0ms  ─────────────────────────────────────────────────────
           Transaction 1: [Read][Process][COMMIT] ✅ 30ms
           Transaction 2: [Read][Process][FAIL]❌[Retry][COMMIT] ✅ 90ms
           Transaction 3: [Read][Process][FAIL]❌[Retry][FAIL]❌[Retry][COMMIT] ✅ 150ms
           
Total Time: 270ms
Throughput: 11 TPS
Conflicts: 5 (many retries, wasted work)
```

**Winner: Pessimistic** ✅ - Conflicts cause too many retries

---

## Real-World Example: E-Commerce Flash Sale

### Pessimistic Locking (Recommended)
```
Popular Product (1000 buyers competing)
─────────────────────────────────────────
Buyer 1: [LOCK]─────[BUY]─────[COMMIT] ✅
Buyer 2:       [WAIT]─────[LOCK]─────[BUY]─────[COMMIT] ✅
Buyer 3:                   [WAIT]─────[LOCK]─────[BUY]─────[COMMIT] ✅
...

✅ All buyers eventually succeed (if stock available)
✅ Predictable wait times
✅ No wasted work
```

### Optimistic Locking (Not Recommended)
```
Popular Product (1000 buyers competing)
─────────────────────────────────────────
Buyer 1: [READ]─────[BUY]─────[COMMIT] ✅
Buyer 2: [READ]─────[BUY]─────[FAIL]❌[RETRY]─────[FAIL]❌[RETRY]─────[COMMIT] ✅
Buyer 3: [READ]─────[BUY]─────[FAIL]❌[RETRY]─────[FAIL]❌[RETRY]─────[FAIL]❌[RETRY]─────[COMMIT] ✅
...

❌ Many retries (frustrating for users)
❌ Wasted database work
❌ Unpredictable response times
```

---

## Real-World Example: Peer-to-Peer Transfers

### Pessimistic Locking (Works but slower)
```
Random Users (low collision probability)
─────────────────────────────────────────
Alice→Bob:   [LOCK]─────[TRANSFER]─────[COMMIT] ✅ 50ms
Carol→Dave:  [LOCK]─────[TRANSFER]─────[COMMIT] ✅ 50ms
Eve→Frank:   [LOCK]─────[TRANSFER]─────[COMMIT] ✅ 50ms

✅ Works fine
⚠️  Lock overhead unnecessary (no conflicts)
```

### Optimistic Locking (Recommended)
```
Random Users (low collision probability)
─────────────────────────────────────────
Alice→Bob:   [READ]─────[TRANSFER]─────[COMMIT] ✅ 30ms
Carol→Dave:  [READ]─────[TRANSFER]─────[COMMIT] ✅ 30ms
Eve→Frank:   [READ]─────[TRANSFER]─────[COMMIT] ✅ 30ms

✅ 40% faster (no lock overhead)
✅ Higher throughput
✅ Conflicts extremely rare
```

---

## Performance Metrics Summary

| Metric | Pessimistic (Low Contention) | Optimistic (Low Contention) |
|--------|------------------------------|----------------------------|
| Avg Latency | 50ms | **30ms** ✅ |
| P99 Latency | 100ms | **60ms** ✅ |
| Throughput | 1000 TPS | **1500 TPS** ✅ |
| Conflicts | 0 | 10 (retried) |
| **Winner** | | **Optimistic** |

| Metric | Pessimistic (High Contention) | Optimistic (High Contention) |
|--------|-------------------------------|----------------------------|
| Avg Latency | **60ms** ✅ | 150ms |
| P99 Latency | **120ms** ✅ | 500ms |
| Throughput | **800 TPS** ✅ | 400 TPS |
| Conflicts | 0 | 100 (many retries) |
| **Winner** | **Pessimistic** | |

---

## Decision Tree

```
                    Start
                      |
                      v
            Is conflict rate > 10%?
                   /     \
                 Yes      No
                  |        |
                  v        v
            PESSIMISTIC  Is user waiting?
                           /     \
                         Yes      No
                          |        |
                          v        v
                    PESSIMISTIC  OPTIMISTIC
```

---

## Key Takeaways

### Pessimistic Locking
- 🔒 **Locks first, asks questions later**
- ⏳ **Blocks other transactions**
- ✅ **Zero conflicts**
- 🎯 **Best for high contention**

### Optimistic Locking
- 🚀 **Fast and furious**
- 🔄 **Retry on conflict**
- ⚡ **No blocking**
- 🎯 **Best for low contention**

### The Golden Rule
> "If transactions fight over the same data often, lock it.  
> If they rarely collide, let them race and retry on conflict."
