from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.tools.patient_history_tools import get_patient_history_tool
from app.services.llm_service import summarize_patient_history_with_llm


class PatientHistorySummaryState(TypedDict, total=False):
    db: Session
    patient_id: int
    raw_history: Any
    history_data: dict[str, Any]
    llm_result: dict[str, Any]
    result: dict[str, Any]
    node_trace: list[str]


def _append_trace(state: PatientHistorySummaryState, node_name: str) -> None:
    if "node_trace" not in state:
        state["node_trace"] = []

    state["node_trace"].append(node_name)


def load_patient_history_node(
    state: PatientHistorySummaryState,
) -> PatientHistorySummaryState:
    _append_trace(state, "load_patient_history_node")

    raw_history = get_patient_history_tool(
        db=state["db"],
        patient_id=state["patient_id"],
    )

    state["raw_history"] = raw_history

    if raw_history.status == "not_found":
        state["history_data"] = {}
        return state

    state["history_data"] = raw_history.model_dump()

    return state


def summarize_history_node(
    state: PatientHistorySummaryState,
) -> PatientHistorySummaryState:
    _append_trace(state, "summarize_history_node")

    raw_history = state["raw_history"]

    if raw_history.status == "not_found":
        state["llm_result"] = {
            "status": "not_found",
            "summary": "Patient history was not found.",
            "model": None,
        }
        return state

    state["llm_result"] = summarize_patient_history_with_llm(
        state["history_data"]
    )

    return state


def build_response_node(
    state: PatientHistorySummaryState,
) -> PatientHistorySummaryState:
    _append_trace(state, "build_response_node")

    raw_history = state["raw_history"]
    llm_result = state["llm_result"]

    if raw_history.status == "not_found":
        state["result"] = {
            "ui_type": "patient_history_summary_not_found",
            "message": "Patient history was not found.",
            "ui_data": {
                "patient": None,
                "summary": llm_result["summary"],
                "llm_status": llm_result["status"],
                "llm_model": llm_result["model"],
                "graph_nodes": state["node_trace"],
            },
        }
        return state

    history_data = state["history_data"]
    patient = history_data["patient"]

    state["result"] = {
        "ui_type": "patient_history_summary",
        "message": f"Generated patient history summary for {patient['full_name']}.",
        "ui_data": {
            "patient": patient,
            "summary": llm_result["summary"],
            "llm_status": llm_result["status"],
            "llm_model": llm_result["model"],
            "graph_nodes": state["node_trace"],
        },
    }

    return state


def build_patient_history_summary_graph():
    graph = StateGraph(PatientHistorySummaryState)

    graph.add_node("load_patient_history", load_patient_history_node)
    graph.add_node("summarize_history", summarize_history_node)
    graph.add_node("build_response", build_response_node)

    graph.set_entry_point("load_patient_history")
    graph.add_edge("load_patient_history", "summarize_history")
    graph.add_edge("summarize_history", "build_response")
    graph.add_edge("build_response", END)

    return graph.compile()


def run_patient_history_summary_graph(
    db: Session,
    patient_id: int,
) -> dict[str, Any]:
    graph = build_patient_history_summary_graph()

    final_state = graph.invoke(
        {
            "db": db,
            "patient_id": patient_id,
            "node_trace": [],
        }
    )

    return final_state["result"]