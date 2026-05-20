import os
import chromadb

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "chromadb_data")
_client = chromadb.PersistentClient(path=_DB_PATH)
_collection = None


def get_collection():
    global _collection
    if _collection is None:
        _collection = _client.get_or_create_collection("repair_guides")
    return _collection


def add_repair_guides(guides: list[dict]):
    collection = get_collection()
    for guide in guides:
        symptom_name = guide.get("symptom_name", "")
        description = guide.get("description", "")
        percentage = guide.get("percentage", "")
        guide_url = guide.get("guide_url", "")
        appliance_type = guide.get("appliance_type", "")

        doc_id = f"{appliance_type}_{symptom_name}".lower().replace(" ", "_")
        document = f"{symptom_name}: {description}"
        metadata = {
            "percentage": percentage,
            "guide_url": guide_url,
            "appliance_type": appliance_type,
            "symptom_name": symptom_name,
        }

        try:
            existing = collection.get(ids=[doc_id])
            if existing["ids"]:
                continue
            collection.add(ids=[doc_id], documents=[document], metadatas=[metadata])
        except Exception:
            pass


def search_repair_guides(query: str, appliance_type: str, n_results: int = 3) -> list[dict]:
    try:
        collection = get_collection()
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"appliance_type": appliance_type},
        )

        output = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) else {}
            doc = documents[i] if i < len(documents) else ""
            distance = distances[i] if i < len(distances) else None

            description = doc.split(": ", 1)[1] if ": " in doc else doc

            output.append({
                "symptom_name": meta.get("symptom_name", ""),
                "description": description,
                "percentage": meta.get("percentage", ""),
                "guide_url": meta.get("guide_url", ""),
                "appliance_type": meta.get("appliance_type", ""),
                "distance": distance,
            })

        return output
    except Exception:
        return []
