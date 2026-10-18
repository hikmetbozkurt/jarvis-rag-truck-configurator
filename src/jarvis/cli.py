import argparse
import logging
from pathlib import Path

from jarvis.config import Settings, get_settings
from jarvis.logging_setup import configure_logging

logger = logging.getLogger("jarvis.cli")


def run_ingestion(settings: Settings, skip_if_populated: bool) -> None:
    from jarvis.bootstrap import create_embedding_model, create_knowledge_base_builder, create_vector_store

    builder = create_knowledge_base_builder(
        settings, create_embedding_model(settings), create_vector_store(settings)
    )
    report = builder.build_knowledge_base(skip_if_populated=skip_if_populated)
    if report.was_skipped:
        print("Knowledge base already populated, nothing to do.")
        return
    for source_name, document_count in report.document_count_by_source.items():
        print(f"{source_name:<24} {document_count:>4} documents")
    print(f"{'Total':<24} {report.total_document_count:>4} documents")


def run_retrieval_evaluation(settings: Settings, golden_set_path: Path) -> None:
    from jarvis.bootstrap import create_embedding_model, create_hybrid_retriever, create_vector_store
    from jarvis.evaluation.retrieval_evaluation import (
        RetrievalEvaluator,
        load_golden_queries,
        save_evaluation_report,
    )
    from jarvis.retrieval.query_analysis import KeywordIntentClassifier

    retriever = create_hybrid_retriever(
        settings, create_embedding_model(settings), create_vector_store(settings)
    )
    evaluator = RetrievalEvaluator(retriever, KeywordIntentClassifier())
    report = evaluator.evaluate_golden_queries(load_golden_queries(golden_set_path))
    report_path = save_evaluation_report(report, settings.evaluation_report_directory)
    print(report.render_markdown_summary())
    print(f"\nFull report: {report_path}")


def run_interactive_chat(settings: Settings) -> None:
    from jarvis.bootstrap import build_application_container
    from jarvis.domain.configuration import VehicleBuild
    from jarvis.domain.conversation import AssistantRequest, ChatTurn

    container = build_application_container(settings)
    history: list[ChatTurn] = []
    active_build = VehicleBuild()
    print("Jarvis is ready. Type 'exit' to quit.")

    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        response = container.assistant.answer_question(
            AssistantRequest(question=question, history=history, current_build=active_build)
        )
        active_build = response.active_build
        history += [
            ChatTurn(role="user", content=question),
            ChatTurn(role="assistant", content=response.reply),
        ]
        source_ids = ", ".join(source.document_id for source in response.sources) or "none"
        print(f"\nJarvis: {response.reply}")
        print(
            f"[intent={response.intent.value} status={response.validation.status.value} "
            f"sources={source_ids} trace={response.trace_id}]"
        )
    container.shutdown()


def run_api_server(host: str, port: int, reload: bool) -> None:
    import uvicorn

    uvicorn.run("jarvis.api.app:create_app", factory=True, host=host, port=port, reload=reload)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jarvis", description="Jarvis truck configuration assistant")
    subcommands = parser.add_subparsers(dest="command", required=True)

    ingest_command = subcommands.add_parser("ingest", help="Embed the datasets into the vector store")
    ingest_command.add_argument("--skip-if-populated", action="store_true")

    evaluate_command = subcommands.add_parser("evaluate", help="Measure retrieval quality on the golden set")
    evaluate_command.add_argument("--golden-set", type=Path, default=None)

    subcommands.add_parser("chat", help="Chat with Jarvis in the terminal")

    serve_command = subcommands.add_parser("serve", help="Start the HTTP API")
    serve_command.add_argument("--host", default="127.0.0.1")
    serve_command.add_argument("--port", type=int, default=8000)
    serve_command.add_argument("--reload", action="store_true")
    return parser


def run_command_line(argument_list: list[str] | None = None) -> None:
    arguments = build_argument_parser().parse_args(argument_list)
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_as_json)

    if arguments.command == "ingest":
        run_ingestion(settings, arguments.skip_if_populated)
    elif arguments.command == "evaluate":
        run_retrieval_evaluation(settings, arguments.golden_set or settings.golden_set_path)
    elif arguments.command == "chat":
        run_interactive_chat(settings)
    elif arguments.command == "serve":
        run_api_server(arguments.host, arguments.port, arguments.reload)


if __name__ == "__main__":
    run_command_line()
