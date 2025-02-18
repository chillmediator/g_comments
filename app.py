from flask import Flask, request, jsonify
import os
from rich.console import Console
from rich.panel import Panel
from rich.pretty import pprint
from datetime import datetime
import requests
from dotenv import load_dotenv, find_dotenv

# Initialize console
console = Console()

def reload_env():
    """Reload environment variables from .env file"""
    dotenv_path = find_dotenv()
    if dotenv_path:
        load_dotenv(dotenv_path, override=True)
    else:
        console.print("[bold red]Warning:[/bold red] No .env file found")

# Initial load of environment variables
reload_env()

# Configuration
CHATWOOT_BASE_URL = os.getenv('CHATWOOT_BASE_URL')
CHATWOOT_API_TOKEN = os.getenv('CHATWOOT_API_TOKEN')
CHATWOOT_ACCOUNT_ID = os.getenv('CHATWOOT_ACCOUNT_ID')

app = Flask(__name__)

def get_conversation_history(conversation_id, max_messages=50):
    """
    Fetch and format conversation history from Chatwoot for a specific conversation.
    
    Args:
        conversation_id (str): The ID of the conversation to fetch
        max_messages (int): Maximum number of messages to include in context
        
    Returns:
        str: Formatted conversation history for LLM context
    """
    try:
        # Validate environment variables
        if not all([CHATWOOT_BASE_URL, CHATWOOT_API_TOKEN, CHATWOOT_ACCOUNT_ID]):
            raise ValueError("Missing required Chatwoot environment variables")

        url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages"
        headers = {
            'api_access_token': CHATWOOT_API_TOKEN,
            'Content-Type': 'application/json'
        }

        # Make API request
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Extract messages from payload
        messages = []
        if isinstance(data, dict):
            messages = data.get('payload', [])
        elif isinstance(data, list):
            messages = data
            
        if not messages:
            console.print("[yellow]No messages found in conversation history[/yellow]")
            return ""
        
        # Format messages
        formatted_history = []
        message_count = 0
        
        # Process messages in chronological order (oldest first)
        for message in messages:
            # Skip empty content
            content = message.get('content', '').strip()
            if not content:
                continue
                
            # Get message type (0 = incoming/user, 1 = outgoing/assistant)
            message_type = message.get('message_type')
            if message_type not in (0, 1):
                continue
                
            # Format message
            prefix = "User:" if message_type == 0 else "Assistant:"
            formatted_history.append(f"{prefix} {content}")
            
            message_count += 1
            if message_count >= max_messages:
                break
        
        # Combine messages into context string
        context = "\n".join(formatted_history)
        
        # Log success
        console.print(Panel(
            f"[bold green]Successfully Retrieved History[/bold green]\n"
            f"Messages processed: {message_count}",
            border_style="green"
        ))
        
        return context

    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]API Error:[/bold red] Error fetching conversation history: {str(e)}")
        return ""
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Unexpected error while fetching history: {str(e)}")
        return ""

def get_llm_response(message, conversation_id=None):
    """
    Get a response from the LLM API with conversation history context
    
    Args:
        message (str): The user's message to respond to
        conversation_id (str, optional): The conversation ID to fetch history for
        
    Returns:
        str: The AI's response
    """
    try:
        # Reload environment variables to ensure we have the latest values
        reload_env()
        
        # Get conversation history if available
        context = ""
        if conversation_id:
            context = get_conversation_history(conversation_id)
        
        # Construct the prompt with fresh environment variables
        system_message = os.getenv('SYSTEM_MESSAGE', 'You are a helpful AI assistant.')
        
        # Build the full prompt with history and current message
        if context:
            full_prompt = f"{system_message}\n\nConversation history:\n{context}\n\nUser: {message}\nAssistant:"
        else:
            full_prompt = f"{system_message}\n\nUser: {message}\nAssistant:"
            
        # Log the prompt for debugging
        console.print(Panel(
            f"[bold cyan]Prompt Details[/bold cyan]\n"
            f"System Message: {system_message}\n"
            f"Has History: {'Yes' if context else 'No'}",
            border_style="cyan"
        ))
        
        # Prepare API request with fresh environment variables
        endpoint = os.getenv('OLLAMA_ENDPOINT')
        model = os.getenv('LLM_MODEL', 'dolphin3')
        
        if not endpoint:
            raise ValueError("OLLAMA_ENDPOINT environment variable is not set")
        
        console.print(Panel(
            f"[bold cyan]Request Details[/bold cyan]\n"
            f"Endpoint: {endpoint}\n"
            f"Model: {model}\n"
            f"System Message: {system_message}\n"
            f"Prompt: {message}",
            border_style="cyan"
        ))
        
        # Make API request
        url = f"{endpoint}/api/generate"
        response = requests.post(url, json={
            'model': model,
            'prompt': full_prompt,
            'stream': False
        })
        response.raise_for_status()
        
        # Parse response
        response_data = response.json()
        if 'response' not in response_data:
            raise ValueError(f"Unexpected API response format: {response_data}")
            
        # Log raw response for debugging
        console.print("[bold yellow]Raw LLM Response:[/bold yellow]")
        console.print(response_data)
        
        ai_response = response_data['response'].strip()
        
        # Log the final response
        console.print(Panel(
            f"[bold green]AI Response[/bold green]\n"
            f"{ai_response}",
            border_style="green"
        ))
        
        return ai_response
        
    except requests.exceptions.RequestException as e:
        error_message = f"API Error: {str(e)}"
        console.print(f"[bold red]Error:[/bold red] {error_message}")
        return "I apologize, but I'm having trouble connecting to my language model right now. Please try again in a moment."
        
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        console.print(f"[bold red]Error:[/bold red] {error_message}")
        return "I apologize, but I encountered an unexpected error. Please try again."

