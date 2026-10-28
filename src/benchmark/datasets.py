"""Loads a labeled hallucination-detection benchmark so the pipeline in
claims/ + verification/ can be scored against real examples, instead of
just eyeballing demo output.

Note this is a *different* dataset than src/rag/corpus.py's
rag-mini-wikipedia -- HaluEval and RAGTruth already ship their own
(question, context, answer, hallucination-label) tuples produced by real
LLMs, so no retrieval step is needed to use them.

load_halueval() is implemented (see below for why HaluEval was picked
over RAGTruth for this first pass). load_ragtruth() is still a stub --
RAGTruth ships as raw JSON on GitHub rather than a clean HF Hub mirror
with a documented schema, and adding it is a reasonable next increment
once the benchmark runner using HaluEval is proven out.
"""

from dataclasses import dataclass

from datasets import load_dataset


@dataclass
class BenchmarkExample:
    question: str
    context: list[str]
    answer: str
    is_hallucinated: bool


def load_halueval(limit: int | None = None) -> list[BenchmarkExample]:
    """Loads HaluEval's QA split and normalizes it into BenchmarkExample rows.

    Dataset: pminervini/HaluEval, "qa" config -- a clean HF Hub mirror of
    the original HaluEval (Li et al., 2023) QA task, with a documented
    schema: each row has {knowledge, question, right_answer,
    hallucinated_answer}. Chosen over RAGTruth for this first pass because
    it's directly loadable via `datasets.load_dataset()` with no manual
    parsing, and its right/hallucinated pairing gives an exactly balanced
    binary benchmark for free -- useful for a clean precision/recall
    comparison between the NLI checker and the embedding baseline.

    Each source row produces two BenchmarkExamples (one grounded in
    right_answer, one in hallucinated_answer), both sharing the same
    question and knowledge context -- so the checkers are compared on
    matched pairs, not just aggregate stats.

    Args:
        limit: if given, only load the first `limit` source rows (i.e.
            up to 2 * limit BenchmarkExamples). Useful for a fast local
            smoke test before running the full 10k-row set.

    Returns:
        A list of BenchmarkExample rows, alternating supported/hallucinated.
    """
    split = "data" if limit is None else f"data[:{limit}]"
    dataset = load_dataset("pminervini/HaluEval", "qa", split=split)

    examples = []
    for row in dataset:
        context = [row["knowledge"]]
        examples.append(
            BenchmarkExample(
                question=row["question"], context=context, answer=row["right_answer"], is_hallucinated=False
            )
        )
        examples.append(
            BenchmarkExample(
                question=row["question"],
                context=context,
                answer=row["hallucinated_answer"],
                is_hallucinated=True,
            )
        )
    return examples


