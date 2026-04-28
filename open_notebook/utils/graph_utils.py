import asyncio
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from loguru import logger


async def get_session_message_count(
    graph,
    session_id: str,
    *,
    checkpoint_file: Optional[str] = None,
    state_graph: Optional[StateGraph] = None,
) -> int:
    """Get message count from LangGraph state, returns 0 on error.

    If checkpoint_file is provided, uses SqliteSaver to read from the persistent
    checkpoint file (matching the streaming endpoint's write path). The state_graph
    parameter must also be provided when using checkpoint_file.

    Otherwise falls back to the passed-in graph (for backward compatibility).
    """
    try:
        if checkpoint_file and state_graph is not None:
            from langgraph.checkpoint.sqlite import SqliteSaver

            with SqliteSaver.from_conn_string(checkpoint_file) as saver:
                temp_graph = state_graph.compile(checkpointer=saver)
                thread_state = await asyncio.to_thread(
                    temp_graph.get_state,
                    config=RunnableConfig(configurable={"thread_id": session_id}),
                )
        else:
            thread_state = await asyncio.to_thread(
                graph.get_state,
                config=RunnableConfig(configurable={"thread_id": session_id}),
            )
        if (
            thread_state
            and thread_state.values
            and "messages" in thread_state.values
        ):
            return len(thread_state.values["messages"])
    except Exception as e:
        logger.warning(f"Could not fetch message count for session {session_id}: {e}")
    return 0
