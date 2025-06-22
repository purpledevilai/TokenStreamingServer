from Models import JSONDocument, User


def retrieve_and_cache_doc(document_id, context):
    # Check if document is cached
    memory_document = None
    if "memory_documents" in context and document_id in context["memory_documents"]:
        # Return cached document
        memory_document = context["memory_documents"][document_id]
    else:
        if "user_id" in context:
            user_id = context["user_id"]
            user = User.get_user(user_id)
            memory_document = JSONDocument.get_json_document_for_user(document_id, user)
        else:
            memory_document = JSONDocument.get_public_json_document(document_id)

        # Cache the document in context
        if "memory_documents" not in context:
            context["memory_documents"] = {}
        context["memory_documents"][document_id] = memory_document
    
    if not memory_document:
        raise Exception(f"Error: Memory document with ID {document_id} not found.")
    
    return memory_document