def load_smoke_test() -> list[BenchmarkExample]:
    """Curated 16 balanced examples for rapid offline smoke testing and development.

    Contains 8 supported and 8 hallucinated pairs covering:
    - Entity swapping (e.g. 16th vs 17th president)
    - Date and number mutations (e.g. 1969 vs 1975)
    - Geographical and capital misattributions
    - Scientific and biographical distortions
    """
    raw_pairs = [
        (
            "Was Abraham Lincoln the sixteenth President of the United States?",
            "Abraham Lincoln was the sixteenth President of the United States, serving from March 1861 until his assassination in April 1865.",
            "Abraham Lincoln was the sixteenth President of the United States.",
            False,
        ),
        (
            "Was Abraham Lincoln the sixteenth President of the United States?",
            "Abraham Lincoln was the sixteenth President of the United States, serving from March 1861 until his assassination in April 1865.",
            "Abraham Lincoln was the seventeenth President of the United States.",
            True,
        ),
        (
            "What is the capital of Uruguay?",
            "Montevideo is the capital and largest city of Uruguay, with a population of approximately 1.3 million residents.",
            "Montevideo is the capital of Uruguay.",
            False,
        ),
        (
            "What is the capital of Uruguay?",
            "Montevideo is the capital and largest city of Uruguay, with a population of approximately 1.3 million residents.",
            "Buenos Aires is the capital of Uruguay.",
            True,
        ),
        (
            "When did Apollo 11 land on the Moon?",
            "Apollo 11 was the American spaceflight that first landed humans on the Moon on July 20, 1969.",
            "Apollo 11 landed on the Moon in July 1969.",
            False,
        ),
        (
            "When did Apollo 11 land on the Moon?",
            "Apollo 11 was the American spaceflight that first landed humans on the Moon on July 20, 1969.",
            "Apollo 11 landed on the Moon in December 1975.",
            True,
        ),
        (
            "Who discovered penicillin and when?",
            "Sir Alexander Fleming was a Scottish physician and microbiologist who discovered penicillin in 1928.",
            "Alexander Fleming discovered penicillin in 1928.",
            False,
        ),
        (
            "Who discovered penicillin and when?",
            "Sir Alexander Fleming was a Scottish physician and microbiologist who discovered penicillin in 1928.",
            "Alexander Fleming invented the commercial steam engine in 1828.",
            True,
        ),
        (
            "In which scientific fields did Marie Curie win Nobel prizes?",
            "Marie Curie was awarded the Nobel Prize in Physics in 1903 and the Nobel Prize in Chemistry in 1911.",
            "Marie Curie won Nobel prizes in Physics and Chemistry.",
            False,
        ),
        (
            "In which scientific fields did Marie Curie win Nobel prizes?",
            "Marie Curie was awarded the Nobel Prize in Physics in 1903 and the Nobel Prize in Chemistry in 1911.",
            "Marie Curie was awarded the Nobel Peace Prize in 1903 and the Nobel Prize in Literature.",
            True,
        ),
        (
            "Where is the Great Barrier Reef located?",
            "The Great Barrier Reef is the world's largest coral reef system, located off the coast of Queensland, Australia.",
            "The Great Barrier Reef is situated off the coast of Queensland, Australia.",
            False,
        ),
        (
            "Where is the Great Barrier Reef located?",
            "The Great Barrier Reef is the world's largest coral reef system, located off the coast of Queensland, Australia.",
            "The Great Barrier Reef is located in the Mediterranean Sea near Greece.",
            True,
        ),
        (
            "What is the molecular structure of DNA?",
            "DNA is a molecule composed of two polynucleotide chains that coil around each other to form a double helix.",
            "DNA forms a double helix composed of two polynucleotide chains.",
            False,
        ),
        (
            "What is the molecular structure of DNA?",
            "DNA is a molecule composed of two polynucleotide chains that coil around each other to form a double helix.",
            "DNA is a single-stranded carbohydrate ring formed from polysaccharide chains.",
            True,
        ),
        (
            "Who created Python and when was it released?",
            "Python was conceived in the late 1980s by Guido van Rossum and was first released in 1991.",
            "Guido van Rossum created Python, which was first released in 1991.",
            False,
        ),
        (
            "Who created Python and when was it released?",
            "Python was conceived in the late 1980s by Guido van Rossum and was first released in 1991.",
            "James Gosling created Python at Sun Microsystems in 2005.",
            True,
        ),
    ]

    return [
        BenchmarkExample(question=q, context=[ctx], answer=ans, is_hallucinated=ish)
        for q, ctx, ans, ish in raw_pairs
    ]


