# State Management and Reducers in LangGraph

Effective state management is crucial for building robust and scalable applications with LangGraph. This guide covers the recommended patterns for defining state and implementing reducer functions to ensure your graph is maintainable, predictable, and efficient.

## The State Model: `TypedDict` and Reducers

In LangGraph, the state is a central object that flows through the nodes of your graph. Each node can read from the state and return updates to it. LangGraph then merges these updates into the main state before passing it to the next node.

### Why Use `TypedDict` for State?

While you can use any Python object for state (like dataclasses or Pydantic models), **`TypedDict` is the recommended approach** for several key reasons:

1.  **Explicit Updates**: `TypedDict` encourages a pattern of returning only the *changes* (deltas) to the state, not the entire state object. This makes the data flow clearer and prevents accidental overwrites.
2.  **Flexibility**: It's easy to add new keys to a `TypedDict` without breaking existing nodes, making the graph more extensible.
3.  **Performance**: Returning small deltas is more efficient than passing around a large, monolithic state object, especially in complex graphs.
4.  **Reducer Semantics**: `TypedDict` works seamlessly with LangGraph's reducer functions, which are designed to handle state updates in a controlled and predictable way.

### Defining State with `TypedDict`

Here’s how to define a simple state object using `TypedDict` and `typing.Annotated` to specify a reducer.

```python
from typing import TypedDict, Annotated, List
from langgraph.graph.message import add_messages

# The 'messages' key is special. It's managed by a built-in reducer, `add_messages`,
# which appends new messages to the existing list.
class State(TypedDict):
    """
    The central state of our application.
    """
    messages: Annotated[list, add_messages]
    # Other keys for your application state
    repository_url: str
    analysis: str
    files_to_review: List[str]
```

In this example:
- `messages: Annotated[list, add_messages]` tells LangGraph that the `messages` key should be updated by appending new messages. This is the standard way to manage conversational history.
- Other keys like `repository_url` and `analysis` are updated by simple replacement (the last value written wins).

## Reducers: The "Return Deltas" Pattern

A **reducer** is a function that defines how to merge a new value with an existing value in the state. The `add_messages` function is a built-in reducer. You can also define your own.

The most important principle for writing nodes is to **return only the state you want to change**. This is the "return deltas" pattern.

### Do: Return Only What Changed

When a node executes, it should return a dictionary containing only the keys of the state it needs to update.

**✅ Correct Example: Returning a Delta**

```python
def analyze_repository(state: State) -> dict:
    """
    A node that analyzes a repository and returns an update to the 'analysis' key.
    """
    # Business logic to analyze the repository...
    analysis_result = "This repository has high complexity."

    # Return ONLY the key that needs to be updated.
    return {"analysis": analysis_result}

# LangGraph will merge this dictionary into the main state.
# If the state was {"messages": [...], "analysis": ""},
# it will become {"messages": [...], "analysis": "This repository has high complexity."}.
```

### Don't: Return the Full State Object

Returning the entire state object from a node is an anti-pattern. It is inefficient and can lead to race conditions in graphs with parallel execution paths, where nodes might accidentally overwrite each other's updates.

**❌ Incorrect Example: Returning the Full State**

```python
def analyze_repository_bad(state: State) -> dict:
    """
    An incorrect implementation that modifies and returns the whole state.
    """
    # Business logic...
    state["analysis"] = "This repository has high complexity."

    # ANTI-PATTERN: Don't return the entire state object!
    return state
```

This is dangerous because if another node running in parallel modifies a different part of the state (e.g., `files_to_review`), this node's full return could overwrite that change.

### Using `add_messages` for Conversational History

The `add_messages` reducer is designed for managing conversational history. When you return a `messages` key, `add_messages` appends the new message(s) to the existing list.

**✅ Correct Usage of `add_messages`**

```python
from langchain_core.messages import HumanMessage, AIMessage

def user_input_node(state: State) -> dict:
    """
    A node that adds a new user message to the state.
    """
    user_message = HumanMessage(content="Please analyze this repository.")
    
    # Return a list of messages to be appended.
    return {"messages": [user_message]}

def ai_response_node(state: State) -> dict:
    """
    A node that adds the AI's response.
    """
    ai_response = AIMessage(content="Analysis complete. The repository is complex.")

    # Return the message to be appended.
    return {"messages": [ai_response]}

# If the initial state is {"messages": [HumanMessage(...)]},
# after the AI node runs, the state will be:
# {"messages": [HumanMessage(...), AIMessage(...)]}
```

By following these patterns—using `TypedDict` for state, returning deltas, and leveraging reducers like `add_messages`—you can build robust, scalable, and maintainable LangGraph applications.