def send_chatwoot_reply(conversation_id, message):
    """Send reply back to Chatwoot conversation"""
    try:
        # Get account_id from environment variable
        account_id = os.getenv('CHATWOOT_ACCOUNT_ID')
        if not account_id:
            console.print(Panel(
                "[bold red]CHATWOOT_ACCOUNT_ID not set in environment variables[/bold red]",
                border_style="red"
            ))
            return False

        url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
        headers = {
            'api_access_token': CHATWOOT_API_TOKEN,
            'Content-Type': 'application/json'
        }
        payload = {
            'content': message,
            'message_type': 'outgoing'
        }
        
        console.print(f"[bold cyan]Sending to URL:[/bold cyan] {url}")
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        console.print(Panel(
            f"[bold green]Reply Sent to Chatwoot[/bold green]\nConversation ID: {conversation_id}\nMessage: {message}",
            border_style="green"
        ))
        
        return True
        
    except requests.exceptions.RequestException as e:
        console.print(Panel(
            f"[bold red]Chatwoot API Error[/bold red]\n{str(e)}",
            border_style="red"
        ))
        return False

@app.route('/webhook', methods=['POST'])
def chatwoot_webhook():
    try:
        data = request.json
        
        # Log incoming webhook data
        console.print(Panel(
            "[bold cyan]Incoming Webhook Data[/bold cyan]",
            border_style="cyan"
        ))
        pprint(data)
        
        # Extract relevant information
        event_type = data.get('event')
        if not event_type or 'message_created' not in event_type:
            return jsonify({'status': 'ignored', 'reason': 'not a message event'})
        
        # Get the latest message from the messages array
        messages = data.get('messages', [])
        if not messages:
            return jsonify({'status': 'error', 'reason': 'no messages found'})
        
        latest_message = messages[0]
        message_type = latest_message.get('message_type')
        
        # Check if it's an incoming message (message_type 0 is incoming)
        if message_type != 0:
            return jsonify({'status': 'ignored', 'reason': 'not an incoming message'})
        
        conversation_id = data.get('id')
        message_content = latest_message.get('content')
        
        console.print(Panel(
            f"[bold green]Processing Message[/bold green]\nContent: {message_content}",
            border_style="green"
        ))
        
        if not all([conversation_id, message_content]):
            return jsonify({'status': 'error', 'reason': 'missing required fields'})
        
        # Get AI response
        ai_response = get_llm_response(message_content, conversation_id=conversation_id)
        
        console.print(Panel(
            f"[bold blue]AI Response[/bold blue]\n{ai_response}",
            border_style="blue"
        ))
        
        # Send response back to Chatwoot
        if send_chatwoot_reply(conversation_id, ai_response):
            return jsonify({'status': 'success', 'message': 'response sent'})
        else:
            return jsonify({'status': 'error', 'reason': 'failed to send response'})
            
    except Exception as e:
        console.print(Panel(
            f"[bold red]Webhook Error[/bold red]\n{str(e)}",
            border_style="red"
        ))
        return jsonify({'status': 'error', 'reason': str(e)}), 500

@app.route('/update_system_message', methods=['POST'])
def update_system_message():
    """Update the system message in the .env file"""
    try:
        data = request.get_json()
        new_system_message = data.get('system_message')
        new_model = data.get('model')
        
        if not new_system_message and not new_model:
            return jsonify({'error': 'No system_message or model provided'}), 400
        
        # Read all environment variables
        with open('.env', 'r') as f:
            env_lines = f.readlines()
        
        # Update the relevant lines
        updated_lines = []
        for line in env_lines:
            if new_system_message and line.startswith('SYSTEM_MESSAGE='):
                updated_lines.append(f'SYSTEM_MESSAGE="{new_system_message}"\n')
            elif new_model and line.startswith('LLM_MODEL='):
                updated_lines.append(f'LLM_MODEL={new_model}\n')
            else:
                updated_lines.append(line)
        
        # Write back to .env file
        with open('.env', 'w') as f:
            f.writelines(updated_lines)
        
        # Force reload of environment variables
        reload_env()
        
        return jsonify({
            'message': 'Settings updated successfully',
            'system_message': new_system_message if new_system_message else 'unchanged',
            'model': new_model if new_model else 'unchanged'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    if not all([CHATWOOT_BASE_URL, CHATWOOT_API_TOKEN, CHATWOOT_ACCOUNT_ID]):
        console.print(Panel(
            "[bold red]Missing required environment variables![/bold red]\n"
            "Please ensure all required environment variables are set in .env file:",
            border_style="red"
        ))
        exit(1)
    
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
