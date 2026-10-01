import csv
import json
import re
import time
import urllib.request
from pathlib import Path

import faiss
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = ROOT / "data" / "hw04" / "corpus"
QUESTIONS_FILE = ROOT / "data" / "hw04" / "questions.json"
RAW_DIR = ROOT / "reports" / "hw04" / "raw"

MODEL_NAME = "qwen3:1.7b"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3
REFUSAL = (
    "I cannot answer this question from the provided documents"
)


def load_text(path):
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    return path.read_text(
        encoding="utf-8",
        errors="ignore"
    )


def create_chunks(text, source):
    text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    start = 0
    number = 1

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk_text = text[start:end].strip()

        if chunk_text:
            chunks.append(
                {
                    "source": source,
                    "chunk_id": f"{source}-chunk-{number}",
                    "text": chunk_text
                }
            )
            number += 1

        if end == len(text):
            break

        start = end - CHUNK_OVERLAP

    return chunks


def load_corpus():
    chunks = []

    for path in sorted(CORPUS_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in {
            ".pdf",
            ".txt"
        }:
            text = load_text(path)
            document_chunks = create_chunks(text, path.name)
            chunks.extend(document_chunks)

            print(
                f"Loaded {path.name}: "
                f"{len(document_chunks)} chunks"
            )

    return chunks


def build_index(chunks, embedding_model):
    texts = [chunk["text"] for chunk in chunks]

    embeddings = embedding_model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True
    ).astype("float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    return index


def retrieve(
    question,
    k,
    chunks,
    index,
    embedding_model
):
    query = embedding_model.encode(
        [question],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype("float32")

    scores, indices = index.search(query, k)
    results = []

    for rank, (score, index_number) in enumerate(
        zip(scores[0], indices[0]),
        start=1
    ):
        chunk = chunks[int(index_number)]

        results.append(
            {
                "rank": rank,
                "source": chunk["source"],
                "chunk_id": chunk["chunk_id"],
                "score": round(float(score), 6),
                "text": chunk["text"]
            }
        )

    return results


def print_retrieval(question_id, results):
    print(f"\n--- {question_id}: retrieved chunks ---")

    for result in results:
        print(
            f"Rank {result['rank']} | "
            f"Source: {result['source']} | "
            f"Chunk: {result['chunk_id']} | "
            f"Score: {result['score']}"
        )
        print(result["text"])
        print()


def context_engineer(results):
    selected = []
    seen_text = set()

    for result in results:
        normalized = re.sub(
            r"\W+",
            " ",
            result["text"].lower()
        ).strip()

        signature = normalized[:250]

        if result["score"] < 0.30:
            continue

        if signature in seen_text:
            continue

        seen_text.add(signature)
        selected.append(result)

    return selected[:3]


def build_context(results):
    sections = []

    for number, result in enumerate(results, start=1):
        sections.append(
            f"[Source {number}: {result['source']}; "
            f"chunk_id={result['chunk_id']}]\n"
            f"{result['text']}"
        )

    return "\n\n".join(sections)


def call_ollama(prompt):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.0,
            "num_ctx": 4096,
            "num_predict": 180,
            "seed": 2562
        }
    }

    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(
        request,
        timeout=600
    ) as response:
        data = json.loads(
            response.read().decode("utf-8")
        )

    return data["message"]["content"].strip()


def make_prompt(configuration, question, results):
    if configuration == "A":
        return (
            "Answer the following question concisely.\n\n"
            f"Question: {question}"
        )

    context = build_context(results)

    if configuration == "B":
        return (
            "Use the following retrieved text to answer the "
            "question.\n\n"
            f"{context}\n\n"
            f"Question: {question}"
        )

    return (
        "Answer only from the provided context.\n"
        "Cite supporting evidence using [Source 1], "
        "[Source 2], and so on.\n"
        "Do not use outside knowledge.\n"
        "If the evidence is insufficient, respond exactly:\n"
        f"{REFUSAL}\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}"
    )


def expected_keywords(question_id):
    mapping = {
        "Q1": ["five minutes"],
        "Q2": ["p1", "15 minutes"],
        "Q3": [],
        "Q4": [],
        "Q5": [],
        "Q6": []
    }

    return mapping[question_id]


