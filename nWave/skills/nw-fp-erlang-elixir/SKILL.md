---
name: nw-fp-erlang-elixir
agent: nw-functional-software-crafter
description: Erlang/Elixir language-specific patterns, OTP as the effect model, and runtime-enforced immutability
user-invocable: false
disable-model-invocation: true
---

# FP in Erlang/Elixir -- Functional Software Crafter Skill

Cross-references: [fp-principles](../nw-fp-principles/SKILL.md) | [fp-domain-modeling](../nw-fp-domain-modeling/SKILL.md) | [pbt-erlang-elixir](../nw-pbt-erlang-elixir/SKILL.md)

## When to Choose Erlang/Elixir

- Best for: fault-tolerant distributed systems | massive concurrency (millions of lightweight processes) | soft
  real-time (telecom, messaging, payments) | hot code reload without downtime
- Not ideal for: CPU-bound numeric computation | teams needing static types at compile time | small scripts where
  the BEAM's operational surface (release, clustering) is pure overhead

Elixir is shown below (more common entry point); Erlang differs in syntax, not in the model -- both compile to
BEAM bytecode and share OTP, so every pattern below applies to Erlang under a different concrete syntax.

## [STARTER] Quick Setup

```bash
mix new order_service --sup
cd order_service
# Add stream_data to mix.exs deps for property-based testing
mix deps.get && mix test
```

**Test runner**: `mix test`. Add `{:stream_data, "~> 1.0", only: :test}` to `deps`.

## [STARTER] Type System for Domain Modeling

Erlang/Elixir has no compile-time type checker in mainstream use (Dialyzer is opt-in, gradual, and advisory, not
enforced) -- domain shape is a RUNTIME discipline: pattern matching on tagged tuples/structs plus guard clauses,
never an ad-hoc map with an implicit shape.

### Choice Types (Tagged Tuples and Structs)

```elixir
defmodule PaymentMethod do
  @type t ::
          {:credit_card, card_number :: String.t(), expiry :: Date.t()}
          | {:bank_transfer, account_number :: String.t()}
          | :cash
end
```

### Record Types and Domain Wrappers

```elixir
defmodule Customer do
  @enforce_keys [:customer_id, :customer_name, :customer_email]
  defstruct [:customer_id, :customer_name, :customer_email]
end

defmodule EmailAddress do
  @opaque t :: %__MODULE__{value: String.t()}
  defstruct [:value]

  @spec new(String.t()) :: {:ok, t()} | {:error, :invalid_email}
  def new(raw) do
    if String.contains?(raw, "@"),
      do: {:ok, %__MODULE__{value: raw}},
      else: {:error, :invalid_email}
  end
end
```

`@enforce_keys` and `@opaque` push construction through `new/1` -- no direct `%EmailAddress{value: raw}` literal
outside the module can skip validation, because the field is opaque to callers.

### [INTERMEDIATE] Validated Construction with `with`

```elixir
def validate_order(raw) do
  with {:ok, customer} <- Customer.validate(raw.customer),
       {:ok, lines} <- OrderLines.validate(raw.lines) do
    {:ok, %ValidatedOrder{customer: customer, lines: lines}}
  end
end
```

`with` short-circuits on the first non-matching clause, returning that clause's own value -- no manual case-nesting.

## [INTERMEDIATE] Composition Style

### Pipe Operator for Left-to-Right Pipelines

```elixir
def place_order(raw_order) do
  raw_order
  |> validate_order()
  |> price_order()
  |> confirm_order()
end
```

`|>` threads the LEFT expression as the first argument of the RIGHT call -- reads as a pipeline, executes as nested
calls.

### Pattern Matching as Control Flow

```elixir
def process_order({:ok, order}), do: confirm(order)
def process_order({:error, reason}), do: {:error, reason}
```

Multiple function clauses dispatch on the SHAPE of the argument -- no `if`/`case` needed when the shapes are
already distinct tuples.

Standard `with` short-circuits on the first error; accumulate explicitly via `Enum.reduce/3` over a list of
`{:ok, _} | {:error, _}` results when the caller needs every validation failure, not just the first.

## [INTERMEDIATE] Effect Management -- OTP IS the Effect System

Erlang/Elixir has no `IO` type or effect monad: **the process model itself is the effect boundary**. A pure
function computes and returns; a side effect happens by SENDING A MESSAGE to a process (the mailbox), never by
calling a side-effecting function inline in domain logic.

