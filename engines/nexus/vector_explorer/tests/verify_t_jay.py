
import os
import unittest
from engines.nexus.vector_explorer.vector_store import VertexExplorerVectorStore
from engines.nexus.embedding import VertexEmbeddingAdapter

class TestHazePersistence(unittest.TestCase):
    
    def test_verify_t_jay_data(self):
        tenant_id = "t_jay"
        env = "dev"
        space = "haze-default"
        
        print(f"\n--- Verifying Data for {tenant_id} / {space} ---")
        
        store = VertexExplorerVectorStore()
        
        # We need a query vector. 
        # Ideally we query with "everything" or a generic embedding.
        # Let's simple embed "hello" to get a valid vector.
        embedder = VertexEmbeddingAdapter()
        vector = embedder.embed_text("hello").vector
        
        print(f"Querying store with limit=100...")
        hits = store.query(
            vector=vector,
            tenant_id=tenant_id,
            env=env,
            space=space,
            top_k=100
        )
        
        print(f"Result count: {len(hits)}")
        for i, hit in enumerate(hits[:5]):
            print(f"Hit {i}: ID={hit.id}, Score={hit.score}")
            
        if len(hits) == 0:
            print("FAILURE: No nodes returned from Vertex. Ingest pipeline silent failure suspect.")
        else:
            print(f"SUCCESS: Vertex Data exists ({len(hits)} hits).")
            
        # Verify Firestore (Corpus)
        print(f"\nVerifying Firestore Corpus for {tenant_id}...")
        try:
            from engines.nexus.vector_explorer.repository import FirestoreVectorCorpusRepository
            repo = FirestoreVectorCorpusRepository()
            items = list(repo.list_filtered(
                tenant_id=tenant_id,
                env=env,
                space=space,
                limit=10,
            ))
            print(f"Firestore result count: {len(items)}")
            if len(items) == 0:
                 print("WARNING: Firestore has 0 items! This explains why default scene is empty.")
            else:
                 print(f"SUCCESS: Firestore has data ({len(items)} items). ID[0]={items[0].id}")
        except Exception as e:
            print(f"Firestore check skipped/failed: {e}")
            
if __name__ == "__main__":
    unittest.main()
