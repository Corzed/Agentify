from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
from openai import OpenAI
import uuid
from dotenv import load_dotenv
import os
import json
import markdown
import datetime
import importlib.util

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='../frontend')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
GPT_MODEL = os.getenv('GPT_MODEL')

# Folder to store agents and tools
AGENTS_FOLDER = 'agents'
TOOLS_FOLDER = 'tools'

# In-memory storage for active sessions
active_sessions = {}
conversation_history = []

# Tool cache
tools_cache = {}


@app.route('/agent/create', methods=['POST'])
def create_agent():
    data = request.json
    agent_id = str(uuid.uuid4())
    name = data['name']
    new_agent = {
        'name': data['name'],
        'context': data.get('context', ''),
        'tools': data.get('tools', [])
    }
    active_sessions[agent_id] = new_agent

    # Persist the new agent to a file
    with open(os.path.join(AGENTS_FOLDER, f"{name}.json"), 'w') as f:
        json.dump(new_agent, f)

    return jsonify({"id": agent_id, "name": new_agent['name']})

def ensure_agents_folder():
    if not os.path.exists(AGENTS_FOLDER):
        os.makedirs(AGENTS_FOLDER)


def load_tool(tool_name):
    if tool_name in tools_cache:
        return tools_cache[tool_name]

    # First, check in the general tools folder
    tool_path = os.path.join(TOOLS_FOLDER, f"{tool_name}.py")
    if not os.path.exists(tool_path):
        # If not found, check in the agent's folder
        agent_folder = os.path.join(AGENTS_FOLDER, os.path.dirname(tool_name))
        tool_filename = os.path.basename(tool_name)
        tool_path = os.path.join(agent_folder, f"{tool_filename}.py")
        if not os.path.exists(tool_path):
            return None

    spec = importlib.util.spec_from_file_location(tool_name, tool_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, 'tool'):
        tools_cache[tool_name] = module.tool
        return module.tool
    else:
        return None


def get_available_tools():
    tools = []
    # Get tools from the general tools folder
    for filename in os.listdir(TOOLS_FOLDER):
        if filename.endswith('.py'):
            tool_name = filename[:-3]
            tool = load_tool(tool_name)
            if tool:
                tools.append({
                    'name': tool_name,
                    'description': tool.get('description', 'No description provided')
                })

    # Get tools from agent-specific folders
    for agent_folder in os.listdir(AGENTS_FOLDER):
        agent_path = os.path.join(AGENTS_FOLDER, agent_folder)
        if os.path.isdir(agent_path):
            for filename in os.listdir(agent_path):
                if filename.endswith('.py'):
                    tool_name = f"{agent_folder}/{filename[:-3]}"
                    tool = load_tool(tool_name)
                    if tool:
                        tools.append({
                            'name': tool_name,
                            'description': tool.get('description', 'No description provided')
                        })
    return tools


def load_agents():
    ensure_agents_folder()
    for filename in os.listdir(AGENTS_FOLDER):
        if filename.endswith('.json'):
            with open(os.path.join(AGENTS_FOLDER, filename), 'r') as f:
                agent_data = json.load(f)
                agent_id = str(uuid.uuid4())
                active_sessions[agent_id] = {
                    'name': agent_data['name'],
                    'context': agent_data.get('context', ''),
                    'tools': agent_data.get('tools', [])
                }


def get_agent_tool_descriptions(agent_id):
    agent = active_sessions.get(agent_id)
    if not agent or not agent['tools']:
        return ""

    tool_descriptions = []
    for tool_name in agent['tools']:
        tool = load_tool(tool_name)
        if tool:
            tool_descriptions.append(f"- {tool_name}: {tool.get('description', 'No description provided')}")

    return "\n".join(tool_descriptions)


def use_tool(agent_id, tool_name, *args):
    agent = active_sessions.get(agent_id)
    if not agent or not agent['tools'] or tool_name not in agent['tools']:
        return f"Error: Tool '{tool_name}' is not available for this agent"

    tool = load_tool(tool_name)
    if tool and 'function' in tool:
        try:
            result = tool['function'](*args)
            print(f"Tool used: {tool_name}, Agent: {agent['name']}, Arguments: {args}, Result: {result}")  # New line
            return result
        except Exception as e:
            error_message = f"Error using tool '{tool_name}': {str(e)}"
            print(f"Tool error: {tool_name}, Agent: {agent['name']}, Arguments: {args}, Error: {error_message}")  # New line
            return error_message
    else:
        error_message = f"Error: Tool '{tool_name}' not found or invalid"
        print(f"Tool not found: {tool_name}, Agent: {agent['name']}")  # New line
        return error_message


def generate_agent_response(agent_id, task):
    session = active_sessions.get(agent_id)
    if not session:
        return "Agent session not found"

    tool_descriptions = get_agent_tool_descriptions(agent_id)

    if tool_descriptions:
        tool_prompt = f"""You have access to the following tools:
{tool_descriptions}

To use a tool, include [USE_TOOL: tool_name, arg1, arg2, ...] in your response."""
    else:
        tool_prompt = "You do not have access to any tools for this task."

    prompt = f"""You are Agent {session['name']} with context: {session['context']}.
Your task is: {task}
{tool_prompt}
Provide a response to this task, using tools if available and necessary."""

    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system",
             "content": "You are an AI agent in an orchestrator system with potential access to tools."},
            {"role": "user", "content": prompt}
        ]
    )

    agent_response = response.choices[0].message.content.strip()

    # Check for tool usage in the response only if the agent has tools
    if session['tools']:
        while "[USE_TOOL:" in agent_response:
            start = agent_response.find("[USE_TOOL:")
            end = agent_response.find("]", start)
            if end == -1:
                break

            tool_call = agent_response[start + 10:end].split(',')
            tool_name = tool_call[0].strip()
            tool_args = [arg.strip() for arg in tool_call[1:]]

            tool_result = use_tool(agent_id, tool_name, *tool_args)
            agent_response = agent_response[:start] + str(tool_result) + agent_response[end + 1:]

    return agent_response