def evaluate(question, configuration, answer, retrieval):
    expected_sources = set(question["expected_sources"])
    retrieved_sources = {
        result["source"]
        for result in retrieval
    }

    refusal_needed = question["id"] in {"Q5", "Q6"}
    refused = REFUSAL.lower() in answer.lower()

    keywords = expected_keywords(question["id"])

    if refusal_needed:
        correct_answer = refused
    elif keywords:
        correct_answer = all(
            keyword in answer.lower()
            for keyword in keywords
        )
    else:
        correct_answer = bool(answer.strip())

    if expected_sources:
        correct_retrieval = expected_sources.issubset(
            retrieved_sources
        )
    else:
        correct_retrieval = True

    cited = bool(
        re.search(r"\[Source \d+\]", answer)
    )

    grounded = (
        correct_answer
        and (
            refused
            if refusal_needed
            else (
                configuration == "C"
                and correct_retrieval
                and cited
            )
        )
    )

    format_compliance = (
        refused or cited
        if configuration == "C"
        else bool(answer.strip())
    )

    return {
        "correct_retrieval": correct_retrieval,
        "correct_answer": correct_answer,
        "grounded": grounded,
        "refused_when_needed": (
            refused if refusal_needed else True
        ),
        "format_compliance": format_compliance
    }


def save_csv(path, rows):
    if not rows:
        return

    with path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=rows[0].keys()
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    questions = json.loads(
        QUESTIONS_FILE.read_text(encoding="utf-8")
    )

    print("HW4 Grounded RAG Experiment")
    print("SEED: 2562")
    print("VERIFY_SEED: 262562")
    print(f"LLM: {MODEL_NAME}")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print(f"Chunk size: {CHUNK_SIZE}")
    print(f"Chunk overlap: {CHUNK_OVERLAP}")
    print(f"Default top-k: {TOP_K}")

    chunks = load_corpus()

    print(f"\nDocuments: {len(list(CORPUS_DIR.iterdir()))}")
    print(f"Total chunks: {len(chunks)}")

    embedding_model = SentenceTransformer(
        EMBEDDING_MODEL,
        device="cpu"
    )
    index = build_index(chunks, embedding_model)

    retrieval_output = []
    comparison_output = []
    evaluation_output = []

    for question in questions:
        retrieval = retrieve(
            question["question"],
            TOP_K,
            chunks,
            index,
            embedding_model
        )

        print_retrieval(question["id"], retrieval)

        retrieval_output.append(
            {
                "question_id": question["id"],
                "question": question["question"],
                "top_k": TOP_K,
                "results": retrieval
            }
        )

        configurations = {
            "A": [],
            "B": retrieval,
            "C": context_engineer(retrieval)
        }

        for configuration, context_results in (
            configurations.items()
        ):
            prompt = make_prompt(
                configuration,
                question["question"],
                context_results
            )

            started = time.perf_counter()
            answer = call_ollama(prompt)
            latency_ms = round(
                (time.perf_counter() - started) * 1000,
                3
            )

            print(
                f"\n{question['id']} "
                f"Configuration {configuration}"
            )
            print(answer)

            comparison_output.append(
                {
                    "question_id": question["id"],
                    "question_type": question["type"],
                    "configuration": configuration,
                    "answer": answer,
                    "latency_ms": latency_ms,
                    "retrieved_sources": "; ".join(
                        result["source"]
                        for result in context_results
                    )
                }
            )

            evaluation = evaluate(
                question,
                configuration,
                answer,
                context_results
            )

            evaluation_output.append(
                {
                    "question_id": question["id"],
                    "configuration": configuration,
                    **evaluation
                }
            )

    sweep_question = questions[1]
    sweep_output = []

    print("\n=== TOP-K SWEEP: Q2 ===")

    for k in [1, 3, 5]:
        retrieval = retrieve(
            sweep_question["question"],
            k,
            chunks,
            index,
            embedding_model
        )

        print_retrieval(
            f"{sweep_question['id']} k={k}",
            retrieval
        )

        engineered = context_engineer(retrieval)
        prompt = make_prompt(
            "C",
            sweep_question["question"],
            engineered
        )
        answer = call_ollama(prompt)

        print(f"Context-RAG answer at k={k}:")
        print(answer)

        sweep_output.append(
            {
                "question_id": sweep_question["id"],
                "k": k,
                "retrieved": retrieval,
                "selected_after_filtering": engineered,
                "answer": answer
            }
        )

    (RAW_DIR / "retrieved_chunks.json").write_text(
        json.dumps(
            retrieval_output,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    (RAW_DIR / "configuration_comparison.json").write_text(
        json.dumps(
            comparison_output,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    save_csv(
        RAW_DIR / "configuration_comparison.csv",
        comparison_output
    )

    (RAW_DIR / "k_sweep.json").write_text(
        json.dumps(
            sweep_output,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    (RAW_DIR / "rag_evaluation.json").write_text(
        json.dumps(
            evaluation_output,
            indent=2
        ),
        encoding="utf-8"
    )

    save_csv(
        RAW_DIR / "rag_evaluation.csv",
        evaluation_output
    )

    print("\nSaved required RAG outputs:")
    print("retrieved_chunks.json")
    print("configuration_comparison.json")
    print("configuration_comparison.csv")
    print("k_sweep.json")
    print("rag_evaluation.json")
    print("rag_evaluation.csv")


if __name__ == "__main__":
    main()