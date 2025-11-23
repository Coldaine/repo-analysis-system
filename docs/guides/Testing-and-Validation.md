# Testing and Validation

**Status**: Canonical
**Last Updated**: November 23, 2025

Reliable LangGraph applications require rigorous testing of state transitions, reducers, and graph flows. This guide provides patterns for unit and integration testing your graph components.

## 🧪 Unit Testing Reducers

Reducers are the core logic for state updates. They should be pure functions and easy to test.

### Testing `add_messages` behavior

Ensure that your state definition correctly appends messages.

```python
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage

def test_add_messages_reducer():
    # Initial state
    existing = [HumanMessage(content="Hello")]
    
    # New update (delta)
    new_msg = AIMessage(content="Hi there")
    
    # Apply reducer
    result = add_messages(existing, new_msg)
    
    assert len(result) == 2
    assert result[0].content == "Hello"
    assert result[1].content == "Hi there"
```

## 🧪 Unit Testing Nodes

Nodes are just functions. You can test them by passing a mock state and asserting on the returned delta.

```python
from my_graph import analyze_node, State

def test_analyze_node_returns_delta():
    # Setup
    mock_state = {"messages": [HumanMessage(content="Analyze this")]}
    
    # Execute
    result = analyze_node(mock_state)
    
    # Assert
    assert "analysis" in result
    assert result["analysis"] is not None
    # Ensure it didn't return the full state
    assert "messages" not in result 
```

## 🧪 Integration Testing: `ToolNode`

Test that the `ToolNode` correctly executes tools and updates the state.

```python
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_core.messages import AIMessage

@tool
def search(query: str):
    """Search tool."""
    return f"Results for {query}"

def test_tool_node_execution():
    # Setup
    tools = [search]
    tool_node = ToolNode(tools)
    
    # Mock state with a tool call request
    tool_call = {"name": "search", "args": {"query": "LangGraph"}, "id": "call_1"}
    message = AIMessage(content="", tool_calls=[tool_call])
    state = {"messages": [message]}
    
    # Execute
    result = tool_node.invoke(state)
    
    # Assert
    messages = result["messages"]
    assert len(messages) == 1
    tool_msg = messages[0]
    assert tool_msg.type == "tool"
    assert tool_msg.content == "Results for LangGraph"
    assert tool_msg.tool_call_id == "call_1"
```

## 🧪 End-to-End Graph Testing

You can test the entire compiled graph using `invoke`.

```python
from my_graph import app

def test_simple_workflow():
    inputs = {"messages": [HumanMessage(content="Hello")]}
    
    # Run the graph
    final_state = app.invoke(inputs)
    
    # Assert final state
    assert len(final_state["messages"]) > 1
    assert isinstance(final_state["messages"][-1], AIMessage)
```

## 🛡️ Validation Best Practices

1.  **Test Parallelism**: If you have fan-out nodes, write a test that ensures all parallel branches contribute to the state correctly (e.g., using a custom reducer that sums values).
2.  **Mock External Services**: When testing nodes that use `Runtime`, pass a mock runtime with faked API clients to avoid hitting real endpoints.
3.  **Snapshot Testing**: For complex outputs, use snapshot testing to verify that the graph output remains consistent over time.
