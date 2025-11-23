# Checkpointer and Persistence

Persistence is a cornerstone of robust, production-grade LangGraph applications. The checkpointer system provides a seamless way to save and resume the state of your graphs, ensuring that long-running or critical workflows can survive interruptions and continue from where they left off.

This guide provides a deep dive into configuring and using checkpointers, with a focus on the `PostgresSaver`.

## The Role of the Checkpointer

A checkpointer is a backend component that automatically records the state of your graph at the end of each successful step. When you `invoke` a graph with a specific `thread_id`, the checkpointer does the following:

1.  **Saves State**: After each node in the graph finishes execution, the checkpointer saves the complete state to a persistent store (like a database).
2.  **Enables Resumption**: If you `invoke` the graph again with the same `thread_id`, the checkpointer automatically loads the most recent saved state for that thread. The graph then resumes execution from the step *after* the last successfully completed one.

This makes your graphs resilient to failures, restarts, and deployments.

## Configuring `PostgresSaver`

For production environments, `PostgresSaver` is the recommended checkpointer. It stores graph snapshots in a PostgreSQL database, providing a durable and queryable persistence layer.

### 1. Database Schema

First, you need a table in your database to store the checkpoints. The `PostgresSaver` can create this for you automatically, but here is the SQL schema for reference:

```sql
CREATE TABLE IF NOT EXISTS lg_checkpoints (
    thread_id TEXT PRIMARY KEY,
    checkpoint BYTEA,
    parent_ts TEXT
);
```

### 2. Configuration

The checkpointer is configured when you compile your graph. You instantiate `PostgresSaver` with the database connection details and pass it to the `compile` method.

```python
import os
from langgraph.checkpoint.postgres import PostgresSaver

# The connection string should be securely managed (e.g., via environment variables)
db_url = os.environ.get("POSTGRES_CONNECTION_STRING", "postgresql+psycopg2://user:pass@localhost/db_name")

# Instantiate the checkpointer
# `serde` handles the serialization of the state.
checkpointer = PostgresSaver.from_conn_string(db_url)

# Pass the checkpointer to the compile() method
graph = builder.compile(checkpointer=checkpointer)
```

## Example: Resuming an Interrupted Run

This example demonstrates the full lifecycle of a resumable graph: initial invocation, interruption, and successful resumption.

```python
import os
import uuid
import time
from typing import TypedDict, Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import HumanMessage, AIMessage

# --- 1. Define State and Graph ---

class State(TypedDict):
    messages: Annotated[list, add_messages]

def node_1(state: State):
    print("Executing Node 1")
    time.sleep(1)
    return {"messages": [AIMessage(content="Hello from Node 1")]}

def node_2(state: State):
    print("Executing Node 2")
    # Simulate a failure during the second step
    if len(state["messages"]) < 3:
        print("Node 2 is failing...")
        raise ValueError("A transient error occurred!")
    print("Node 2 succeeded on retry.")
    time.sleep(1)
    return {"messages": [AIMessage(content="Hello from Node 2")]}

def node_3(state: State):
    print("Executing Node 3")
    time.sleep(1)
    return {"messages": [AIMessage(content="Workflow complete!")]}

builder = StateGraph(State)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)

builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", "node_3")
builder.add_edge("node_3", END)

# --- 2. Compile with Checkpointer ---

# Ensure you have a running Postgres instance and the connection string is set
db_url = os.environ.get("POSTGRES_CONNECTION_STRING")
if not db_url:
    raise ValueError("POSTGRES_CONNECTION_STRING environment variable not set.")

checkpointer = PostgresSaver.from_conn_string(db_url)
graph = builder.compile(checkpointer=checkpointer)

# --- 3. Run and Simulate Interruption ---

# Each run needs a unique, persistent ID
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}

print(f"--- Starting initial run for thread_id: {thread_id} ---")
try:
    # The first invocation will fail in node_2
    graph.invoke({"messages": [HumanMessage(content="Start")]}, config)
except ValueError as e:
    print(f"\nGraph interrupted as expected: {e}\n")

# At this point, the checkpointer has saved the state *after* node_1 completed.
# We can verify this by inspecting the checkpoint.
checkpoint = checkpointer.get(config)
print("--- State after interruption (loaded from checkpoint) ---")
print(checkpoint.channel_values["messages"])
print("-" * 20)


# --- 4. Resume the Run ---

print("\n--- Resuming the run ---")
# To resume, we invoke the graph again with the same config.
# We pass `None` as the input because the state is loaded from the checkpoint.
final_state = graph.invoke(None, config=config)

print("\n--- Final State ---")
for message in final_state["messages"]:
    print(f"- {message.type}: {message.content}")

# Expected Output:
# - human: Start
# - ai: Hello from Node 1
# - ai: Hello from Node 2
# - ai: Workflow complete!
```

## Time-Travel and Forking

Checkpoints are immutable snapshots. This enables powerful debugging and what-if scenarios.

### Time-Traveling

You can inspect the state of a graph at any point in its history by retrieving a specific checkpoint.

```python
# Get the history of a thread
history = checkpointer.list(config)

# Get the state as it was after the first step
first_step_checkpoint = history[1] 
print(first_step_checkpoint.channel_values)
```

### Forking a Run

You can "fork" a run by starting a new run from an old checkpoint. This is useful for exploring alternative paths without re-running the initial steps.

```python
# Get a checkpoint from a previous run
old_checkpoint = checkpointer.get({"configurable": {"thread_id": "some-past-thread-id"}})

# Start a new run, but from the old checkpoint's state
new_thread_id = str(uuid.uuid4())
forked_config = {"configurable": {"thread_id": new_thread_id}}

# The `invoke` call will start with the state from `old_checkpoint`
graph.invoke(old_checkpoint.channel_values, config=forked_config)
```

By leveraging checkpointers, you can build highly reliable and introspectable agentic systems.
