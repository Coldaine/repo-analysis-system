"""
Documentation Alignment Investigator Agent (LangGraph v1.0 Standard)
Performs forensic analysis on repository history to resolve documentation conflicts.
Implemented as a Sub-Graph with Functional Wrapper Encapsulation.
"""

import logging
import subprocess
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages

# Try to import ChatAnthropic, fallback to a mock or error if not present
try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    # Fallback for environments without the specific package
    # In production, this should be properly installed
    ChatAnthropic = None

# Try to import Runtime, fallback to Any if not present (v1.0+ feature)
try:
    from langgraph.types import Runtime
except ImportError:
    Runtime = Any

logger = logging.getLogger(__name__)

# --- Tools ---

@tool
def git_log(file_path: str, limit: int = 5) -> str:
    """
    Get the commit history for a specific file.
    Returns the commit hash, author, date, and message.
    
    Look for pivot keywords in commit messages: "refactor", "architecture", 
    "rework", "redesign", "big change" - these indicate intentional shifts.
    """
    try:
        cmd = ["git", "log", f"-{limit}", "--format=%h|%an|%ad|%s", "--date=iso", "--", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error running git log: {e}"

@tool
def git_diff(commit_a: str, commit_b: str, file_path: Optional[str] = None) -> str:
    """
    Get the diff between two commits.
    If file_path is provided, only shows diff for that file.
    """
    try:
        cmd = ["git", "diff", commit_a, commit_b]
        if file_path:
            cmd.append("--")
            cmd.append(file_path)
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error running git diff: {e}"

@tool
def git_blame(file_path: str, start_line: int = 1, end_line: int = 10) -> str:
    """
    Get git blame for a specific line range in a file.
    """
    try:
        cmd = ["git", "blame", "-L", f"{start_line},{end_line}", "--", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error running git blame: {e}"

@tool
def read_file(file_path: str) -> str:
    """
    Read the contents of a file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

tools = [git_log, git_diff, git_blame, read_file]

# --- State ---

class InvestigatorState(TypedDict):
    conflict_context: str
    involved_files: List[str]
    messages: Annotated[List[BaseMessage], add_messages]

# --- Nodes ---

def investigator_agent(state: InvestigatorState, runtime: Runtime):
    """
    The brain of the investigator. Decides which tools to call.
    Uses forensic analysis techniques inspired by PR #4 (@google-labs-jules[bot]).
    """
    if ChatAnthropic is None:
        raise ImportError("langchain_anthropic is required for this agent.")
        
    # Initialize model - In a real app, this might come from a config or factory
    # We use a high-intelligence model for forensics
    # Note: Ensure ANTHROPIC_API_KEY is in environment
    # V1.0 Pattern: Use runtime.context for configuration
    model_name = "claude-3-5-sonnet-20240620"
    if hasattr(runtime, 'context') and isinstance(runtime.context, dict):
         model_name = runtime.context.get("model_name", model_name)
    
    # Enhanced system prompt with forensic analysis framework
    # Credit: Prompt engineering from PR #4 by @google-labs-jules[bot]
    system_prompt = """You are a forensic software engineering expert.
Your task is to determine the "True Intent" behind conflicting documentation or architectural divergence.

When investigating conflicts:
1. Use git_log to examine commit history for involved files
2. Use git_diff to compare changes between suspicious commits
3. Use git_blame to identify line-level authorship
4. Use read_file to examine current file contents

Analysis Framework (from PR #4):
- **Recency**: Prioritize newer commits as more likely to represent current intent
- **Pivot Detection**: Flag commits with keywords like "refactor", "architecture", "rework", "redesign", "big change"
- **File Specificity**: `/docs/` directory files are typically more authoritative than `README.md`
- **Intent Signals**: Give more weight to commits with explicit intent messages vs. routine changes

Output Format:
- Synthesize a clear verdict on what the true intent is
- Cite specific commits, authors, and dates as evidence
- Classify divergence as intentional (pivot) or accidental (drift)
- Recommend actions (update conflicting docs, accept new direction, etc.)
"""
    
    model = ChatAnthropic(model=model_name, temperature=0)
    model_with_tools = model.bind_tools(tools)
    
    # Inject system prompt if this is the first message
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=system_prompt)] + list(messages)
    
    return {"messages": [model_with_tools.invoke(messages)]}

# --- Graph Construction ---

def compile_forensics_graph():
    """
    Compiles the forensics subgraph.
    """
    workflow = StateGraph(InvestigatorState)
    
    workflow.add_node("investigator", investigator_agent)
    workflow.add_node("tools", ToolNode(tools))
    
    workflow.add_edge(START, "investigator")
    workflow.add_conditional_edges("investigator", tools_condition)
    workflow.add_edge("tools", "investigator")
    
    return workflow.compile()

# --- Functional Wrapper ---

def call_forensics_wrapper(state: Dict, runtime: Runtime) -> Dict:
    """
    Wrapper node to invoke the investigator subgraph.
    Acts as a firewall between ParentState and InvestigatorState.
    
    Args:
        state: The parent graph's state. Expected to contain 'current_conflict'.
        runtime: The runtime environment object.
        
    Returns:
        Update for the parent graph's state.
    """
    # 1. Down-Mapping
    # Assuming parent state has 'current_conflict' or similar
    conflict = state.get("current_conflict", {})
    description = conflict.get("description", "Unknown conflict")
    files = conflict.get("files", [])
    
    child_input = {
        "conflict_context": description,
        "involved_files": files,
        "messages": [
            HumanMessage(content=f"Investigate the following documentation conflict: {description}. \nFiles involved: {files}. \nUse git tools to determine the source of truth.")
        ]
    }
    
    # 2. Invocation
    # Compile on the fly or cache it globally
    graph = compile_forensics_graph()
    
    # Pass runtime config if available
    config = getattr(runtime, 'config', {})
    result = graph.invoke(child_input, config=config)
    
    # 3. Up-Mapping
    final_message = result["messages"][-1]
    content = final_message.content
    
    return {
        "forensics_verdict": content,
        # We can also append a summary to the main conversation
        "messages": [AIMessage(content=f"Forensics Investigation Result: {content}")]
    }

