from flask import Flask, request, jsonify
import os
from rich.console import Console
from rich.panel import Panel
from rich.pretty import pprint
from datetime import datetime
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
CHATWOOT_BASE_URL = os.getenv('CHATWOOT_BASE_URL')
CHATWOOT_API_TOKEN = os.getenv('CHATWOOT_API_TOKEN')
CHATWOOT_ACCOUNT_ID = os.getenv('CHATWOOT_ACCOUNT_ID')

app = Flask(__name__)
console = Console()

def get_llm_response(message):
    """Get response from LLM API using Ollama"""
    try:
        # Force reload environment variables
        load_dotenv(override=True)
        
        # Load environment variables for each request
        ollama_endpoint = os.getenv('OLLAMA_ENDPOINT')
        llm_model = os.getenv('LLM_MODEL', 'mistral')
        system_message = os.getenv('SYSTEM_MESSAGE', 'You are a helpful AI assistant.')
        
        headers = {'Content-Type': 'application/json'}
        payload = {
            'model': llm_model,
            'prompt': message,
            'system': system_message,
            'stream': False
        }
        
        # Log the request details for debugging
        console.print(Panel(
            f"[bold cyan]Request Details[/bold cyan]\n"
            f"Endpoint: {ollama_endpoint}\n"
            f"Model: {llm_model}\n"
            f"System Message: {system_message}\n"
            f"Message: {message}",
            border_style="cyan"
        ))

        api_url = f"{ollama_endpoint}/api/generate"
        console.print(f"[bold green]Calling API URL:[/bold green] {api_url}")
        
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        
        # Log the raw response for debugging
        console.print("[bold yellow]Raw Response:[/bold yellow]")
        console.print(response.json())
        
        return response.json()['response']
    
    except requests.exceptions.RequestException as e:
        error_message = f"Error calling LLM API: {str(e)}"
        console.print(f"[bold red]Error:[/bold red] {error_message}")
        return f"I apologize, but I encountered an error: {error_message}"
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        console.print(f"[bold red]Error:[/bold red] {error_message}")
        return f"I apologize, but something went wrong: {error_message}"

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
        ai_response = get_llm_response(message_content)
        
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
        load_dotenv(override=True)
        
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
