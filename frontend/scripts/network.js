// Main network object
let network;

// Configuration options for the network
const networkOptions = {
    nodes: {
        shape: 'circularImage',
        size: 30,
        font: {
            size: 14,
            color: '#ffffff',
            strokeWidth: 2,
            strokeColor: '#000000'
        },
        borderWidth: 2,
        shadow: true
    },
    edges: {
        width: 2,
        color: { color: '#3498db', highlight: '#2980b9' },
        smooth: { type: 'continuous' }
    },
    physics: {
        enabled: true,
        barnesHut: {
            gravitationalConstant: -2000,
            centralGravity: 0.3,
            springLength: 95,
            springConstant: 0.04,
            damping: 0.09,
            avoidOverlap: 0.1
        },
        stabilization: {
            iterations: 1000,
            updateInterval: 100
        }
    },
    interaction: {
        dragNodes: true,
        dragView: true,
        zoomView: true,
        hover: true
    }
};

// Function to create and update the agent network
function updateAgentNetwork(agents) {
    const container = document.getElementById('agent-network');
    const nodes = new vis.DataSet();
    const edges = new vis.DataSet();

    addOrchestratorNode(nodes);
    addAgentNodesAndTools(nodes, edges, agents);

    const data = { nodes, edges };

    if (!network) {
        network = new vis.Network(container, data, networkOptions);
    } else {
        network.setData(data);
    }
}

// Function to add the orchestrator node
function addOrchestratorNode(nodes) {
    nodes.add({
        id: 'orchestrator',
        label: 'Orchestrator',
        image: 'https://robohash.org/orchestrator?size=80x80',
        color: {
            border: '#e74c3c',
            background: '#ffffff'
        },
        font: { size: 18, color: '#e74c3c' }
    });
}

// Function to add agent nodes, tool nodes, and edges
function addAgentNodesAndTools(nodes, edges, agents) {
    agents.forEach((agent, index) => {
        nodes.add({
            id: agent.id,
            label: agent.name,
            image: `https://robohash.org/${agent.id}?size=50x50`,
            color: {
                border: '#3498db',
                background: '#ffffff'
            }
        });

        edges.add({
            id: `edge-${agent.id}`,
            from: 'orchestrator',
            to: agent.id
        });

        // Add tools for each agent
        if (agent.tools && Array.isArray(agent.tools)) {
            agent.tools.forEach((tool, toolIndex) => {
                const toolId = `${agent.id}-tool-${toolIndex}`;
                nodes.add({
                    id: toolId,
                    label: tool,
                    shape: 'hexagon',
                    color: {
                        border: '#2ecc71',
                        background: '#ffffff'
                    },
                    font: { size: 12, color: '#2ecc71' }
                });

                edges.add({
                    id: `edge-${agent.id}-${toolId}`,
                    from: agent.id,
                    to: toolId,
                    color: { color: '#2ecc71' },
                    dashes: true
                });
            });
        }
    });
}

// Function to animate agent communication
function animateAgentCommunication(agentId) {
    if (!network) return;

    const edgeId = `edge-${agentId}`;
    const originalColor = '#3498db';
    const originalWidth = 2;
    const animatedColor = '#e74c3c';
    const animatedWidth = 4;
    const animationDuration = 1000; // 1 second

    // Animate to red and thicker
    network.updateEdge(edgeId, {
        color: { color: animatedColor },
        width: animatedWidth
    });

    // After the animation duration, revert back to original state
    setTimeout(() => {
        network.updateEdge(edgeId, {
            color: { color: originalColor },
            width: originalWidth
        });
    }, animationDuration);
}