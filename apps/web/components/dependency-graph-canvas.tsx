"use client";

import { useEffect, useMemo, useState } from "react";
import ELK from "elkjs/lib/elk.bundled.js";
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";

import type { DependencyGraph } from "@/lib/api";

type GraphNodeData = DependencyGraph["nodes"][number] & { onSelectCourse?: (code: string) => void };
type FlowNode = Node<GraphNodeData>;
type FlowEdge = Edge<{ label: string; kind: string }>;

const elk = new ELK();

function SemanticNode({ data }: NodeProps<FlowNode>) {
  const isCourse = data.kind === "COURSE";
  const content = (
    <>
      <span className="graph-node-kind">{isCourse ? "Curso" : "Condición"}</span>
      <strong>{isCourse ? data.course_code : data.label}</strong>
      <span className="graph-node-label">{isCourse ? data.label : data.condition_type}</span>
      <span className="graph-node-state">{data.state.replaceAll("_", " ")}</span>
    </>
  );
  return (
    <div className={`semantic-graph-node semantic-graph-node-${isCourse ? "course" : "condition"}`}>
      <Handle type="target" position={Position.Left} />
      {isCourse && data.course_code ? (
        <button
          className="semantic-graph-node-button"
          type="button"
          onClick={() => data.onSelectCourse?.(data.course_code ?? "")}
          aria-label={`Abrir análisis de ${data.course_code} ${data.label}`}
        >
          {content}
        </button>
      ) : (
        <div className="semantic-graph-node-content">{content}</div>
      )}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = { semantic: SemanticNode };

async function calculateLayout(nodes: FlowNode[], edges: FlowEdge[]): Promise<FlowNode[]> {
  const result = await elk.layout({
    id: "dependency-graph",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.edgeRouting": "ORTHOGONAL",
      "elk.layered.spacing.nodeNodeBetweenLayers": "80",
      "elk.spacing.nodeNode": "36",
      "elk.spacing.edgeNode": "24",
    },
    children: nodes.map((node) => ({ id: node.id, width: 214, height: 112 })),
    edges: edges.map((edge) => ({ id: edge.id, sources: [edge.source], targets: [edge.target] })),
  });
  const positions = new Map((result.children ?? []).map((node) => [node.id, node]));
  return nodes.map((node) => ({
    ...node,
    position: {
      x: positions.get(node.id)?.x ?? 0,
      y: positions.get(node.id)?.y ?? 0,
    },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  }));
}

export function DependencyGraphCanvas({
  nodes,
  edges,
  onSelectCourse,
}: {
  nodes: DependencyGraph["nodes"];
  edges: DependencyGraph["edges"];
  onSelectCourse: (code: string) => void;
}) {
  const sourceNodes = useMemo<FlowNode[]>(
    () => nodes.map((node) => ({ id: node.id, type: "semantic", position: { x: 0, y: 0 }, data: { ...node, onSelectCourse } })),
    [nodes, onSelectCourse],
  );
  const sourceEdges = useMemo<FlowEdge[]>(
    () => edges.map((edge) => ({ id: edge.id, source: edge.source, target: edge.target, label: edge.label, data: { label: edge.label, kind: edge.kind }, type: "default", animated: false })),
    [edges],
  );
  const [flowNodes, setFlowNodes] = useState<FlowNode[]>(sourceNodes);

  useEffect(() => {
    let cancelled = false;
    void calculateLayout(sourceNodes, sourceEdges).then((positioned) => {
      if (!cancelled) window.queueMicrotask(() => setFlowNodes(positioned));
    });
    return () => {
      cancelled = true;
    };
  }, [sourceEdges, sourceNodes]);

  return (
    <div className="dependency-graph-canvas" aria-label="Grafo visual de dependencias">
      <ReactFlow
        nodes={flowNodes}
        edges={sourceEdges}
        nodeTypes={nodeTypes}
        nodesConnectable={false}
        nodesDraggable={false}
        elementsSelectable
        fitView
        fitViewOptions={{ padding: 0.18, maxZoom: 1.1 }}
        minZoom={0.1}
        maxZoom={1.5}
        attributionPosition="bottom-left"
      >
        <Background gap={24} size={1} />
        <Controls showInteractive={false} />
        <MiniMap pannable zoomable nodeColor={(node) => node.data?.kind === "CONDITION" ? "#c7924c" : "#4a8d70"} />
      </ReactFlow>
    </div>
  );
}
