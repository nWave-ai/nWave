---
name: nw-pbt-erlang-elixir
agent: nw-functional-software-crafter
description: Erlang/Elixir property-based testing with PropEr, PropCheck, and StreamData frameworks
disable-model-invocation: true
---

# PBT Erlang/Elixir -- PropEr, PropCheck, StreamData

## Framework Selection

| Framework | Language | Stateful | Parallel | Choose When |
|-----------|----------|----------|----------|-------------|
| PropEr | Erlang | Yes | Yes (linearizability) | Erlang projects needing full stateful/parallel testing |
| PropCheck | Elixir | Yes (via PropEr) | Yes (via PropEr) | Elixir projects needing stateful/parallel testing |
| StreamData | Elixir | No | No | Elixir projects needing only stateless PBT |

PropCheck wraps PropEr with Elixir syntax. StreamData is pure Elixir but lacks stateful testing.

## Quick Start

```erlang
%% PropEr (Erlang)
-include_lib("proper/include/proper.hrl").

prop_sort_preserves_length() ->
    ?FORALL(List, list(integer()),
        length(lists:sort(List)) =:= length(List)).

%% Run: proper:quickcheck(my_module:prop_sort_preserves_length()).
```

### Syntax Differences

| Concept | PropEr (Erlang) | PropCheck (Elixir) | StreamData (Elixir) |
|---------|-----------------|--------------------|--------------------|
| Import | `-include_lib("proper/include/proper.hrl").` | `use PropCheck` | `use ExUnitProperties` |
| Property | `?FORALL(X, gen(), body)` | `forall x <- gen() do body end` | `check all x <- gen() do assert body end` |
| Integer | `integer()` | `integer()` | `integer()` |
| List | `list(integer())` | `list(integer())` | `list_of(integer())` |
| Run | `proper:quickcheck(prop())` | `mix test` | `mix test` |

## Generator Cheat Sheet (PropEr)

### Primitives
```erlang
integer()                  % any integer
integer(0, 100)            % bounded
float()
binary()                   % binary data
boolean()
atom()
```

### Collections
```erlang
list(integer())            % list of integers
non_empty(list(integer())) % non-empty list
vector(5, integer())       % fixed-length list
{integer(), binary()}      % tuple (direct syntax)
```

### Combinators
```erlang
oneof([integer(), binary()])      % union
elements([a, b, c])               % pick from list
frequency([{80, integer()}, {20, atom()}])  % weighted

%% ?LET (map/transform)
even() ->
    ?LET(N, integer(), N * 2).

%% ?SUCHTHAT (filter -- use sparingly)
non_empty_list() ->
    ?SUCHTHAT(L, list(integer()), L =/= []).

%% Nested ?LET (dependent generation)
list_and_element() ->
    ?LET(List, non_empty(list(integer())),
        ?LET(Elem, elements(List),
            {List, Elem})).
```

### Recursive
```erlang
tree(Type) ->
    ?SIZED(Size, tree(Size, Type)).
tree(0, Type) -> {leaf, Type};
tree(Size, Type) ->
    frequency([
        {1, {leaf, Type}},
        {5, ?LAZY({node, Type, tree(Size div 2, Type), tree(Size div 2, Type)})}
    ]).
```

### Shrinking
```erlang
year() ->
    ?SHRINK(integer(0, 9999), [integer(1970, 2000)]).

date() ->
    ?LETSHRINK([Y, M, D],
               [integer(1, 9999), integer(1, 12), integer(1, 31)],
               {Y, M, D}).
```

## Stateful Testing (proper_statem)

```erlang
-behaviour(proper_statem).

initial_state() -> #{items => #{}}.

command(#{items := Items}) ->
    oneof([
        {call, ?MODULE, put, [key(), value()]},
        {call, ?MODULE, get, [elements(maps:keys(Items))]}
            || maps:size(Items) > 0
    ]).

precondition(#{items := Items}, {call, _, get, [Key]}) ->
    maps:is_key(Key, Items);
precondition(_, _) -> true.

postcondition(#{items := Items}, {call, _, get, [Key]}, Result) ->
    Result =:= maps:get(Key, Items);
postcondition(_, _, _) -> true.

next_state(State = #{items := Items}, _Var, {call, _, put, [Key, Val]}) ->
    State#{items := Items#{Key => Val}};
next_state(State, _, _) -> State.

prop_store() ->
    ?FORALL(Cmds, commands(?MODULE),
        begin
            {History, State, Result} = run_commands(?MODULE, Cmds),
            cleanup(),
            Result =:= ok
        end).
```

StreamData: No stateful testing. PropCheck: Same proper_statem callbacks with Elixir syntax.

### Parallel Testing (Linearizability)

```erlang
prop_store_parallel() ->
    ?FORALL(Cmds, parallel_commands(?MODULE),
        begin
            {Sequential, Parallel, Result} = run_parallel_commands(?MODULE, Cmds),
            cleanup(),
            Result =:= ok
        end).
```

Swap `commands` for `parallel_commands`, `run_commands` for `run_parallel_commands`. Framework generates sequential prefix + parallel branches and checks all linearizations.

## Test Runner Integration

```erlang
%% PropEr: {deps, [{proper, "1.4.0"}]}. Run: rebar3 proper
%% PropCheck: {:propcheck, "~> 1.4", only: :test}. Run: mix test
%% StreamData: {:stream_data, "~> 1.0", only: :test}. Run: mix test
```

## Unique Features

- **proper_fsm**: Finite state machine testing module (distinct from generic state machines)
- **PULSE integration**: Controlled scheduling for parallel test race detection
- **Symbolic references**: First-class support with two-phase (abstract + concrete) execution
- **collect/aggregate**: Built-in distribution analysis for generator quality verification
- **Linearizability checking**: One of the most mature implementations in any PBT framework
