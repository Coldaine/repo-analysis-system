# The LangGraph Runtime Object

The `Runtime` object is a powerful feature in LangGraph that allows you to pass request-scoped, read-only context to all nodes in your graph without cluttering the persistent state. It is the ideal place for resources like database connections, API clients, or user-specific configuration that don't change during a graph's execution.

## State vs. Runtime: What's the Difference?

It's important to understand the distinction between the `State` and the `Runtime`:

-   **`State`**: The `State` object (typically a `TypedDict`) holds the data that **evolves** as the graph runs. It's the dynamic, mutable part of your application. The state is what gets saved in checkpoints, allowing you to resume or time-travel through a graph's execution. Examples include conversational history (`messages`), intermediate analysis results, or flags that control flow.

-   **`Runtime`**: The `Runtime` object holds **static, read-only context** for a single `invoke` call. It is not persisted in checkpoints and should not be modified by nodes. It's a dependency injection mechanism for your graph. Examples include API keys, database connection pools, the current user's ID, or system-level configuration.

| Feature          | `State`                                       | `Runtime`                                         |
| ---------------- | --------------------------------------------- | ------------------------------------------------- |
| **Purpose**      | Dynamic, evolving data                        | Static, request-scoped context                    |
| **Mutability**   | Writable (nodes return deltas to update it)   | Read-only (should not be modified by nodes)       |
| **Persistence**  | Saved in checkpoints                          | **Not** saved in checkpoints                      |
| **Lifecycle**    | Persists across an entire graph execution     | Lives for a single `invoke` or `stream` call      |
| **Example**      | `messages`, `analysis_result`                 | `db_connection`, `api_client`, `user_id`          |

## Adopting the Runtime Object Pattern

Using the `Runtime` object involves three steps: defining a context class, updating your node signatures, and passing the runtime context when you invoke the graph.

### 1. Define a Runtime Context Class

First, define a class (a `dataclass` is a good choice) that holds the resources your nodes will need.

```python
from dataclasses import dataclass

# A simple database client (for demonstration)
class DatabaseClient:
    def get_user_prefs(self, user_id: str) -> dict:
        return {"language": "en", "theme": "dark"}

@dataclass
class UserContext:
    """
    A runtime context object holding user-specific information.
    """
    user_id: str
    db_client: DatabaseClient
```

### 2. Update Node Signatures

Next, update your node functions to accept a `Runtime` object. The `Runtime` object is generic, so you can type hint it with your context class to get static analysis benefits.

The signature for a node that uses the runtime is `(state, runtime)`.

```python
from typing import TypedDict
from langgraph.runtime import Runtime

class State(TypedDict):
    user_preferences: dict

# The node signature now accepts a 'runtime' argument.
# We use Runtime[UserContext] to get type hints for our context object.
def load_user_preferences(state: State, runtime: Runtime[UserContext]) -> dict:
    """
    Loads user preferences from the database using the runtime context.
    """
    print(f"Loading preferences for user: {runtime.context.user_id}")
    
    # Access the database client from the runtime context.
    prefs = runtime.context.db_client.get_user_prefs(runtime.context.user_id)
    
    # Return a delta to update the persistent state.
    return {"user_preferences": prefs}
```

### 3. Pass the Runtime to `invoke`

Finally, when you compile and invoke your graph, pass the `runtime` argument to the `invoke` (or `stream`) method.

```python
from langgraph.graph import StateGraph, START, END

# Create the graph
graph_builder = StateGraph(State)
graph_builder.add_node("load_prefs", load_user_preferences)
graph_builder.add_edge(START, "load_prefs")
graph_builder.add_edge("load_prefs", END)
graph = graph_builder.compile()

# Instantiate the runtime context and the graph runtime
db_client = DatabaseClient()
user_context = UserContext(user_id="user-123", db_client=db_client)
graph_runtime = Runtime(context=user_context)

# Invoke the graph, passing the runtime
initial_state = {}
final_state = graph.invoke(initial_state, runtime=graph_runtime)

print(final_state["user_preferences"])
# Output: {'language': 'en', 'theme': 'dark'}
```

## Accessing the Checkpointer via `runtime.store`

The `Runtime` object also provides access to the underlying checkpointer (if one is configured) via the `runtime.store` attribute. This is an advanced feature that can be used for complex scenarios, such as manually saving or loading state outside the normal graph flow.

```python
def custom_save_node(state: State, runtime: Runtime) -> None:
    """
    A node that manually interacts with the checkpointer.
    """
    if runtime.store:
        # Get the current checkpoint
        current_checkpoint = runtime.store.get(runtime.checkpoint_id)
        print(f"Manually accessed checkpoint: {current_checkpoint}")
        
        # This is for inspection; modifying state should still be done
        # by returning deltas from the node.
```

By separating static context from dynamic state, the `Runtime` object helps you build cleaner, more maintainable, and more efficient LangGraph applications.
