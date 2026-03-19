import logging
import json
import time
from typing import List, Dict, Any
from app.core.redis import r, rk

logger = logging.getLogger(__name__)

class GraphDataService:
    """
    Graph Data Serialization (Phase 15).
    Extracts connectivity data for the Visual Graph Explorer.
    """

    async def get_cluster_data(self, risk_id: str, team_id: str) -> Dict[str, Any]:
        """
        Returns a JSON-serializable graph structure (nodes and edges)
        representing the fraud cluster associated with a specific risk decision.
        """
        # 1. Fetch the risk audit to find the primary identity
        # In a real system, we'd query the GraphService or RedisGraph here.
        # For the vision demo, we reconstruct it from the 'explain' context.
        raw_data = await r.get(f"explain:{risk_id}")
        if not raw_data:
            return {"nodes": [], "edges": [], "summary": "Cluster data expired or missing."}
            
        context = json.loads(raw_data)
        identities = context.get("identities", {})
        uid = context.get("uid", "unknown")
        
        # 2. Build a localized graph around this UID
        # We simulate finding 3-5 linked nodes
        nodes = [
            {"id": uid, "type": "USER", "label": f"User: {uid[:8]}", "risk": context.get("score", 0)},
            {"id": "cluster_node_1", "type": "IP", "label": f"IP: {identities.get('ip', 'N/A')}", "risk": 40},
            {"id": "cluster_node_2", "type": "ADDR", "label": "Shared Address", "risk": 60},
        ]
        
        edges = [
            {"source": uid, "target": "cluster_node_1", "type": "SHARED_IP"},
            {"source": uid, "target": "cluster_node_2", "type": "SHARED_ADDR"},
        ]
        
        # Add some historical high-risk nodes if applicable
        if context.get("score", 0) > 70:
            nodes.append({"id": "fraud_actor_X", "type": "USER_RISK", "label": "Known Fraudster", "risk": 100})
            edges.append({"source": "cluster_node_1", "target": "fraud_actor_X", "type": "SHARED_IP_LINK"})
            
        return {
            "risk_id": risk_id,
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "high_risk_count": sum(1 for n in nodes if float(n["risk"]) > 50),
                "generated_at": time.time()
            }
        }

graph_data_service = GraphDataService()
