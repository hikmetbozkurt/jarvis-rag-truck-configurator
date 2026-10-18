import re

from rank_bm25 import BM25Okapi

from jarvis.domain.knowledge import KnowledgeDocument, ScoredDocument

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*")
_STOP_WORDS = frozenset(
    {"a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for", "from", "has", "have", "how"}
    | {"i", "in", "is", "it", "me", "my", "of", "on", "or", "the", "this", "to", "what", "which", "with"}
    | {"you", "your"}
)


def tokenize_for_keyword_search(text: str) -> list[str]:
    tokens: list[str] = []
    for token in _TOKEN_PATTERN.findall(text.lower()):
        if token in _STOP_WORDS:
            continue
        tokens.append(token)
        if "-" in token:
            tokens.append(token.replace("-", ""))
    return tokens


class BM25KeywordIndex:
    def __init__(self, documents: list[KnowledgeDocument]) -> None:
        self._documents = documents
        tokenized_corpus = [tokenize_for_keyword_search(document.searchable_text) for document in documents]
        self._bm25 = BM25Okapi(tokenized_corpus) if documents else None

    @property
    def document_count(self) -> int:
        return len(self._documents)

    def search_by_keywords(self, query: str, limit: int) -> list[ScoredDocument]:
        query_tokens = tokenize_for_keyword_search(query)
        if self._bm25 is None or not query_tokens:
            return []

        document_scores = self._bm25.get_scores(query_tokens)
        ranked_indexes = sorted(range(len(document_scores)), key=lambda index: -document_scores[index])
        matching_indexes = [index for index in ranked_indexes[:limit] if document_scores[index] > 0]
        return [
            ScoredDocument(
                document=self._documents[index], score=round(float(document_scores[index]), 6), rank=rank
            )
            for rank, index in enumerate(matching_indexes, start=1)
        ]