@app.route('/')
def serve_html():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/agent/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    if agent_id in active_sessions:
        return jsonify({
            "id": agent_id,
            "name": active_sessions[agent_id]['name'],
            "context": active_sessions[agent_id]['context'],
            "tools": active_sessions[agent_id]['tools']
        })
    else:
        return jsonify({"error": "Agent not found"}), 404


@app.route('/agent/<agent_id>/communicate', methods=['POST'])
def agent_communicate(agent_id):
    if agent_id not in active_sessions:
        return jsonify({"error": "Agent session not found"}), 404

    message = request.json['message']
    response = generate_agent_response(agent_id, message)

    # Update last activity
    active_sessions[agent_id]['last_activity'] = datetime.datetime.now()

    # Emit WebSocket event
    socketio.emit('agent_response', {'agent_id': agent_id, 'response': response})

    return jsonify({"response": response})


@app.route('/orchestrator/process_request', methods=['POST'])
def process_request():
    user_request = request.json['request']

    # Log user request
    socketio.emit('user_request', {'request': user_request})

    # Step 1: Analyze the request and create a plan
    plan = create_execution_plan(user_request)

    # Step 2: Execute the plan
    results = execute_plan(plan)

    # Step 3: Combine results into a final answer
    final_answer = combine_results(results)

    # Convert Markdown to HTML
    final_answer_html = markdown.markdown(final_answer)

    # Log final answer
    socketio.emit('final_answer', {'response': final_answer_html})

    # Update conversation history
    conversation_history.append({"user": user_request, "assistant": final_answer})
    if len(conversation_history) > 10:
        conversation_history.pop(0)

    return jsonify({"response": final_answer_html})


def create_execution_plan(user_request):
    prompt = f"Given the user request: '{user_request}', create a plan to process this request. Break it down into subtasks if necessary. Each subtask should be assigned to an agent, but do note: you do not need to use all of the agents. Available agents: {[session['name'] for session in active_sessions.values()]}. Respond with a JSON array of tasks, where each task has 'description' and 'assigned_agent' fields. Make sure each agent has the necessary context needed to complete the task. One last thing- each task you make costs the user a lot of money, so use the least amount possible."

    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system",
             "content": "You are an AI orchestrator. Create execution plans for processing user requests."},
            {"role": "user", "content": prompt}
        ]
    )

    plan_text = response.choices[0].message.content.strip()

    try:
        # Remove any markdown formatting
        plan_text = plan_text.replace("```json", "").replace("```", "").strip()
        plan = json.loads(plan_text)
        if not isinstance(plan, list):
            raise ValueError("Expected a JSON array")

        # Validate the structure of each task
        for task in plan:
            if not isinstance(task, dict) or 'description' not in task or 'assigned_agent' not in task:
                raise ValueError("Invalid task structure")

        formatted_plan = format_execution_plan(plan)
        socketio.emit('execution_plan', {'plan': formatted_plan})
        return plan
    except json.JSONDecodeError:
        # If JSON parsing fails, return a default plan
        default_plan = [{"description": user_request, "assigned_agent": list(active_sessions.values())[0]['name']}]
        formatted_plan = format_execution_plan(default_plan)
        socketio.emit('execution_plan', {'plan': formatted_plan})
        return default_plan


def format_execution_plan(plan):
    formatted_plan = "**Execution Plan:**\n\n"
    for i, task in enumerate(plan, 1):
        formatted_plan += f"{i}. {task['description']} (Assigned to: {task['assigned_agent']})\n"
    return formatted_plan


def execute_plan(plan):
    results = []
    context = {}
    for task in plan:
        assigned_agent = next(
            (id for id, session in active_sessions.items() if session['name'] == task['assigned_agent']), None)
        if assigned_agent:
            prompt = f"Task: {task['description']}\nContext: {json.dumps(context, indent=2)}\nProvide a response based on this task and context."
            response = generate_agent_response(assigned_agent, prompt)
            result = {"task": task['description'], "agent": task['assigned_agent'], "response": response}
            results.append(result)
            context[task['description']] = response

            socketio.emit('task_completed', {
                "agent_id": assigned_agent,
                "task": task['description'],
                "response": response
            })
    return results


def combine_results(results):
    conversation_history_text = "\n".join(
        [f"User: {msg['user']}\nAssistant: {msg['assistant']}" for msg in conversation_history[-5:]])
    prompt = f"""Given the following conversation history:

{conversation_history_text}

And the following task results:

{json.dumps(results, indent=2)}

Generate a coherent and integrated response for the user. The response should:
1. Synthesize information from all completed tasks
2. Provide a clear and concise answer to the user's original request
3. Include any relevant code or examples from the task results
4. Flow naturally and not explicitly mention the individual tasks or agents involved
5. Ask for clarification only if absolutely necessary based on the information provided
6. Use Markdown formatting for improved readability (e.g., headers, code blocks, lists)

Your response:"""

    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system",
             "content": "You are an AI assistant. Combine the results of multiple tasks into a natural, flowing response for the user. Use Markdown formatting for improved readability."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()


@app.route('/agents', methods=['GET'])
def get_agents():
    return jsonify([
        {"id": agent_id, "name": agent_data['name']}
        for agent_id, agent_data in active_sessions.items()
    ])


@app.route('/tools', methods=['GET'])
def get_tools():
    return jsonify(get_available_tools())


if __name__ == '__main__':
    load_agents()
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)