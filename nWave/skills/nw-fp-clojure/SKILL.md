---
name: nw-fp-clojure
agent: nw-functional-software-crafter
description: Clojure language-specific patterns, data-first modeling, REPL-driven development, and spec
user-invocable: false
disable-model-invocation: true
---

# FP in Clojure -- Functional Software Crafter Skill

Cross-references: [fp-principles](../nw-fp-principles/SKILL.md) | [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md)

## When to Choose Clojure

- Best for: data-centric domains | REPL-driven exploration | rapid prototyping | frequently evolving data shapes
- Not ideal for: teams wanting compile-time type safety | Android | teams unfamiliar with Lisp syntax

## [STARTER] Quick Setup

```bash
# Install Clojure CLI
brew install clojure/tools/clojure  # macOS
# Create project
mkdir -p order-service/src/order_service order-service/test/order_service
# Run REPL: clj | Run tests: clj -X:test
```

**Namespace caveat**: Clojure namespaces use `-` but filenames use `_` (JVM requirement). `order-service.core` lives in `order_service/core.clj`.

## [STARTER] Domain Modeling with Spec

Clojure is dynamically typed. Domain modeling uses maps with qualified keywords, validated at runtime.

```clojure
(require '[clojure.spec.alpha :as s])

;; Domain wrappers as specs
(s/def ::order-id pos-int?)
(s/def ::email (s/and string? #(clojure.string/includes? % "@")))
(s/def ::customer-name (s/and string? #(> (count %) 0)))

;; Record types as spec'd maps
(s/def ::customer (s/keys :req [::customer-name ::email] :opt [::phone]))

;; Choice types as spec alternatives
(s/def ::payment-method
  (s/or :credit-card (s/keys :req [::card-number ::expiry-date])
        :bank-transfer (s/keys :req [::account-number])
        :cash #{:cash}))
```

### [STARTER] Validated Construction

```clojure
(defn make-email [raw-email]
  (if (s/valid? ::email raw-email)
    {:ok raw-email}
    {:error (str "Invalid email: " raw-email)}))
```

### [INTERMEDIATE] Auto-Generated Test Data from Specs

```clojure
(require '[clojure.spec.gen.alpha :as gen]
         '[clojure.spec.test.alpha :as stest])

(gen/sample (s/gen ::customer) 5)  ;; random valid customers

;; Auto-test functions against their specs
(s/fdef validate-order
  :args (s/cat :raw-order ::raw-order)
  :ret (s/or :ok ::validated-order :error ::validation-error))
(stest/check `validate-order)
```

Define specs, get generators and function tests for free.

## [INTERMEDIATE] Composition Style

### Threading Macros

```clojure
;; Thread-first (data through first arg) / Thread-last (for collections)
(-> raw-order validate-order price-order confirm-order)
(->> orders (filter active?) (map :customer-name) (sort))

;; comp composes right-to-left; partial for partial application
(def process-order (comp confirm-order price-order validate-order))
```

### Error-Track Pipeline (Convention-Based)

```clojure
(defn bind-result [result f]
  (if (:ok result) (f (:ok result)) result))

(defn place-order [raw-order]
  (-> {:ok raw-order}
      (bind-result validate-order)
      (bind-result price-order)
      (bind-result confirm-order)))
```

No stdlib Result/Either -- by convention using `{:ok v}` / `{:error r}` maps.

## [INTERMEDIATE] Effect Management

Side effects managed by convention and architecture, not the type system.

### Pure Core / Imperative Shell

```clojure
;; Pure domain logic (no I/O, no state)
(defn calculate-discount [order]
  (if (> (count (:lines order)) 10) {:rate 0.1} {:rate 0.0}))

;; Imperative shell (I/O at edges)
(defn place-order-handler! [deps raw-order]
  (let [result (-> raw-order
                   validate-order
                   (bind-result (partial price-order (:get-price deps)))
                   (bind-result confirm-order))]
    (when (:ok result)
      ((:save-order! deps) (:ok result)))
    result))
```

### [ADVANCED] Hexagonal Architecture with Functions

```clojure
;; Functions as dependencies (idiomatic Clojure)
(defn make-place-order-handler [find-order-fn save-order-fn!]
  (fn [raw-order]
    (let [result (validate-and-price raw-order)]
      (when (:ok result) (save-order-fn! (:ok result)))
      result)))

;; Composition root
(def handler
  (make-place-order-handler
    (partial find-order-in-db datasource)
    (partial save-order-in-db! datasource)))
```

For lifecycle management, use Component, Integrant, or Mount:

```clojure
(require '[integrant.core :as ig])

(defmethod ig/init-key ::order-repo [_ {:keys [datasource]}]
  (->PostgresOrderRepo datasource))
```

## [INTERMEDIATE] Testing

**Frameworks**: clojure.test (built-in) | test.check (PBT) | Kaocha (test runner).

### Property Test with test.check

```clojure
(require '[clojure.test.check.clojure-test :refer [defspec]]
         '[clojure.test.check.generators :as gen]
         '[clojure.test.check.properties :as prop])

(defspec serialization-round-trips 100
  (prop/for-all [order (s/gen ::order)]
    (= order (deserialize (serialize order)))))
```

### Custom Generator

```clojure
(def gen-valid-email
  (gen/fmap (fn [[user domain]] (str user "@" domain ".com"))
    (gen/tuple
      (gen/such-that not-empty (gen/string-alphanumeric))
      (gen/such-that not-empty (gen/string-alphanumeric)))))
```

## [ADVANCED] Idiomatic Patterns

### Data-First Domain Modeling

```clojure
(def order
  {::order-id 42
   ::customer {::customer-name "Alice" ::email "alice@example.com"}
   ::lines [{::product-code "W-1234" ::quantity 10 ::price 25.0}]
   ::status :validated})
```

"Data is better than types." Domain models are maps. Validation happens at boundaries.

### Multimethods for State Machines

```clojure
(defmulti handle-command (fn [state _command] (:status state)))

(defmethod handle-command :empty [_state {:keys [item]}]
  {:status :active :lines [item]})

(defmethod handle-command :active [state {:keys [action] :as command}]
  (case action
    :add-item (update state :lines conj (:item command))
    :pay (assoc state :status :paid)
    state))

(defmethod handle-command :paid [state _command]
  state)
```

## Maturity and Adoption

- **Dynamic typing trade-offs**: No compile-time type checking; typos in keywords are silent until runtime. Spec instrumentation helps but is opt-in.
- **Spec limitations**: Powerful for data validation but lacks expressiveness of static type systems for complex invariants. Spec 2 in development for years.
- **Discipline needed for test coverage**: Without compiler catching type errors, comprehensive tests are essential.
- **Smaller ecosystem**: Fewer libraries than Java/Kotlin. Good JVM interop compensates but Java interop code is verbose.

## Common Pitfalls

1. **Silent nil propagation**: Missing key returns `nil`, propagates silently. Use `some->` and explicit nil checks at boundaries.
2. **Learning curve for non-Lispers**: Parenthesis-heavy syntax is a barrier. Invest in Paredit/Parinfer and REPL workflow first.
3. **Spec verbosity**: Large spec definitions become unwieldy. Extract into focused namespaces and use `s/merge`.
4. **Convention-based error handling**: Without stdlib Result, teams use inconsistent patterns. Standardize on `{:ok v}` / `{:error r}` early.
