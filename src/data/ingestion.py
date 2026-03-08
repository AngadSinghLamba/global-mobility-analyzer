import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

# Azure SDK
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchFieldDataType,
    SearchableField,
)
from azure.search.documents import SearchClient

logger = logging.getLogger(__name__)

class VisaDocumentIndexer:
    def __init__(self):
        load_dotenv()
        self.endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
        self.key = os.environ.get("AZURE_SEARCH_API_KEY")
        self.index_name = os.environ.get("AZURE_SEARCH_INDEX_NAME", "visa-regulations")
        
        if not self.endpoint or not self.key:
            logger.warning("Azure Search credentials not found in environment.")
            return

        self.credential = AzureKeyCredential(self.key)
        self.index_client = SearchIndexClient(endpoint=self.endpoint, credential=self.credential)
        self.search_client = SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.credential)

    def create_or_update_index(self):
        """Creates the Azure AI Search schema needed for Corrective RAG."""
        logger.info(f"Creating or updating index '{self.index_name}'...")
        
        fields = [
            # Unique ID for the chunk (e.g. document_name_chunk_001)
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            
            # Core searchable content
            SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
            
            # Metadata for routing and filtering
            SimpleField(name="target_country", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="source_url", type=SearchFieldDataType.String, filterable=True),
            
            # Recency and Authority metadata for conflict resolution (Grader rules)
            SimpleField(name="published_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SimpleField(name="authority_level", type=SearchFieldDataType.Int32, filterable=True, sortable=True), # 1: Law, 2: Gov Guide, 3: Third Party
            
            # Context window size estimation
            SimpleField(name="token_estimate", type=SearchFieldDataType.Int32)
        ]
        
        index = SearchIndex(name=self.index_name, fields=fields)
        
        try:
            self.index_client.create_or_update_index(index=index)
            logger.info("Index updated successfully.")
        except Exception as e:
            logger.error(f"Failed to update index: {e}")

    def upload_chunks(self, chunks: List[Dict[str, Any]]):
        """Uploads text chunks to Azure AI Search in batches."""
        if not chunks:
            return
            
        logger.info(f"Uploading {len(chunks)} chunks to {self.index_name}...")
        try:
            result = self.search_client.upload_documents(documents=chunks)
            success_count = sum(1 for r in result if r.succeeded)
            logger.info(f"Successfully uploaded {success_count}/{len(chunks)} documents.")
        except Exception as e:
            logger.error(f"Upload failed: {e}")

# Example dummy chunk for structural testing
DUMMY_CHUNKS = [
    {
        "id": "uk_skilled_worker_salary_chunk_01",
        "content": "The general salary threshold for a Skilled Worker visa is £38,700 per year.",
        "target_country": "UK",
        "source_url": "https://www.gov.uk/skilled-worker-visa",
        "published_date": "2024-04-04T00:00:00Z",
        "authority_level": 1,
        "token_estimate": 25
    }
]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Initializing Data Ops pipeline...")
    
    indexer = VisaDocumentIndexer()
    if indexer.endpoint:
        indexer.create_or_update_index()
        # Uncomment to test ingestion:
        # indexer.upload_chunks(DUMMY_CHUNKS)
    else:
        logger.info("Skipping execution because Azure configs are missing (which is expected right now).")
