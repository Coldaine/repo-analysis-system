````markdown
# State Model and Reducers (LangGraph v1.0)

**Status**: Canonical
**Last Updated**: November 23, 2025

This document describes the canonical state model for LangGraph v1.0 and how to implement reducers to merge concurrent updates safely.

## Overview

LangGraph v1.0 uses an explicit, schema-defined `State` that is passed through nodes. The recommended pattern is to use `TypedDict` to define the state's shape and `Annotated[...]` to attach reducer functions to channels that can be updated by multiple nodes in parallel.

Reducers are functions with the signature:

```
def reducer(current_value, update_value) -> new_value:
    ...
```

Reducers are applied to the results emitted by nodes when the graph commits state transitions. This allows the runtime to safely combine multiple independent updates in one atomic step.

## Why `TypedDict` + `Annotated`?

- `TypedDict` is runtime-lightweight and provides good static typing support.
- `Annotated` allows you to attach reducer functions to state channels in a way the runtime recognizes and uses when merging parallel updates.

## Common Reducers

- `add_messages`: Append or update messages in a conversation channel. Merges by message ID where available.
- `operator.add` (or `list concatenation`): Useful for simple list accumulation, but dangerous if used incorrectly (see the duplication section).

## The Exponential Duplication Trap — DO vs DON’T

Problem: When a node reads the current state, appends to a list, and returns the entire list, a reducer that concatenates lists will *double-count* the prior data if multiple parallel nodes do this. This leads to exponential duplication.

### BAD: Returning a full snapshot

```python
from typing import TypedDict, List
from operator import add

class State(TypedDict):
    items: List[str]  # Annotated with operator.add in a real graph

def node(state: State):
    # reads the current list and returns a new full list
    new_items = state['items'] + ['X']
    return {'items': new_items}

# Reducer: operator.add -> state.items += update
```

If two nodes run in parallel and both read the same initial [A] and return [A, X], the reducer does:

new_state = [A] + [A, X] + [A, X] => exponential duplication

### GOOD: Return a delta (only the added values)

```python
def node(state: State):
    # return only the delta
    return {'items': ['X']}

# Reducer: operator.add -> state.items += ['X']
```

This ensures the final state becomes [A, X, X] if both nodes add the same `X` (and you can de-duplicate by ID if needed) but avoids accidental duplication of the entire prior list.

## add_messages reducer example

For conversations, prefer `add_messages` which understands message IDs and merges safely.

```python
from typing import TypedDict, Annotated, List
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

def add_user_message(state: ChatState, msg: BaseMessage):
    return {'messages': [msg]}  # delta only
```

`add_messages` will append new messages and update existing messages if message IDs match, preventing accidental duplication and keeping message integrity.

## Best Practices

- Always prefer returning deltas for reducer-managed channels.
- Prefer `TypedDict` + `Annotated` for state schema; keep the `GraphState` shape explicit and small.
- Use `add_messages` for conversation channels; implement custom reducers for other specialized channels (e.g., `merge_documents` or `aggregate_scores`).
- Add unit tests for your reducer behavior to ensure merge semantics are stable under concurrency.

## Testing reducers

Write unit tests proving: idempotent updates, order-insensitive merges for parallel updates, and the absence of exponential duplication under typical concurrent load.

Example test skeleton (pytest-style):

```python
def test_add_messages_reducer():
    cur = [msg_a]
    upd = [msg_b]
    new = add_messages(cur, upd)
    assert new == [msg_a, msg_b]
```

This doc aims to be a concise, actionable reference for implementing safe state channels and reducers in your LangGraph graphs.
````
