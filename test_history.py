import os
import json
from datetime import datetime
import requests
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Rich console
console = Console()

def test_fetch_history():
    """
    Test function to fetch and log conversation history from Chatwoot
    """
    # Configuration
    CHATWOOT_BASE_URL = "https://chatwoot.orhidi.com"
    CHATWOOT_API_TOKEN = os.getenv('CHATWOOT_API_TOKEN')
    ACCOUNT_ID = "2"
    CONVERSATION_ID = "23276"
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"conversation_history_{timestamp}.log"
    
    try:
        # Prepare request
        url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations/{CONVERSATION_ID}/messages"
        headers = {
            'api_access_token': CHATWOOT_API_TOKEN,
            'Content-Type': 'application/json'
        }
        
        console.print(Panel(
            f"[bold cyan]Fetching Conversation History[/bold cyan]\n"
            f"URL: {url}\n"
            f"Account ID: {ACCOUNT_ID}\n"
            f"Conversation ID: {CONVERSATION_ID}",
            border_style="cyan"
        ))
        
        # Make request
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Get response data
        response_data = response.json()
        
        # Create detailed log
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'request': {
                'url': url,
                'headers': {k: v for k, v in headers.items() if k != 'api_access_token'}  # Exclude token for security
            },
            'response': {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'data': response_data
            }
        }
        
        # Write to log file
        with open(log_filename, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
            
        console.print(Panel(
            f"[bold green]Success![/bold green]\n"
            f"Log file created: {log_filename}\n"
            f"Response status: {response.status_code}",
            border_style="green"
        ))
        
        # Print message summary
        if isinstance(response_data, list):
            messages = response_data
        else:
            messages = response_data.get('payload', [])
            
        console.print("\n[bold cyan]Message Summary:[/bold cyan]")
        for idx, msg in enumerate(messages, 1):
            console.print(f"[bold]Message {idx}:[/bold]")
            console.print(f"Type: {msg.get('message_type', 'unknown')}")
            console.print(f"Content: {msg.get('content', 'no content')[:100]}...")
            console.print(f"Created at: {msg.get('created_at', 'unknown')}")
            console.print("---")
            
    except requests.exceptions.RequestException as e:
        error_message = f"API Error: {str(e)}"
        console.print(f"[bold red]Error:[/bold red] {error_message}")
        
        # Log error
        with open(log_filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'type': type(e).__name__
            }, f, indent=2)
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        console.print(f"[bold red]Error:[/bold red] {error_message}")
        
        # Log error
        with open(log_filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'type': type(e).__name__
            }, f, indent=2)

if __name__ == "__main__":
    test_fetch_history()
