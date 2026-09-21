"""Compare three LlamaIndex chunking techniques for HW3."""

from __future__ import annotations

import argparse
import csv
import json
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from llama_index.core import (
    Document,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.node_parser import (
    SemanticSplitterNodeParser,
    SentenceWindowNodeParser,
    TokenTextSplitter,
)
from llama_index.core.schema import MetadataMode
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.embeddings.huggingface import (
    HuggingFaceEmbedding,
)
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CORPUS = (
    ROOT / "data" / "hw03" / "corpus"
)
DEFAULT_QUESTIONS = (
    ROOT / "reports" / "hw03" / "questions.yaml"
)
DEFAULT_RAW_DIRECTORY = (
    ROOT / "reports" / "hw03" / "raw"
)
WARMUP_PATH = (
    ROOT
    / "data"
    / "hw03"
    / "warmup"
    / "tinyshakespeare.txt"
)

MODEL_NAME = (
    "sentence-transformers/all-MiniLM-L6-v2"
)

SEED = 2562
TOP_K = 5

TOKEN_CHUNK_SIZE = 256
TOKEN_CHUNK_OVERLAP = 32

SEMANTIC_BUFFER_SIZE = 1
SEMANTIC_BREAKPOINT_PERCENTILE = 95

SENTENCE_WINDOW_SIZE = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare Token, Semantic, and "
            "Sentence-window retrieval."
        )
    )

    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS,
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=DEFAULT_QUESTIONS,
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_RAW_DIRECTORY,
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=TOP_K,
    )
    parser.add_argument(
        "--warmup-only",
        action="store_true",
    )

    return parser.parse_args()


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def read_pdf(path: Path) -> str:
    reader = PdfReader(path)

    pages = [
        page.extract_text() or ""
        for page in reader.pages
    ]

    return "\n\n".join(pages).strip()


def load_documents(corpus_directory: Path):
    documents = []

    for path in sorted(
        corpus_directory.glob("*.pdf")
    ):
        text = read_pdf(path)

        if not text:
            raise ValueError(
                f"No text extracted from {path}"
            )

        documents.append(
            Document(
                text=text,
                metadata={
                    "source_file": path.name,
                    "byte_size": path.stat().st_size,
                },
            )
        )

        print(
            f"Loaded {path.name}: "
            f"{len(text):,} extracted characters"
        )

    if not documents:
        raise ValueError(
            f"No PDF files found in {corpus_directory}"
        )

    return documents


