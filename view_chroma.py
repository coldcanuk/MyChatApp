import streamlit as st
import chromadb
import json
from datetime import datetime

client = chromadb.HttpClient(host='localhost', port=8000)

st.title("ChromaDB Visualization and Query Interface")

# Fetch all available collections in ChromaDB
collections = client.list_collections()

# Display all collections
if collections:
    st.subheader("Available Collections")

    # List collections with a brief overview
    st.write("Here is a list of all available collections in ChromaDB:")
    for idx, col in enumerate(collections):
        st.write(f"{idx + 1}. Collection Name: {col.name}")

    # Allow user to select a collection from the dropdown
    collection_names = [col.name for col in collections]
    selected_collection = st.selectbox(
        "Select a Collection to Query", collection_names)

    # Get the selected collection
    collection = client.get_collection(selected_collection)

    # Fetch and display documents in the selected collection
    st.subheader(f"Documents in Collection: {selected_collection}")
    all_documents = collection.get()

    if all_documents['documents']:
        # Display structure of the first document
        st.subheader(f"Structure of the '{selected_collection}' Collection")
        first_document = all_documents['documents'][0]

        # Check if the document is JSON-like or plain text
        try:
            document_data = json.loads(first_document)  # Try to load as JSON
            st.write("Here is an overview of the document structure (field names):")
            for field in document_data.keys():
                st.write(f"- {field}")
        except json.JSONDecodeError:
            st.write("The document is stored as plain text.")

        # Display all documents
        st.subheader(f"Documents in the {selected_collection} Collection")

        for idx, doc in enumerate(all_documents['documents']):
            try:
                document_data = json.loads(doc)

                st.write(
                    f"Document {idx + 1}: Thread ID: {document_data['id']}")

                # Convert string timestamps to datetime objects with milliseconds
                created_time = datetime.strptime(
                    document_data['created'], "%Y-%m-%d %H:%M:%S.%f")
                last_updated_time = datetime.strptime(
                    document_data['last_updated'], "%Y-%m-%d %H:%M:%S.%f")

                st.write(f"Created at: {created_time}")
                st.write(f"Last updated at: {last_updated_time}")

                st.write("Messages in this thread:")
                for message in document_data['messages']:
                    message_time = datetime.strptime(
                        message['time_value'], "%Y-%m-%d %H:%M:%S.%f")
                    st.write(
                        f"- {message['role']} ({message['time_state']} at {message_time}): {message['content']}")

            except json.JSONDecodeError:
                st.write(f"Document {idx + 1}: {doc}")

        # Option to query the selected collection
        st.subheader(f"Query the {selected_collection} Collection")

        # Add specific, meaningful example queries
        st.write("Here are some example queries to get you started:")
        example_query1 = "What are the benefits of using ChromaDB?"
        example_query2 = "Explain vector databases in simple terms."
        st.write(f"1. {example_query1}")
        st.write(f"2. {example_query2}")

        # Provide a selectbox for users to choose an example query
        example_query = st.selectbox(
            "Or select an example query to fill the input:",
            [None, example_query1, example_query2]
        )

        # Allow users to enter their own query or select an example
        query = st.text_input("Enter your query:",
                              value=example_query if example_query else "")

        # Add a slider for adjusting the distance threshold
        st.write("Adjust the distance threshold for similarity:")
        distance_threshold = st.slider(
            "Distance Threshold (Lower values mean more similar results):",
            min_value=0.0,
            max_value=1.0,
            value=0.5,  # Default value
            step=0.05
        )

        st.write("Examples of Distance Threshold:")
        st.write("- **0.1**: Very strict, only returns highly relevant documents.")
        st.write(
            "- **0.5**: Moderate similarity, balance between precision and recall.")
        st.write(
            "- **0.9**: Loose similarity, returns less relevant docs but broadens search"
        )

        if query:
            # Execute the query with distance threshold
            results = collection.query(
                query_texts=[query], n_results=5, distance_threshold=distance_threshold)

            # Display results
            st.write("Query Results:")
            for i, result in enumerate(results['documents']):
                st.write(f"Result {i+1}: {result}")

    else:
        st.write(f"No documents found in collection '{selected_collection}'.")

else:
    st.write("No collections found in ChromaDB.")
