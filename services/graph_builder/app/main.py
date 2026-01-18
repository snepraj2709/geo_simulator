"""
Knowledge Graph Builder FastAPI Application.

Provides REST API endpoints for graph building and querying.
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware

from shared.utils.logging import get_logger
from shared.db.neo4j_client import Neo4jClient
from shared.config import get_settings

from services.graph_builder.components.builder import GraphBuilder
from services.graph_builder.components.queries import QueryBuilder
from services.graph_builder.schemas import (
    GraphBuildRequest,
    GraphBuildResponse,
    BeliefMapRequest,
    BeliefMapResponse,
    CoMentionRequest,
    CoMentionResponse,
    ICPJourneyRequest,
    ICPJourneyResponse,
    SubstitutionPatternRequest,
    SubstitutionPatternResponse,
    BatchNodeCreate,
    BatchEdgeCreate,
    BatchOperationResult,
    IntentTypeEnum,
)

logger = get_logger(__name__)

# Global instances
_neo4j_client: Neo4jClient | None = None
_graph_builder: GraphBuilder | None = None
_query_builder: QueryBuilder | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global _neo4j_client, _graph_builder, _query_builder

    # Startup
    logger.info("Starting Knowledge Graph Builder service...")

    settings = get_settings()
    _neo4j_client = Neo4jClient(
        uri=settings.NEO4J_URI,
        username=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
    )

    _graph_builder = GraphBuilder(_neo4j_client)
    _query_builder = QueryBuilder(_neo4j_client)

    # Initialize graph constraints and base nodes
    await _graph_builder.initialize_graph()

    logger.info("Knowledge Graph Builder service started")

    yield

    # Shutdown
    logger.info("Shutting down Knowledge Graph Builder service...")
    if _neo4j_client:
        await _neo4j_client.close()
    logger.info("Knowledge Graph Builder service stopped")


app = FastAPI(
    title="Knowledge Graph Builder Service",
    description="Builds and queries the Neo4j knowledge graph for brand relationships, ICP concerns, and belief formations.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================================
# DEPENDENCIES
# =========================================================================


def get_graph_builder() -> GraphBuilder:
    """Get graph builder instance."""
    if _graph_builder is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _graph_builder


def get_query_builder() -> QueryBuilder:
    """Get query builder instance."""
    if _query_builder is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _query_builder


# =========================================================================
# HEALTH ENDPOINTS
# =========================================================================


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "graph-builder"}


@app.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    """Readiness check - verifies Neo4j connection."""
    if _neo4j_client is None:
        raise HTTPException(status_code=503, detail="Neo4j client not initialized")

    try:
        healthy = await _neo4j_client.health_check()
        if not healthy:
            raise HTTPException(status_code=503, detail="Neo4j connection unhealthy")
        return {"status": "ready", "neo4j": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Neo4j error: {str(e)}")


# =========================================================================
# GRAPH BUILDING ENDPOINTS
# =========================================================================


@app.post("/graph/build", response_model=GraphBuildResponse)
async def build_graph(
    request: GraphBuildRequest,
    simulation_data: dict[str, Any],
    builder: GraphBuilder = Depends(get_graph_builder),
) -> GraphBuildResponse:
    """
    Build graph from simulation data.

    Processes simulation run data and builds/updates the knowledge graph.
    """
    try:
        result = await builder.build_from_simulation(request, simulation_data)
        return result
    except Exception as e:
        logger.error(f"Graph build failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/graph/nodes", response_model=BatchOperationResult)
async def create_nodes(
    nodes: BatchNodeCreate,
    builder: GraphBuilder = Depends(get_graph_builder),
) -> BatchOperationResult:
    """Create nodes in batch."""
    try:
        result = await builder.create_nodes_batch(nodes)
        return result
    except Exception as e:
        logger.error(f"Batch node creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/graph/edges", response_model=BatchOperationResult)
async def create_edges(
    edges: BatchEdgeCreate,
    builder: GraphBuilder = Depends(get_graph_builder),
) -> BatchOperationResult:
    """Create edges in batch."""
    try:
        result = await builder.create_edges_batch(edges)
        return result
    except Exception as e:
        logger.error(f"Batch edge creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/graph/initialize")
async def initialize_graph(
    builder: GraphBuilder = Depends(get_graph_builder),
) -> dict[str, bool]:
    """Initialize graph with constraints and base nodes."""
    try:
        success = await builder.initialize_graph()
        return {"initialized": success}
    except Exception as e:
        logger.error(f"Graph initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# BELIEF MAP ENDPOINTS
# =========================================================================


@app.get("/websites/{website_id}/graph/belief-map")
async def get_belief_map(
    website_id: str,
    brand_id: str | None = Query(None, description="Filter by brand ID"),
    brand_name: str | None = Query(None, description="Filter by brand name"),
    icp_id: str | None = Query(None, description="Filter by ICP ID"),
    llm_provider: str | None = Query(None, description="Filter by LLM provider"),
    query: QueryBuilder = Depends(get_query_builder),
) -> dict[str, Any]:
    """
    Get LLM answer belief map data for visualization.

    Returns nodes and edges for belief map visualization.
    """
    if not brand_name and not brand_id:
        raise HTTPException(
            status_code=400,
            detail="Either brand_id or brand_name is required"
        )

    try:
        # Get belief map for the brand
        belief_data = await query.get_belief_map(
            brand_name=brand_name or brand_id,
            llm_provider=llm_provider,
        )

        # Format as graph visualization data
        nodes = [
            {
                "id": f"brand_{belief_data.brand_name}",
                "type": "brand",
                "name": belief_data.brand_name,
            }
        ]

        edges = []

        for belief in belief_data.beliefs:
            belief_node_id = f"belief_{belief['belief_type']}"
            nodes.append({
                "id": belief_node_id,
                "type": "belief",
                "name": belief["belief_type"],
            })
            edges.append({
                "source": f"brand_{belief_data.brand_name}",
                "target": belief_node_id,
                "type": "installs_belief",
                "weight": belief["count"],
                "confidence": belief["confidence"],
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "total_occurrences": belief_data.total_occurrences,
        }

    except Exception as e:
        logger.error(f"Error getting belief map: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/belief-map/{brand_name}", response_model=BeliefMapResponse)
async def get_brand_belief_map(
    brand_name: str,
    llm_provider: str | None = Query(None),
    intent_type: IntentTypeEnum | None = Query(None),
    query: QueryBuilder = Depends(get_query_builder),
) -> BeliefMapResponse:
    """Get belief map for a specific brand."""
    try:
        return await query.get_belief_map(
            brand_name=brand_name,
            llm_provider=llm_provider,
            intent_type=intent_type,
        )
    except Exception as e:
        logger.error(f"Error getting belief map: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/belief-comparison")
async def get_belief_comparison(
    brands: str = Query(..., description="Comma-separated brand names"),
    llm_provider: str | None = Query(None),
    query: QueryBuilder = Depends(get_query_builder),
) -> dict[str, Any]:
    """Compare belief maps across multiple brands."""
    try:
        brand_list = [b.strip() for b in brands.split(",")]
        return await query.get_belief_comparison(brand_list, llm_provider)
    except Exception as e:
        logger.error(f"Error comparing beliefs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# CO-MENTION ENDPOINTS
# =========================================================================


@app.get("/websites/{website_id}/graph/co-mentions")
async def get_co_mentions_graph(
    website_id: str,
    brand_name: str | None = Query(None, description="Center brand name"),
    llm_provider: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    query: QueryBuilder = Depends(get_query_builder),
) -> dict[str, Any]:
    """
    Get brand co-mention network.

    Returns nodes and edges for co-mention visualization.
    """
    try:
        if brand_name:
            co_mention_data = await query.get_co_mentions(
                brand_name=brand_name,
                limit=limit,
                llm_provider=llm_provider,
            )

            nodes = [
                {
                    "id": f"brand_{co_mention_data.brand_name}",
                    "name": co_mention_data.brand_name,
                    "is_center": True,
                }
            ]

            edges = []

            for co_mention in co_mention_data.co_mentions:
                node_id = f"brand_{co_mention['normalized_name']}"
                nodes.append({
                    "id": node_id,
                    "name": co_mention["brand_name"],
                    "mention_count": co_mention["count"],
                })
                edges.append({
                    "source": f"brand_{co_mention_data.brand_name}",
                    "target": node_id,
                    "co_mention_count": co_mention["count"],
                    "avg_position_delta": co_mention["avg_position_delta"],
                })

            return {"nodes": nodes, "edges": edges}

        # Return full network for website
        network = await query.get_co_mention_network(
            brand_name=brand_name or "",
            depth=2,
            min_count=1,
        )
        return network

    except Exception as e:
        logger.error(f"Error getting co-mentions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/co-mentions/{brand_name}", response_model=CoMentionResponse)
async def get_brand_co_mentions(
    brand_name: str,
    limit: int = Query(10, ge=1, le=100),
    llm_provider: str | None = Query(None),
    query: QueryBuilder = Depends(get_query_builder),
) -> CoMentionResponse:
    """Get co-mentions for a specific brand."""
    try:
        return await query.get_co_mentions(
            brand_name=brand_name,
            limit=limit,
            llm_provider=llm_provider,
        )
    except Exception as e:
        logger.error(f"Error getting co-mentions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# ICP JOURNEY ENDPOINTS
# =========================================================================


@app.get("/websites/{website_id}/graph/icp-journey")
async def get_icp_journey_graph(
    website_id: str,
    icp_id: str = Query(..., description="ICP UUID"),
    query: QueryBuilder = Depends(get_query_builder),
) -> dict[str, Any]:
    """
    Get ICP concern to brand recommendation paths.

    Returns journey data for visualization.
    """
    try:
        journey = await query.get_icp_journey(icp_id=icp_id, include_brands=True)

        # Format as paths for visualization
        paths = []

        for concern in journey.concerns:
            # Find intents triggered by this concern
            concern_intents = [
                i for i in journey.intents
                if i.get("id") is not None
            ]

            for intent in concern_intents:
                # Find brands ranked for this intent
                intent_brands = [
                    br for br in journey.brand_recommendations
                    if br.get("intent_id") == intent.get("id")
                ]

                paths.append({
                    "concern": concern["description"],
                    "triggers_intent": {
                        "type": intent.get("intent_type"),
                        "funnel_stage": intent.get("funnel_stage"),
                        "buying_signal": intent.get("buying_signal"),
                    },
                    "brands_ranked": [
                        {
                            "name": br["brand_name"],
                            "position": br["position"],
                            "presence": br["presence"],
                        }
                        for br in sorted(intent_brands, key=lambda x: x.get("position", 999))
                    ],
                })

        return {
            "icp": {
                "id": journey.icp_id,
                "name": journey.icp_name,
            },
            "paths": paths,
        }

    except Exception as e:
        logger.error(f"Error getting ICP journey: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/icp-journey/{icp_id}", response_model=ICPJourneyResponse)
async def get_icp_journey(
    icp_id: str,
    include_brands: bool = Query(True),
    query: QueryBuilder = Depends(get_query_builder),
) -> ICPJourneyResponse:
    """Get journey data for a specific ICP."""
    try:
        return await query.get_icp_journey(
            icp_id=icp_id,
            include_brands=include_brands,
        )
    except Exception as e:
        logger.error(f"Error getting ICP journey: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# SUBSTITUTION PATTERN ENDPOINTS
# =========================================================================


@app.get("/graph/substitutions/{brand_name}", response_model=SubstitutionPatternResponse)
async def get_substitution_patterns(
    brand_name: str,
    llm_provider: str | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    query: QueryBuilder = Depends(get_query_builder),
) -> SubstitutionPatternResponse:
    """Get substitution patterns for when a brand is ignored."""
    try:
        return await query.get_substitution_patterns(
            brand_name=brand_name,
            llm_provider=llm_provider,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Error getting substitutions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# COMPETITIVE ANALYSIS ENDPOINTS
# =========================================================================


@app.get("/graph/share-of-voice")
async def get_share_of_voice(
    brands: str = Query(..., description="Comma-separated brand names"),
    llm_provider: str | None = Query(None),
    query: QueryBuilder = Depends(get_query_builder),
) -> dict[str, Any]:
    """Get share of voice metrics for brands."""
    try:
        brand_list = [b.strip() for b in brands.split(",")]
        return await query.get_share_of_voice(brand_list, llm_provider)
    except Exception as e:
        logger.error(f"Error getting share of voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/competitive-landscape/{brand_name}")
async def get_competitive_landscape(
    brand_name: str,
    llm_provider: str | None = Query(None),
    query: QueryBuilder = Depends(get_query_builder),
) -> dict[str, Any]:
    """Get competitive landscape for a brand."""
    try:
        return await query.get_competitive_landscape(brand_name, llm_provider)
    except Exception as e:
        logger.error(f"Error getting competitive landscape: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# STATS ENDPOINTS
# =========================================================================


@app.get("/graph/stats")
async def get_graph_stats(
    query: QueryBuilder = Depends(get_query_builder),
) -> dict[str, Any]:
    """Get overall graph statistics."""
    try:
        return await query.get_graph_stats()
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# CLEANUP ENDPOINTS
# =========================================================================


@app.delete("/graph/website/{website_id}")
async def clear_website_data(
    website_id: str,
    builder: GraphBuilder = Depends(get_graph_builder),
) -> dict[str, int]:
    """Clear all graph data for a website."""
    try:
        deleted = await builder.clear_website_data(website_id)
        return {"deleted_nodes": deleted}
    except Exception as e:
        logger.error(f"Error clearing website data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
