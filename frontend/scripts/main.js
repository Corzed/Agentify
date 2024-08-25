const socket = io('http://localhost:5000');
const converter = new showdown.Converter({extensions: [{
    type: 'output',
    filter: function(text) {
        var left = '<pre><code\\b[^>]*>',
            right = '</code></pre>',
            flags = 'g';
        return text.replace(new RegExp(left, flags), function(match) {
            return match.replace(/class="(.*)"/g, 'class="hljs $1"');
        });
    }
}]});

socket.on('connect', () => {
    console.log('Connected to server');
    fetchAgents();
});

socket.on('user_request', (data) => {
    addCommMessage('to', `User Request: ${data.request}`);
});

socket.on('execution_plan', (data) => {
    addCommMessage('to', data.plan);
});

socket.on('task_completed', (data) => {
    addCommMessage('from', `Task "${data.task}" completed by ${data.agent_id}:`);
    addCommMessage('from', data.response);
    animateAgentCommunication(data.agent_id);
});

socket.on('final_answer', (data) => {
    addCommMessage('from', `Final Answer:`);
    addCommMessage('from', data.response, true);
});

function fetchAgents() {
    fetch('http://localhost:5000/agents')
        .then(response => response.json())
        .then(data => {
            const agents = data.map(agent => {
                return fetch(`http://localhost:5000/agent/${agent.id}`)
                    .then(response => response.json())
                    .then(agentData => ({
                        id: agent.id,
                        name: agentData.name || `Agent ${agent.id.substring(0, 8)}`,
                        tools: agentData.tools || [] // Include tools here
                    }));
            });

            Promise.all(agents).then(resolvedAgents => {
                updateAgentList(resolvedAgents);
                updateAgentNetwork(resolvedAgents);
            });
        })
        .catch(error => console.error('Error fetching agents:', error));
}

function createAgent() {
    const name = document.getElementById('agent-name').value;
    const description = document.getElementById('agent-description').value;

    fetch('http://localhost:5000/agent/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: name, context: description }),
    })
    .then(response => response.json())
    .then(data => {
        console.log('Agent created:', data);
        fetchAgents();
        clearAgentForm();
    })
    .catch(error => console.error('Error creating agent:', error));
}

function updateAgentList(agents) {
    const activeAgents = document.getElementById('active-agents');
    activeAgents.innerHTML = '';
    agents.forEach(agent => {
        const agentItem = document.createElement('div');
        agentItem.className = 'agent-item';
        if (typeof agent === 'object' && agent.name) {
            agentItem.innerHTML = `<h3>${agent.name}</h3>`;
        } else if (typeof agent === 'string') {
            fetch(`http://localhost:5000/agent/${agent}`)
                .then(response => response.json())
                .then(data => {
                    agentItem.innerHTML = `<h3>${data.name || 'Unnamed Agent'}</h3>`;
                })
                .catch(error => {
                    console.error('Error fetching agent details:', error);
                    agentItem.innerHTML = `<h3>Agent ${agent.substring(0, 8)}</h3>`;
                });
        }
        activeAgents.appendChild(agentItem);
    });
}

function clearAgentForm() {
    document.getElementById('agent-name').value = '';
    document.getElementById('agent-description').value = '';
}

function addCommMessage(direction, text, isHtml = false) {
    const messages = document.getElementById('comm-messages');
    const message = document.createElement('div');
    message.className = `message comm-${direction} markdown-body`;
    if (isHtml) {
        message.innerHTML = text;
    } else {
        message.innerHTML = converter.makeHtml(text);
    }
    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
    hljs.highlightAll();
}

// Event listeners
document.getElementById('create-agent').addEventListener('click', createAgent);

// Initialize
fetchAgents();