```elixir
# Pure domain logic -- ordinary functions, no process interaction
defmodule OrderDomain do
  def calculate_discount(order) when length(order.lines) > 10, do: 0.1
  def calculate_discount(_order), do: 0.0
end

# Effectful boundary -- a GenServer owns the mutable state and I/O
defmodule OrderServer do
  use GenServer

  def place_order(pid, raw_order), do: GenServer.call(pid, {:place_order, raw_order})

  @impl true
  def handle_call({:place_order, raw_order}, _from, state) do
    case OrderDomain.validate_order(raw_order) do
      {:ok, validated} ->
        priced = OrderDomain.calculate_discount(validated)
        {:reply, {:ok, priced}, Map.put(state, validated.id, priced)}

      {:error, _} = err ->
        {:reply, err, state}
    end
  end
end
```

### [ADVANCED] Supervision Trees as the Failure-Recovery Layer

```elixir
defmodule OrderService.Application do
  use Application

  def start(_type, _args) do
    children = [
      {OrderServer, name: OrderServer},
      {DBConnection.Pool, name: OrderDB}
    ]

    # :one_for_one -- a crashed child restarts alone, siblings keep running
    Supervisor.start_link(children, strategy: :one_for_one)
  end
end
```

"Let it crash": a process that hits an unexpected state terminates instead of defensively guarding every branch;
its supervisor restarts it into a KNOWN-GOOD initial state. This replaces most of what a `try`/`catch` railway
does in other languages -- the recovery unit is the PROCESS, not the call stack.

## [INTERMEDIATE] Testing

**Frameworks**: ExUnit (built-in) | StreamData (property-based testing, `use ExUnitProperties`) | Mox
(behaviour-based mocking for OTP boundaries). See [pbt-erlang-elixir](../nw-pbt-erlang-elixir/SKILL.md) for
detailed PBT patterns.

### Property Test Example

```elixir
use ExUnit.Case
use ExUnitProperties

property "round-trips through serialization" do
  check all(order <- order_generator()) do
    assert {:ok, order} == order |> serialize() |> deserialize()
  end
end

property "validated orders always have a positive total" do
  check all(raw <- raw_order_generator()) do
    case OrderDomain.validate_order(raw) do
      {:error, _} -> :ok
      {:ok, validated} -> assert validated.total > 0
    end
  end
end
```

### Custom Generator

```elixir
def email_generator do
  gen all(
        user <- StreamData.string(:alphanumeric, min_length: 1),
        domain <- StreamData.string(:alphanumeric, min_length: 1)
      ) do
    "#{user}@#{domain}.com"
  end
end
```

## [ADVANCED] Idiomatic Patterns

### Protocols for Data-Directed Polymorphism

```elixir
defprotocol Priceable do
  @spec price(t()) :: Money.t()
end

defimpl Priceable, for: PhysicalOrder do
  def price(order), do: order.subtotal + order.shipping
end

defimpl Priceable, for: DigitalOrder do
  def price(order), do: order.subtotal
end
```

Protocols dispatch on the STRUCT's own type at the call site -- open for new types without touching existing
`defimpl` blocks, the Elixir analogue of a type class.

### Immutability Is Not Optional

Every value in Erlang/Elixir is immutable by construction of the runtime -- there is no mutable-cell escape hatch
comparable to Haskell's `IORef` or Clojure's `atom` reached casually; process state changes ONLY by a `GenServer`
returning a new state from its own callback.

## Maturity and Adoption

- **Dialyzer is advisory, not enforced**: success typing catches real bugs but is unsound by design and opt-in
  per project. A clean Dialyzer run is not a type-safety guarantee.
- **BEAM has real CPU-bound limits**: scheduling favors I/O-bound concurrency; a hot numeric loop belongs in a
  NIF (Rust via `rustler`, C), not pure Elixir.
- **Smaller ecosystem outside web/telecom**: Phoenix/OTP are mature; general-purpose libraries (ML, scientific
  computing) are thinner than JVM or Python.

## Common Pitfalls

1. **Business logic inside `GenServer.handle_call`**: keep the callback thin (pattern-match, delegate); put
   validation/pricing/decision logic in pure modules the callback CALLS, so it is testable without a running
   process.
2. **Blocking calls inside a `GenServer` callback**: a synchronous DB call inside `handle_call` blocks the whole
   process's mailbox; use `Task` for I/O that should not serialize behind other messages.
3. **Catching what should crash**: wrapping ordinary business errors in `try`/`rescue` defeats "let it crash" --
   reserve rescue for genuinely exceptional, unrecoverable-locally conditions; return `{:error, reason}` for
   everything else.
4. **Unbounded process mailboxes**: a producer faster than its consumer grows the mailbox unbounded and OOMs the
   node; back-pressure explicitly (`GenStage`, `Broadway`) for high-throughput pipelines.
