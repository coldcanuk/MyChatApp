import chromadb

# Connect to ChromaDB
client = chromadb.HttpClient(host='localhost', port=8000)

# Get the mychat_threads collection
collection_name = "mychat_threads"
collection = client.get_collection(collection_name)

# Fetch all documents in the collection
all_documents = collection.get()

# Check if there are documents in the collection
if all_documents and 'ids' in all_documents:
    document_ids = all_documents['ids']

    if document_ids:
        # Delete all documents by their IDs
        collection.delete(ids=document_ids)
        print(f"Deleted {len(document_ids)} documents from the collection '{
              collection_name}'.")
    else:
        print(f"No documents found in the collection '{collection_name}'.")
else:
    print(f"No documents found or error fetching the collection '{
          collection_name}'.")