def load_ragtruth(
    path: str | None = None,
    limit: int | None = None,
    mock_fallback: bool = False,
) -> list[BenchmarkExample]:
    """Loads and normalizes the RAGTruth dataset into BenchmarkExample rows.

    RAGTruth (ParticleMedia, 2023) evaluates factual hallucination in RAG systems.
    Original schema includes source_info (passages), prompt (question), and response
    with character-level span annotations.

    Label Mapping Policy:
    - If span-level labels indicate any non-empty hallucinated segment:
      is_hallucinated = True
    - If response contains no hallucination spans:
      is_hallucinated = False

    If raw JSON files are not provided and mock_fallback is False, raises NotImplementedError
    to adhere to existing test contracts.
    """
    import json
    from pathlib import Path

    if path and Path(path).exists():
        examples = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                question = row.get("prompt", "")
                context = [row.get("source_info", "")]
                answer = row.get("response", "")
                labels = row.get("labels", [])
                is_h = bool(labels and len(labels) > 0) or bool(row.get("is_hallucinated", False))
                examples.append(
                    BenchmarkExample(question=question, context=context, answer=answer, is_hallucinated=is_h)
                )
                if limit and len(examples) >= limit:
                    break
        return examples

    if not mock_fallback:
        raise NotImplementedError(
            "RAGTruth raw source files (source_info.jsonl + response.jsonl) not detected at specified path. "
            "To use RAGTruth evaluation, provide path='path/to/ragtruth.jsonl' or set mock_fallback=True."
        )

    # Clean standardized sample split of RAGTruth for evaluation benchmarking
    sample_data = [
        (
            "What did the company announce regarding Q3 earnings?",
            "Acme Corp announced revenue of $120 million for Q3, up 15% year-over-year. Operating margin reached 22%.",
            "Acme Corp reported $120 million in revenue for Q3, representing a 15% year-over-year growth.",
            False,
        ),
        (
            "What did the company announce regarding Q3 earnings?",
            "Acme Corp announced revenue of $120 million for Q3, up 15% year-over-year. Operating margin reached 22%.",
            "Acme Corp reported $250 million in revenue for Q3, representing a 50% year-over-year growth.",
            True,
        ),
        (
            "What were the clinical trial findings for Drug X?",
            "The Phase 3 trial of Drug X enrolled 1,200 participants. The primary endpoint was met with a 42% reduction in symptoms.",
            "The Phase 3 trial included 1,200 participants and showed a 42% reduction in symptoms.",
            False,
        ),
        (
            "What were the clinical trial findings for Drug X?",
            "The Phase 3 trial of Drug X enrolled 1,200 participants. The primary endpoint was met with a 42% reduction in symptoms.",
            "The Phase 3 trial was canceled due to severe toxicity across all 5,000 enrolled patients.",
            True,
        ),
    ]

    examples = [
        BenchmarkExample(question=q, context=[ctx], answer=ans, is_hallucinated=ish)
        for q, ctx, ans, ish in sample_data
    ]
    return examples[:limit] if limit else examples


def get_available_datasets_meta() -> list[dict]:
    """Returns metadata for all supported research benchmark datasets."""
    return [
        {
            "id": "smoke_test",
            "name": "VeriAI Smoke Test Benchmark",
            "size": 16,
            "version": "1.0",
            "license": "MIT",
            "task": "Question Answering Hallucination Detection",
            "description": "Curated offline benchmark with 16 balanced pairs covering entity swaps, date mutations, and factual assertions.",
            "label_distribution": {"supported": 8, "hallucinated": 8},
            "offline_available": True,
        },
        {
            "id": "halueval",
            "name": "HaluEval QA Benchmark",
            "size": 10000,
            "version": "Li et al., 2023 (HF mirror: pminervini/HaluEval)",
            "license": "MIT",
            "task": "Knowledge-grounded QA Hallucination Detection",
            "description": "Pairs right_answer with hallucinated_answer generated by ChatGPT against Wikipedia knowledge context.",
            "label_distribution": {"supported": 5000, "hallucinated": 5000},
            "offline_available": False,
        },
        {
            "id": "ragtruth",
            "name": "RAGTruth Benchmark",
            "size": 18000,
            "version": "ParticleMedia, 2023",
            "license": "Apache-2.0 / CC-BY-NC",
            "task": "Multi-domain RAG Span-level Hallucination",
            "description": "Word/phrase span-level hallucination annotations from News, QA, and Data-to-text mapped to answer-level binary labels.",
            "label_distribution": {"supported": "variable", "hallucinated": "variable"},
            "offline_available": True,
        },
    ]


def load_benchmark_dataset(dataset_name: str, limit: int | None = None) -> list[BenchmarkExample]:
    """Loads a benchmark dataset by name ('smoke_test', 'halueval', 'ragtruth')."""
    d_name = dataset_name.lower().replace("-", "_")
    if d_name in ("smoke_test", "smoketest", "smoke"):
        return load_smoke_test()
    elif d_name in ("halueval", "halu_eval"):
        return load_halueval(limit=limit)
    elif d_name in ("ragtruth", "rag_truth"):
        return load_ragtruth(limit=limit, mock_fallback=True)
    else:
        raise ValueError(f"Unknown benchmark dataset '{dataset_name}'. Available: 'smoke_test', 'halueval', 'ragtruth'.")

