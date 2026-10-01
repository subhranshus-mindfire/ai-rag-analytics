def test_get_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert "vector_store" in data

def test_documents_lifecycle(client):
    # 1. Ingest
    ingest_res = client.post("/documents/ingest")
    assert ingest_res.status_code == 200
    assert ingest_res.json()["files_processed"] > 0

    # 2. List
    list_res = client.get("/documents")
    assert list_res.status_code == 200
    docs = list_res.json()["documents"]
    assert len(docs) > 0

    # 3. Delete specific document
    doc_to_delete = docs[0]["document_id"]
    del_res = client.delete(f"/documents/{doc_to_delete}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

def test_chat_sql_intent(client):
    response = client.post("/chat", json={
        "message": "Which are the top 5 customers by revenue?",
        "session_id": "test_session_sql"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "sql"
    assert data["sql_query"] is not None
    assert len(data["answer"]) > 0

def test_chat_rag_intent(client):
    response = client.post("/chat", json={
        "message": "What is the company leave policy?",
        "session_id": "test_session_rag"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "rag"
    assert len(data["answer"]) > 0
