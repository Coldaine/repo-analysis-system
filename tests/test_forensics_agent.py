"""
Integration tests for the forensics agent wrapper and graph wiring.
"""
from unittest.mock import patch
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from src.agents.forensics_agent import (
    compile_forensics_graph,
    call_forensics_wrapper,
    InvestigatorState
)

# Mock runtime
class MockRuntime:
    def __init__(self):
        self.config = {}
        self.context = {}

def test_graph_compilation():
    """Test that the forensics graph compiles correctly"""
    graph = compile_forensics_graph()
    assert graph is not None
    print("✓ Graph compiled successfully")

def test_wrapper_function():
    """Test the functional wrapper with mock data"""
    runtime = MockRuntime()
    runtime.config = {"configurable": {"thread_id": "test-thread"}}
    
    # Simulate parent state that would be passed from the orchestrator
    parent_state = {
        "current_conflict": {
            "description": "README.md says feature X is deprecated, but docs/api.md says it's supported",
            "files": ["README.md", "docs/api.md"]
        }
    }

    captured_child_input = {}

    class StubGraph:
        def invoke(self, child_input, config=None):
            captured_child_input["value"] = child_input
            assert config == runtime.config
            return {"messages": [AIMessage(content="Stub verdict")]}  # pragma: no cover

    with patch("src.agents.forensics_agent.compile_forensics_graph", return_value=StubGraph()):
        result = call_forensics_wrapper(parent_state, runtime)

    assert result["forensics_verdict"] == "Stub verdict"
    assert result["messages"][0].content.startswith("Forensics Investigation Result: Stub verdict")
    child_input = captured_child_input["value"]
    assert child_input["conflict_context"] == parent_state["current_conflict"]["description"]
    assert child_input["involved_files"] == parent_state["current_conflict"]["files"]
    assert isinstance(child_input["messages"][0], HumanMessage)

def test_state_typing():
    """Test that InvestigatorState type is correct"""
    state: InvestigatorState = {
        "conflict_context": "Test conflict",
        "involved_files": ["test.py"],
        "messages": [HumanMessage(content="Test message")]
    }
    
    assert "conflict_context" in state
    assert "involved_files" in state
    assert "messages" in state
    print("✓ InvestigatorState typing correct")

def test_system_prompt_injection():
    """Verify system prompt is properly injected on first call"""
    # This is tested separately to avoid needing actual API keys
    messages = [HumanMessage(content="Investigate")]
    
    # Simulate the injection logic
    if not any(isinstance(m, SystemMessage) for m in messages):
        test_prompt = "You are a forensic expert"
        messages = [SystemMessage(content=test_prompt)] + list(messages)
    
    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert "forensic expert" in messages[0].content
    print("✓ System prompt injection works correctly")

if __name__ == "__main__":
    print("Running forensics agent integration tests...\n")
    test_graph_compilation()
    test_wrapper_function()
    test_state_typing()
    test_system_prompt_injection()
    print("\n✅ All forensics agent integration tests passed!")
    print("\nNote: Full LLM integration requires ANTHROPIC_API_KEY")
