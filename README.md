# RAG Simulator API - Backend Documentation

## Overview

This is a FastAPI backend for a **Resource Allocation Graph (RAG) Simulator**. It provides endpoints to create processes and resources, manage allocations and requests, detect deadlocks, and visualize the graph state.

The system uses an **in-memory graph** managed by NetworkX, suitable for development and demonstration purposes.

---

## Base URL

- **Local Development**: `http://localhost:8000`
- **Production (Vercel)**: `https://your-deployment.vercel.app`

---

## API Endpoints

### 1. List All Nodes

**GET** `/nodes`

Returns all processes and resources in the system.

**Response:**
```json
{
  "processes": ["P1", "P2", "P3"],
  "resources": ["R1", "R2"]
}
```

**Frontend Example:**
```javascript
const response = await fetch(`${API_BASE_URL}/nodes`);
const data = await response.json();
console.log(data.processes); // ["P1", "P2", "P3"]
console.log(data.resources);  // ["R1", "R2"]
```

---

### 2. Create Process

**POST** `/nodes/process`

Creates a new process node. Process IDs are auto-generated (P1, P2, P3, ...).

**Request Body:** None

**Response:**
```json
{
  "node": "P1"
}
```

**Frontend Example:**
```javascript
const response = await fetch(`${API_BASE_URL}/nodes/process`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' }
});
const data = await response.json();
console.log(data.node); // "P1"
```

---

### 3. Create Resource

**POST** `/nodes/resource`

Creates a new resource node. Resource IDs are auto-generated (R1, R2, R3, ...).

**Request Body:** None

**Response:**
```json
{
  "node": "R1"
}
```

**Frontend Example:**
```javascript
const response = await fetch(`${API_BASE_URL}/nodes/resource`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' }
});
const data = await response.json();
console.log(data.node); // "R1"
```

---

### 4. Add Request Edge

**POST** `/edge/request`

Creates a request edge from a process to a resource (P → R).

**Request Body:**
```json
{
  "src": "P1",
  "dst": "R1"
}
```

**Response:**
```json
{
  "status": "ok"
}
```

**Error Response (400):**
```json
{
  "detail": "Invalid nodes or request already exists"
}
```

**Frontend Example:**
```javascript
const response = await fetch(`${API_BASE_URL}/edge/request`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    src: "P1",  // Process ID
    dst: "R1"   // Resource ID
  })
});
const data = await response.json();
```

---

### 5. Add Allocation Edge

**POST** `/edge/alloc`

Creates an allocation edge from a resource to a process (R → P). The resource must be free (not already allocated).

**Request Body:**
```json
{
  "src": "R1",
  "dst": "P1"
}
```

**Response:**
```json
{
  "status": "ok"
}
```

**Error Response (400):**
```json
{
  "detail": "Allocation failed (maybe resource busy or invalid nodes)"
}
```

**Frontend Example:**
```javascript
const response = await fetch(`${API_BASE_URL}/edge/alloc`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    src: "R1",  // Resource ID
    dst: "P1"   // Process ID
  })
});
const data = await response.json();
```

**Note:** When a resource is allocated to a process, any existing request edge (P → R) is automatically removed.

---

### 6. Release Allocation

**POST** `/alloc/release`

Releases the allocation from a resource, making it available again.

**Request Body:**
```json
{
  "src": "R1",
  "dst": ""
}
```

**Note:** Only the `src` field (resource ID) is used; `dst` can be any value.

**Response:**
```json
{
  "released_by": "P1"
}
```

If the resource wasn't allocated:
```json
{
  "released_by": null
}
```

**Frontend Example:**
```javascript
const response = await fetch(`${API_BASE_URL}/alloc/release`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    src: "R1",  // Resource ID to release
    dst: ""     // Ignored
  })
});
const data = await response.json();
console.log(data.released_by); // Process that was holding the resource
```

---

### 7. Auto-Allocate Resources

**POST** `/auto_allocate`

Automatically allocates all free resources to processes that have requested them.

**Request Body:** None

**Response:**
```json
{
  "allocated": 3
}
```

The `allocated` field indicates how many allocations were made.

**Frontend Example:**
```javascript
const response = await fetch(`${API_BASE_URL}/auto_allocate`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' }
});
const data = await response.json();
console.log(`${data.allocated} resources auto-allocated`);
```

---

### 8. Detect Deadlocks

**GET** `/deadlocks`

Detects deadlocks using a Wait-For Graph (WFG) algorithm. Returns all circular wait cycles.

**Response:**
```json
{
  "cycles": [
    ["P1", "P2", "P3"],
    ["P4", "P5"]
  ]
}
```

**Frontend Example:**
```javascript
const response = await fetch(`${API_BASE_URL}/deadlocks`);
const data = await response.json();
if (data.cycles.length > 0) {
  console.log("Deadlock detected!");
  data.cycles.forEach(cycle => {
    console.log("Cycle:", cycle.join(" → "));
  });
} else {
  console.log("No deadlocks detected");
}
```

---

### 9. Get Graph State

**GET** `/graph`

Returns the complete graph state with all nodes and edges.

**Response:**
```json
{
  "nodes": [
    { "id": "P1", "type": "P" },
    { "id": "P2", "type": "P" },
    { "id": "R1", "type": "R" }
  ],
  "edges": [
    { "source": "P1", "target": "R1", "type": "request" },
    { "source": "R1", "target": "P2", "type": "alloc" }
  ]
}
```

