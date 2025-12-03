# app.py
"""
FastAPI backend for Resource Allocation Graph (RAG) simulator.
Single-file implementation (in-memory). Suitable for development / local use.

Run:
    pip install fastapi uvicorn networkx
    uvicorn app:app --reload --port 8000

CORS is enabled for http://localhost:3000 (React dev server).
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from threading import Lock
import networkx as nx
import logging

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)


# -----------------------
# RAG Manager (thread-safe)
# -----------------------
class RAGManager:
    def __init__(self):
        self._lock = Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self.G = nx.DiGraph()
            self.pcount = 0
            self.rcount = 0

    # Node ops
    def add_process(self) -> str:
        with self._lock:
            self.pcount += 1
            node = f"P{self.pcount}"
            self.G.add_node(node, type="P")
            logger.info(f"Added process {node}")
            return node

    def add_resource(self) -> str:
        with self._lock:
            self.rcount += 1
            node = f"R{self.rcount}"
            self.G.add_node(node, type="R")
            logger.info(f"Added resource {node}")
            return node

    def list_nodes(self) -> Dict[str, List[str]]:
        with self._lock:
            ps = [n for n, d in self.G.nodes(data=True) if d.get("type") == "P"]
            rs = [n for n, d in self.G.nodes(data=True) if d.get("type") == "R"]
            return {"processes": sorted(ps), "resources": sorted(rs)}

    # Edge ops
    def add_request(self, process: str, resource: str) -> bool:
        with self._lock:
            if not self._valid_nodes(process, resource, "P", "R"):
                return False
            if self.G.has_edge(process, resource):
                return False
            self.G.add_edge(process, resource, type="request")
            logger.info(f"Request added: {process} -> {resource}")
            return True

    def add_allocation(self, resource: str, process: str) -> bool:
        with self._lock:
            # NOTE: params order expects resource, process to match edge R->P
            if resource not in self.G or process not in self.G:
                return False
            if self.G.nodes.get(resource, {}).get("type") != "R" or self.G.nodes.get(process, {}).get("type") != "P":
                return False
            # single-instance resource model: ensure resource not already allocated
            alloc_to = [dst for src, dst, ed in self.G.edges(data=True) if src == resource and ed.get("type") == "alloc"]
            if alloc_to:
                return False
            self.G.add_edge(resource, process, type="alloc")
            # remove corresponding request P->R if present
            if self.G.has_edge(process, resource) and self.G[process][resource].get("type") == "request":
                self.G.remove_edge(process, resource)
            logger.info(f"Allocation added: {resource} -> {process}")
            return True

    def release_allocation(self, resource: str) -> Optional[str]:
        with self._lock:
            allocs = [(src, dst, ed) for src, dst, ed in self.G.edges(data=True) if src == resource and ed.get("type") == "alloc"]
            if not allocs:
                return None
            dst = allocs[0][1]
            self.G.remove_edge(resource, dst)
            logger.info(f"Released allocation {resource} -> {dst}")
            return dst

    def auto_allocate(self) -> int:
        with self._lock:
            made = 0
            requests = [(u, v) for u, v, ed in self.G.edges(data=True) if ed.get("type") == "request"]
            # convert P->R into R->P when R is free
            for p, r in requests:
                alloc_to = [dst for src, dst, ed in self.G.edges(data=True) if src == r and ed.get("type") == "alloc"]
                if not alloc_to:
                    self.G.add_edge(r, p, type="alloc")
                    if self.G.has_edge(p, r):
                        self.G.remove_edge(p, r)
                    made += 1
                    logger.info(f"Auto-allocated {r} -> {p}")
            return made

    # Deadlock detection using Wait-For Graph (WFG)
    def detect_deadlocks(self) -> List[List[str]]:
        with self._lock:
            wg = nx.DiGraph()
            processes = [n for n, d in self.G.nodes(data=True) if d.get("type") == "P"]
            wg.add_nodes_from(processes)
            # for each request P->R, if R allocated to P2 then add P->P2 in WFG
            for p, r, ed in self.G.edges(data=True):
                if ed.get("type") != "request":
                    continue
                allocs = [dst for src, dst, ed2 in self.G.edges(data=True) if src == r and ed2.get("type") == "alloc"]
                for p2 in allocs:
                    wg.add_edge(p, p2)
            try:
                cycles = list(nx.simple_cycles(wg))
            except Exception:
                cycles = []
            return cycles

    def export_graph(self) -> Dict:
        with self._lock:
            nodes = [{"id": n, "type": d.get("type")} for n, d in self.G.nodes(data=True)]
            edges = [{"source": u, "target": v, "type": ed.get("type")} for u, v, ed in self.G.edges(data=True)]
            return {"nodes": nodes, "edges": edges}

    def _valid_nodes(self, p: str, r: str, ptype="P", rtype="R") -> bool:
        if p not in self.G or r not in self.G:
            return False
        if self.G.nodes[p].get("type") != ptype or self.G.nodes[r].get("type") != rtype:
            return False
        return True


# single global manager (in-memory)
manager = RAGManager()


# -----------------------
# Pydantic models (requests/responses)
# -----------------------
class AddEdgeReq(BaseModel):
    src: str
    dst: str


class NodeList(BaseModel):
    processes: List[str]
    resources: List[str]


class GraphSnapshot(BaseModel):
    nodes: List[Dict]
    edges: List[Dict]


class ReleaseResp(BaseModel):
    released_by: Optional[str]


# -----------------------
# FastAPI app & endpoints
# -----------------------
app = FastAPI(title="RAG Simulator API")

# Allow requests from any origin (suitable for public API deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/nodes", response_model=NodeList)
def list_nodes():
    return manager.list_nodes()


@app.post("/nodes/process")
def create_process():
    node = manager.add_process()
    return {"node": node}


@app.post("/nodes/resource")
def create_resource():
    node = manager.add_resource()
    return {"node": node}


@app.post("/edge/request")
def add_request(req: AddEdgeReq):
    ok = manager.add_request(req.src, req.dst)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid nodes or request already exists")
    return {"status": "ok"}


@app.post("/edge/alloc")
def add_alloc(req: AddEdgeReq):
    # Expecting req.src to be resource id and req.dst to be process id (R -> P)
    ok = manager.add_allocation(req.src, req.dst)
    if not ok:
        raise HTTPException(status_code=400, detail="Allocation failed (maybe resource busy or invalid nodes)")
    return {"status": "ok"}


@app.post("/alloc/release", response_model=ReleaseResp)
def release(req: AddEdgeReq):
    # Use req.src as resource id to release its allocation
    released = manager.release_allocation(req.src)
    return {"released_by": released}


@app.post("/auto_allocate")
def auto_alloc():
    made = manager.auto_allocate()
    return {"allocated": made}


@app.get("/deadlocks")
def deadlocks():
    cycles = manager.detect_deadlocks()
    return {"cycles": cycles}


@app.get("/graph", response_model=GraphSnapshot)
def get_graph():
    return manager.export_graph()


@app.post("/reset")
def reset():
    manager.reset()
    return {"status": "reset"}


    