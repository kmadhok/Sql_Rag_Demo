# 🧪 Complete API Testing Guide with cURL Commands

## 🚀 Getting Started

**Backend URL:** `http://localhost:8001`
**Important**: Make sure the backend is running before testing:
```bash
cd backend
python app.py
```

## 📋 Table of Contents

1. [Health & System Check](#health--system-check)
2. [Query Search API](#query-search-api) ⭐ *(Main Feature)*
3. [Chat API](#chat-api)
4. [Data API](#data-api) 
5. [SQL API](#sql-api)
6. [Advanced Testing](#advanced-testing)

---

## 🏥 Health & System Check

### 1. Health Check
```bash
curl -X GET http://localhost:8001/health | jq
```
**Expected Response:**
```json
{
  "status": "healthy",
  "service": "RAG SQL Service",
  "version": "1.0.0"
}
```

### 2. Service Info
```bash
curl -X GET http://localhost:8000/ | grep -A 5 "<h1>"
```

### 3. API Documentation
```bash
# Open in browser
open http://localhost:8001/docs
```

---

## 🎯 Query Search API ⭐ *(Main Feature)*

### 📝 **1. Generate SQL from Question**
```bash
curl -X POST http://localhost:8000/api/query-search/search \n  -H "Content-Type: application/json" \n  -d '{
    "question": "Show me the most expensive products",
    "k": 5,
    "use_gemini": true,
    "schema_injection": true,
    "sql_validation": true
  }' | jq
```

### 🔍 **2. Different Question Examples**

```bash
# Count users by gender
curl -X POST http://localhost:8000/api/query-search/search \n  -H "Content-Type: application/json" \n  -d '{
    "question": "Count users by gender and show the percentages",
    "k": 3,
    "use_gemini": true,
    "schema_injection": true,
    "sql_validation": true
  }' | jq
```

```bash
# Join operations
curl -X POST http://localhost:8000/api/query-search/search \n  -H "Content-Type: application/json" \n  -d '{
    "question": "Find customers with the most orders including their names and order counts",
    "k": 4,
    "use_gemini": true,
    "schema_injection": true,
    "sql_validation": true
  }' | jq
```

```bash
# Complex analytics
curl -X POST http://localhost:8000/api/query-search/search \n  -H "Content-Type: application/json" \n  -d '{
    "question": "What is the average order value per month for the last 6 months?",
    "k": 6,
    "use_gemini": true,
    "schema_injection": true,
    "sql_validation": true
  }' | jq
```

### 💾 **3. Execute SQL on BigQuery**

**⚠️ WARNING: This runs on real BigQuery and may incur costs!**

**Dry Run (Recommended First):**
```bash
curl -X POST http://localhost:8000/api/query-search/execute \n  -H "Content-Type: application/json" \n  -d '{
    "sql": "SELECT name, category, retail_price FROM `bigquery-public-data.thelook_ecommerce.products` ORDER BY retail_price DESC LIMIT 5",
    "dry_run": true
  }' | jq
```

**Real Execution (Costs Money!):**
```bash
curl -X POST http://localhost:8000/api/query-search/execute \n  -H "Content-Type: application/json" \n  -d '{
    "sql": "SELECT name, category, retail_price FROM `bigquery-public-data.thelook_ecommerce.products` ORDER BY retail_price DESC LIMIT 5",
    "dry_run": false
  }' | jq
```

### 🔄 **4. Complete Pipeline Test**

One-liner to generate and execute (dry run):
```bash
curl -X POST http://localhost:8000/api/query-search/search -H "Content-Type: application/json" -d '{"question": "Show the top 5 most expensive products", "k": 3, "use_gemini": true, "schema_injection": true, "sql_validation": true}' | jq -r '.sql_query' | xargs -I {} curl -X POST http://localhost:8000/api/query-search/execute -H "Content-Type: application/json" -d '{"sql": "{}", "dry_run": true}' | jq
```

---

## 💬 Chat API

### 🆕 **1. Create Chat Session**
```bash
curl -X POST http://localhost:8000/api/chat/sessions \n  -H "Content-Type: application/json" \n  -d '{
    "user_id": "test_user_123"
  }' | jq
```

### 💭 **2. Send Chat Message**
```bash
# Replace {session_id} with actual session ID from previous call
curl -X POST http://localhost:8000/api/chat/ \n  -H "Content-Type: application/json" \n  -d '{
    "session_id": "your_session_id_here",
    "message": "Write a SQL query to find users who placed the most orders",
    "agent_type": "create"
  }' | jq
```

### 📚 **3. Get Session Messages**
```bash
curl -X GET http://localhost:8000/api/chat/sessions/{session_id}/messages | jq
```

### 👥 **4. Get User Sessions**
```bash
curl -X GET http://localhost:8000/api/chat/sessions/user_123 | jq
```

---

## 🗂️ Data API

### 🏗️ **1. Get Database Schema**
```bash
curl -X GET http://localhost:8000/api/schema | jq
```

### 📊 **2. Get Tables List**
```bash
curl -X GET http://localhost:8000/api/tables | jq
```

### 🔍 **3. Get Query Catalog**
```bash
curl -X GET "http://localhost:8000/api/queries?limit=10&offset=0" | jq
```

---

## 🔗 SQL API

### 💾 **1. Execute SQL (Alternative Endpoint)**
```bash
curl -X POST http://localhost:8000/api/sql/execute \n  -H "Content-Type: application/json" \n  -d '{
    "sql": "SELECT COUNT(*) as user_count FROM `bigquery-public-data.thelook_ecommerce.users`",
    "dry_run": true
  }' | jq
```

### ✅ **2. Validate SQL Only**
```bash
curl -X GET "http://localhost:8000/api/sql/validate?sql=SELECT+name+FROM+users+LIMIT+5" | jq
```

### 📜 **3. Get SQL Execution History**
```bash
curl -X GET "http://localhost:8000/api/sql/history?limit=5" | jq
```

---

## 🔬 Advanced Testing

### 📊 **Performance Testing**

```bash
# Time the query search API
time curl -X POST http://localhost:8000/api/query-search/search -H "Content-Type: application/json" -d '{"question": "Show expensive products", "k": 3, "use_gemini": true, "schema_injection": true, "sql_validation": true}' -o /dev/null -s
```

### 🧪 **Batch Testing Script**

```bash
#!/bin/bash
# Test multiple questions

questions=(
  "Show me the most expensive products"
  "Count users by gender"
  "Find customers with the most orders"
  "What is the average order value?"
  "Show products with low inventory"
)

for question in "${questions[@]}"; do
  echo "Testing: $question"
  curl -X POST http://localhost:8000/api/query-search/search \n    -H "Content-Type: application/json" \n    -d "{"question": "$question", "k": 3, "use_gemini": true, "schema_injection": true, "sql_validation": true}" \n    -o response.json -s
  
  if jq -e '.sql_query' response.json > /dev/null; then
    echo "✅ SQL Generated: $(jq -r '.sql_query' response.json)"
  else
    echo "❌ Failed to generate SQL"
  fi
  echo "---"
done
```

### 🚨 **Error Testing**

```bash
# Test with dangerous SQL
curl -X POST http://localhost:8000/api/query-search/execute \n  -H "Content-Type: application/json" \n  -d '{
    "sql": "DROP TABLE users",
    "dry_run": false
  }' | jq

# Test with invalid question
curl -X POST http://localhost:8000/api/query-search/search \n  -H "Content-Type: application/json" \n  -d '{
    "question": "",
    "k": 3,
    "use_gemini": true,
    "schema_injection": true,
    "sql_validation": true
  }' | jq
```

### 📝 **Pretty Print Responses**

Install `jq` for pretty JSON formatting:
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq
```

Then add `| jq` to any curl command pretty-print the JSON response.

---

## 🎯 Quick Test Recommendations

### **For Immediate Testing:**

1. **Health Check:** 
   ```bash
   curl -X GET http://localhost:8001/health | jq
   ```

2. **Simple Query Search:**
   ```bash
   curl -X POST http://localhost:8000/api/query-search/search \n     -H "Content-Type: application/json" \n     -d '{"question": "Show me 5 products", "k": 3, "use_gemini": true, "schema_injection": true, "sql_validation": true}' | jq
   ```

3. **Dry Run Execution:**
   ```bash
   curl -X POST http://localhost:8000/api/query-search/execute \n     -H "Content-Type: application/json" \n     -d '{"sql": "SELECT name, retail_price FROM `bigquery-public-data.thelook_ecommerce.products` LIMIT 3", "dry_run": true}' | jq
   ```

---

## 🐛 Troubleshooting

### **Common Issues:**

- **Connection refused**: Backend not running
- **500 errors**: Check backend logs
- **JSON errors**: Request body malformed
- **CORS errors**: Origin not allowed

### **Debug Commands:**

```bash
# Check if backend is running
curl -I http://localhost:8001/health

# Verbose curl request
curl -v -X POST http://localhost:8000/api/query-search/search \n  -H "Content-Type: application/json" \n  -d '{"question": "test"}' 2>&1 | grep -E "^<|^[^<]"

# Headers only
curl -I http://localhost:8000/api/query-search/search
```

Happy testing! 🚀 Remember that SQL execution against BigQuery costs money, so use `dry_run: true` for testing! 💰