**Edge Types:**
- `"request"`: Process requesting a resource (P → R)
- `"alloc"`: Resource allocated to a process (R → P)

**Frontend Example:**
```javascript
const response = await fetch(`${API_BASE_URL}/graph`);
const data = await response.json();

// Separate processes and resources
const processes = data.nodes.filter(n => n.type === 'P');
const resources = data.nodes.filter(n => n.type === 'R');

// Separate edge types
const requests = data.edges.filter(e => e.type === 'request');
const allocations = data.edges.filter(e => e.type === 'alloc');
```

---

### 10. Reset Graph

**POST** `/reset`

Clears all nodes and edges, resetting the graph to its initial state.

**Request Body:** None

**Response:**
```json
{
  "status": "reset"
}
```

**Frontend Example:**
```javascript
const response = await fetch(`${API_BASE_URL}/reset`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' }
});
const data = await response.json();
console.log("Graph reset successfully");
```

---

## Complete Frontend Integration Example

```javascript
// Configuration
const API_BASE_URL = 'http://localhost:8000'; // Change for production

// Helper function for API calls
async function apiCall(endpoint, method = 'GET', body = null) {
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' }
  };
  if (body) {
    options.body = JSON.stringify(body);
  }
  const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'API request failed');
  }
  return await response.json();
}

// Example: Create a scenario with deadlock
async function createDeadlockScenario() {
  try {
    // Reset graph
    await apiCall('/reset', 'POST');
    
    // Create 2 processes and 2 resources
    const p1 = await apiCall('/nodes/process', 'POST');
    const p2 = await apiCall('/nodes/process', 'POST');
    const r1 = await apiCall('/nodes/resource', 'POST');
    const r2 = await apiCall('/nodes/resource', 'POST');
    
    console.log('Created:', p1.node, p2.node, r1.node, r2.node);
    
    // P1 holds R1, P2 holds R2
    await apiCall('/edge/alloc', 'POST', { src: r1.node, dst: p1.node });
    await apiCall('/edge/alloc', 'POST', { src: r2.node, dst: p2.node });
    
    // P1 requests R2, P2 requests R1 (creates circular wait)
    await apiCall('/edge/request', 'POST', { src: p1.node, dst: r2.node });
    await apiCall('/edge/request', 'POST', { src: p2.node, dst: r1.node });
    
    // Check for deadlock
    const deadlocks = await apiCall('/deadlocks');
    console.log('Deadlocks:', deadlocks.cycles);
    
    // Get full graph state
    const graph = await apiCall('/graph');
    console.log('Graph:', graph);
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Example: Visualize graph with React Flow or similar
async function visualizeGraph() {
  const graph = await apiCall('/graph');
  
  // Transform to React Flow format
  const reactFlowNodes = graph.nodes.map((node, index) => ({
    id: node.id,
    type: node.type === 'P' ? 'process' : 'resource',
    data: { label: node.id },
    position: { x: index * 150, y: node.type === 'P' ? 0 : 200 }
  }));
  
  const reactFlowEdges = graph.edges.map((edge, index) => ({
    id: `e${index}`,
    source: edge.source,
    target: edge.target,
    label: edge.type,
    animated: edge.type === 'request',
    style: { stroke: edge.type === 'alloc' ? 'green' : 'orange' }
  }));
  
  return { nodes: reactFlowNodes, edges: reactFlowEdges };
}
```

---

## Local Development Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

3. **Access the API:**
   - Base URL: `http://localhost:8000`
   - Interactive docs: `http://localhost:8000/docs`
   - Alternative docs: `http://localhost:8000/redoc`

---

## Deployment to Vercel

1. **Install Vercel CLI:**
   ```bash
   npm i -g vercel
   ```

2. **Deploy:**
   ```bash
   vercel deploy
   ```

3. **Update frontend with production URL:**
   ```javascript
   const API_BASE_URL = 'https://your-deployment.vercel.app';
   ```

---

## Important Notes

### Single-Instance Resources
Each resource can only be allocated to **one process** at a time. Attempting to allocate a busy resource will fail with a 400 error.

### Automatic Request Removal
When a resource is allocated to a process, any existing request edge (P → R) is automatically removed from the graph.

### In-Memory State
The current implementation uses in-memory storage. State will be lost when the server restarts or between serverless function invocations on Vercel. For production, consider integrating a database.

### Deadlock Detection Algorithm
The system uses a **Wait-For Graph (WFG)** approach:
1. For each request P → R, if R is allocated to P2, add edge P → P2 in the WFG
2. Detect cycles in the WFG using NetworkX's `simple_cycles` algorithm
3. Each cycle represents a deadlock

---

## LLM Integration Tips

When connecting a frontend to this backend, consider:

1. **Polling for updates**: Use `setInterval` to periodically call `/graph` and `/deadlocks`
2. **Error handling**: Always wrap API calls in try-catch blocks
3. **Visual differentiation**: Use different colors/styles for:
   - Processes (circles) vs Resources (squares)
   - Request edges (dashed/orange) vs Allocation edges (solid/green)
   - Deadlocked processes (highlight in red)
4. **User actions**: Provide buttons for all operations (create process/resource, add request/allocation, release, auto-allocate, detect deadlock, reset)

---

## License

This project is for educational purposes.
