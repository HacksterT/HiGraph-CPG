"""
Neo4j Client Utilities

Shared connection management and batch operation helpers for all
graph population scripts.
"""

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


def get_driver():
    """
    Create a Neo4j driver using environment variables.

    Returns:
        Neo4j GraphDatabase driver
    """
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD')

    if not password:
        raise ValueError("NEO4J_PASSWORD not set in environment")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    return driver


def run_batch(driver, queries: List[Dict[str, Any]], database: str = None):
    """
    Execute a batch of Cypher queries in a single transaction.

    Args:
        driver: Neo4j driver
        queries: List of {'query': str, 'params': dict}
        database: Optional database name
    """
    with driver.session(database=database) as session:
        with session.begin_transaction() as tx:
            for q in queries:
                tx.run(q['query'], q.get('params', {}))
            tx.commit()


def merge_node(tx, label: str, id_property: str, id_value: str, properties: Dict[str, Any]):
    """
    MERGE a node by its primary key and SET all properties.

    Args:
        tx: Neo4j transaction
        label: Node label
        id_property: Primary key property name
        id_value: Primary key value
        properties: All properties to set (including the id)
    """
    # Build SET clause from properties
    set_parts = []
    params = {'id_value': id_value}
    for key, value in properties.items():
        if key == id_property:
            continue  # Already in MERGE
        param_name = f'p_{key}'
        set_parts.append(f'n.{key} = ${param_name}')
        params[param_name] = value

    set_clause = ', '.join(set_parts)
    query = f"""
    MERGE (n:{label} {{{id_property}: $id_value}})
    SET {set_clause}
    """
    tx.run(query, params)


def merge_relationship(
    tx,
    from_label: str,
    from_id_prop: str,
    from_id_val: str,
    to_label: str,
    to_id_prop: str,
    to_id_val: str,
    rel_type: str,
    rel_properties: Optional[Dict[str, Any]] = None,
):
    """
    MERGE a relationship between two existing nodes.

    Args:
        tx: Neo4j transaction
        from_label: Source node label
        from_id_prop: Source node ID property name
        from_id_val: Source node ID value
        to_label: Target node label
        to_id_prop: Target node ID property name
        to_id_val: Target node ID value
        rel_type: Relationship type
        rel_properties: Optional properties on the relationship
    """
    params = {
        'from_id': from_id_val,
        'to_id': to_id_val,
    }

    if rel_properties:
        set_parts = []
        for key, value in rel_properties.items():
            param_name = f'rp_{key}'
            set_parts.append(f'r.{key} = ${param_name}')
            params[param_name] = value
        set_clause = 'SET ' + ', '.join(set_parts)
    else:
        set_clause = ''

    query = f"""
    MATCH (a:{from_label} {{{from_id_prop}: $from_id}})
    MATCH (b:{to_label} {{{to_id_prop}: $to_id}})
    MERGE (a)-[r:{rel_type}]->(b)
    {set_clause}
    """
    tx.run(query, params)


__all__ = ['get_driver', 'run_batch', 'merge_node', 'merge_relationship']