def load_questions(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    questions = data.get("questions", [])

    if len(questions) < 5:
        raise ValueError(
            "At least five questions are required."
        )

    return questions


def create_embedding_model():
    return HuggingFaceEmbedding(
        model_name=MODEL_NAME,
        device="cpu",
    )


def create_parsers(embed_model):
    return {
        "Token": TokenTextSplitter(
            chunk_size=TOKEN_CHUNK_SIZE,
            chunk_overlap=TOKEN_CHUNK_OVERLAP,
        ),
        "Semantic": (
            SemanticSplitterNodeParser(
                buffer_size=SEMANTIC_BUFFER_SIZE,
                breakpoint_percentile_threshold=(
                    SEMANTIC_BREAKPOINT_PERCENTILE
                ),
                embed_model=embed_model,
            )
        ),
        "Sentence window": (
            SentenceWindowNodeParser.from_defaults(
                window_size=SENTENCE_WINDOW_SIZE,
                window_metadata_key="window",
                original_text_metadata_key=(
                    "original_text"
                ),
            )
        ),
    }


def run_warmup(
    embed_model,
    parsers,
) -> None:
    if not WARMUP_PATH.exists():
        raise FileNotFoundError(
            f"Missing warm-up file: {WARMUP_PATH}"
        )

    full_text = WARMUP_PATH.read_text(
        encoding="utf-8"
    )

    # A bounded sample keeps the warm-up quick.
    warmup_text = full_text[:50_000]

    document = Document(
        text=warmup_text,
        metadata={
            "source_file": "tinyshakespeare.txt"
        },
    )

    print("\n=== Tiny Shakespeare Warm-up ===")
    print(
        f"Warm-up characters: {len(warmup_text):,}"
    )

    for technique, parser in parsers.items():
        started = time.perf_counter()

        nodes = parser.get_nodes_from_documents(
            [document]
        )

        elapsed_ms = (
            time.perf_counter() - started
        ) * 1000

        print(
            f"{technique}: "
            f"{len(nodes)} chunks; "
            f"{elapsed_ms:.2f} ms"
        )

    sample_embedding = (
        embed_model.get_text_embedding(
            "To be, or not to be."
        )
    )

    print(
        "Warm-up embedding dimension:",
        len(sample_embedding),
    )
    print("Warm-up completed successfully.")


def build_nodes(
    documents,
    parsers,
):
    all_nodes = {}

    print("\n=== Graded Corpus Chunking ===")

    for technique, parser in parsers.items():
        started = time.perf_counter()

        nodes = parser.get_nodes_from_documents(
            documents
        )

        elapsed_ms = (
            time.perf_counter() - started
        ) * 1000

        if not nodes:
            raise ValueError(
                f"{technique} produced no nodes."
            )

        all_nodes[technique] = nodes

        lengths = [
            len(
                node.get_content(
                    metadata_mode=MetadataMode.NONE
                )
            )
            for node in nodes
        ]

        print(
            f"{technique}: "
            f"{len(nodes)} chunks; "
            f"average length "
            f"{np.mean(lengths):.2f} characters; "
            f"chunking time {elapsed_ms:.2f} ms"
        )

    return all_nodes


def build_indexes(
    nodes_by_technique,
    embed_model,
):
    indexes = {}

    print("\n=== In-memory Indexing ===")

    for technique, nodes in (
        nodes_by_technique.items()
    ):
        vector_store = SimpleVectorStore()

        storage_context = (
            StorageContext.from_defaults(
                vector_store=vector_store
            )
        )

        started = time.perf_counter()

        indexes[technique] = VectorStoreIndex(
            nodes,
            storage_context=storage_context,
            embed_model=embed_model,
            show_progress=True,
        )

        elapsed_ms = (
            time.perf_counter() - started
        ) * 1000

        print(
            f"{technique}: indexed "
            f"{len(nodes)} chunks in "
            f"{elapsed_ms:.2f} ms"
        )

    return indexes


def cosine_similarity(
    left: np.ndarray,
    right: np.ndarray,
) -> float:
    denominator = (
        np.linalg.norm(left)
        * np.linalg.norm(right)
    )

    if denominator == 0:
        return 0.0

    return float(
        np.dot(left, right) / denominator
    )


def text_preview(
    text: str,
    limit: int = 160,
) -> str:
    cleaned = normalize_text(text)

    if len(cleaned) <= limit:
        return cleaned

    return cleaned[:limit].rstrip() + "..."


def print_results_table(
    rows: list[dict[str, Any]],
) -> None:
    header = (
        f"{'Rank':<6}"
        f"{'Store':<12}"
        f"{'Cosine':<12}"
        f"{'Length':<10}"
        f"Preview"
    )

    print(header)
    print("-" * 100)

    for row in rows:
        store_score = row["store_score"]

        if store_score is None:
            store_display = "N/A"
        else:
            store_display = (
                f"{store_score:.6f}"
            )

        print(
            f"{row['rank']:<6}"
            f"{store_display:<12}"
            f"{row['cosine_similarity']:<12.6f}"
            f"{row['chunk_length']:<10}"
            f"{row['preview']}"
        )


def retrieve_for_question(
    technique: str,
    index,
    question_record: dict[str, Any],
    embed_model,
    top_k: int,
) -> dict[str, Any]:
    query = question_record["question"]

    query_embedding = np.asarray(
        embed_model.get_query_embedding(query),
        dtype=float,
    )

    retriever = index.as_retriever(
        similarity_top_k=top_k
    )

    started = time.perf_counter()
    retrieved = retriever.retrieve(query)
    latency_ms = (
        time.perf_counter() - started
    ) * 1000

    rows = []
    document_vectors = []

    for rank, item in enumerate(
        retrieved,
        start=1,
    ):
        node = item.node

        text = node.get_content(
            metadata_mode=MetadataMode.NONE
        )

        document_embedding = np.asarray(
            embed_model.get_text_embedding(text),
            dtype=float,
        )

        document_vectors.append(
            document_embedding
        )

        source_file = node.metadata.get(
            "source_file",
            "unknown",
        )

        window_text = node.metadata.get(
            "window"
        )

        row = {
            "question_id": question_record["id"],
            "question": query,
            "expected_answer": (
                question_record["expected_answer"]
            ),
            "expected_source": (
                question_record["expected_source"]
            ),
            "unique_source": bool(
                question_record.get(
                    "unique_source",
                    False,
                )
            ),
            "technique": technique,
            "rank": rank,
            "source_file": source_file,
            "store_score": (
                float(item.score)
                if item.score is not None
                else None
            ),
            "cosine_similarity": (
                cosine_similarity(
                    query_embedding,
                    document_embedding,
                )
            ),
            "chunk_length": len(text),
            "preview": text_preview(text),
            "full_text": text,
            "window_text": window_text,
            "expected_source_match": (
                source_file
                == question_record[
                    "expected_source"
                ]
            ),
            "retrieval_latency_ms": latency_ms,
        }

        rows.append(row)

    if document_vectors:
        stacked_vectors = np.vstack(
            document_vectors
        )
    else:
        stacked_vectors = np.empty(
            (0, query_embedding.shape[0])
        )

    print(
        f"\n=== {technique} | "
        f"{question_record['id']} ==="
    )
    print("Query:", query)
    print(
        "Query embedding dimension:",
        query_embedding.shape[0],
    )
    print(
        "Query embedding first 8 values:",
        np.round(
            query_embedding[:8],
            6,
        ).tolist(),
    )
    print(
        "Query vector shape:",
        query_embedding.shape,
    )
    print(
        "Stacked document vectors shape:",
        stacked_vectors.shape,
    )
    print(
        f"Retrieval latency: "
        f"{latency_ms:.3f} ms"
    )

    print_results_table(rows)

    return {
        "question_id": question_record["id"],
        "question": query,
        "expected_answer": (
            question_record["expected_answer"]
        ),
        "expected_source": (
            question_record["expected_source"]
        ),
        "technique": technique,
        "query_embedding_dimension": int(
            query_embedding.shape[0]
        ),
        "query_embedding_first_8": (
            query_embedding[:8].tolist()
        ),
        "query_vector_shape": list(
            query_embedding.shape
        ),
        "document_vectors_shape": list(
            stacked_vectors.shape
        ),
        "retrieval_latency_ms": latency_ms,
        "results": rows,
    }


def chunk_statistics(
    nodes_by_technique,
) -> list[dict[str, Any]]:
    records = []

    for technique, nodes in (
        nodes_by_technique.items()
    ):
        lengths = [
            len(
                node.get_content(
                    metadata_mode=MetadataMode.NONE
                )
            )
            for node in nodes
        ]

        records.append(
            {
                "technique": technique,
                "chunk_count": len(nodes),
                "average_chunk_length": float(
                    np.mean(lengths)
                ),
                "minimum_chunk_length": int(
                    np.min(lengths)
                ),
                "maximum_chunk_length": int(
                    np.max(lengths)
                ),
            }
        )

    return records


def write_outputs(
    output_directory: Path,
    runs: list[dict[str, Any]],
    chunk_stats: list[dict[str, Any]],
    top_k: int,
) -> None:
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    structured_output = {
        "homework_number": 3,
        "sid4": 2562,
        "seed": SEED,
        "embedding_model": MODEL_NAME,
        "top_k": top_k,
        "parameters": {
            "token_chunk_size": (
                TOKEN_CHUNK_SIZE
            ),
            "token_chunk_overlap": (
                TOKEN_CHUNK_OVERLAP
            ),
            "semantic_buffer_size": (
                SEMANTIC_BUFFER_SIZE
            ),
            "semantic_breakpoint_percentile": (
                SEMANTIC_BREAKPOINT_PERCENTILE
            ),
            "sentence_window_size": (
                SENTENCE_WINDOW_SIZE
            ),
        },
        "chunk_statistics": chunk_stats,
        "runs": runs,
    }

    json_path = (
        output_directory
        / "retrieval_results.json"
    )

    json_path.write_text(
        json.dumps(
            structured_output,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    flat_rows = [
        row
        for run in runs
        for row in run["results"]
    ]

    csv_path = (
        output_directory
        / "retrieval_results.csv"
    )

    fieldnames = [
        "question_id",
        "technique",
        "rank",
        "source_file",
        "store_score",
        "cosine_similarity",
        "chunk_length",
        "retrieval_latency_ms",
        "expected_source",
        "expected_source_match",
        "preview",
    ]

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in flat_rows:
            writer.writerow(
                {
                    key: row.get(key)
                    for key in fieldnames
                }
            )

    stats_path = (
        output_directory
        / "chunk_statistics.json"
    )

    stats_path.write_text(
        json.dumps(
            chunk_stats,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("\n=== Saved Machine-readable Output ===")
    print(json_path)
    print(csv_path)
    print(stats_path)
    print(
        "Retrieval rows saved:",
        len(flat_rows),
    )


def main() -> None:
    args = parse_args()

    random.seed(SEED)
    np.random.seed(SEED)

    print("Embedding model:", MODEL_NAME)
    print("SEED:", SEED)
    print("Device: CPU")
    print("Top-k:", args.top_k)

    embed_model = create_embedding_model()
    parsers = create_parsers(embed_model)

    run_warmup(
        embed_model,
        parsers,
    )

    if args.warmup_only:
        return

    documents = load_documents(args.corpus)
    questions = load_questions(args.questions)

    nodes_by_technique = build_nodes(
        documents,
        parsers,
    )

    indexes = build_indexes(
        nodes_by_technique,
        embed_model,
    )

    runs = []

    for technique, index in indexes.items():
        for question_record in questions:
            run = retrieve_for_question(
                technique=technique,
                index=index,
                question_record=question_record,
                embed_model=embed_model,
                top_k=args.top_k,
            )

            runs.append(run)

    stats = chunk_statistics(
        nodes_by_technique
    )

    write_outputs(
        output_directory=args.output_directory,
        runs=runs,
        chunk_stats=stats,
        top_k=args.top_k,
    )

    print("\nGraded retrieval comparison completed.")


if __name__ == "__main__":
    main()