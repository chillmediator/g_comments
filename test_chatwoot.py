import requests
import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.pretty import pprint

# Load environment variables
load_dotenv()

console = Console()

def test_chatwoot_api(conversation_id, message="This is a test message from the API"):
    """Test sending a message via Chatwoot API"""
    base_url = os.getenv('CHATWOOT_BASE_URL')
    api_token = os.getenv('CHATWOOT_API_TOKEN')
    
    console.print(Panel(
        f"[bold blue]Testing Chatwoot API[/bold blue]\n"
        f"Base URL: {base_url}\n"
        f"Conversation ID: {conversation_id}\n"
        f"Test message: {message}",
        border_style="blue"
    ))
    
    try:
        url = f"{base_url}/api/v1/conversations/{conversation_id}/messages"
        headers = {
            'api_access_token': api_token,
            'Content-Type': 'application/json'
        }
        payload = {
            'content': message,
            'message_type': 'outgoing'
        }
        
        # Log the request details
        console.print("\n[bold yellow]Sending Request:[/bold yellow]")
        console.print(f"URL: {url}")
        console.print("Headers:", {k: '***' if k == 'api_access_token' else v for k, v in headers.items()})
        console.print("Payload:")
        pprint(payload)
        
        # Make the request
        response = requests.post(url, json=payload, headers=headers)
        
        # Log the raw response
        console.print("\n[bold green]Raw Response:[/bold green]")
        console.print(f"Status Code: {response.status_code}")
        console.print("Response Headers:")
        pprint(dict(response.headers))
        console.print("\nResponse Body:")
        pprint(response.json())
        
        # Process the response
        if response.status_code in [200, 201]:
            data = response.json()
            console.print(Panel(
                f"[bold green]Success![/bold green]\n"
                f"Message ID: {data.get('id')}\n"
                f"Content: {data.get('content')}",
                border_style="green"
            ))
            return True, data
        else:
            console.print(Panel(
                f"[bold red]Error: Non-200 Status Code[/bold red]\n"
                f"Status: {response.status_code}\n"
                f"Response: {response.text}",
                border_style="red"
            ))
            return False, None
            
    except requests.exceptions.RequestException as e:
        console.print(Panel(
            f"[bold red]Connection Error[/bold red]\n{str(e)}",
            border_style="red"
        ))
        return False, None
    except Exception as e:
        console.print(Panel(
            f"[bold red]Unexpected Error[/bold red]\n{str(e)}",
            border_style="red"
        ))
        return False, None

def list_recent_conversations():
    """List recent conversations to get a valid conversation ID"""
    base_url = os.getenv('CHATWOOT_BASE_URL')
    api_token = os.getenv('CHATWOOT_API_TOKEN')
    
    try:
        url = f"{base_url}/api/v1/conversations"
        headers = {
            'api_access_token': api_token,
            'Content-Type': 'application/json'
        }
        
        console.print(Panel(
            "[bold blue]Fetching Recent Conversations[/bold blue]",
            border_style="blue"
        ))
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            conversations = response.json()
            console.print("\n[bold green]Available Conversations:[/bold green]")
            for conv in conversations.get('payload', []):
                console.print(f"ID: {conv.get('id')} - Inbox: {conv.get('inbox_id')} - Status: {conv.get('status')}")
            return conversations.get('payload', [])
        else:
            console.print(Panel(
                f"[bold red]Error Fetching Conversations[/bold red]\n"
                f"Status: {response.status_code}\n"
                f"Response: {response.text}",
                border_style="red"
            ))
            return []
            
    except Exception as e:
        console.print(Panel(
            f"[bold red]Error Fetching Conversations[/bold red]\n{str(e)}",
            border_style="red"
        ))
        return []

if __name__ == "__main__":
    # First, list available conversations
    conversations = list_recent_conversations()
    
    if conversations:
        # Use the first available conversation for testing
        conversation_id = conversations[0]['id']
        console.print(f"\n[bold]Using conversation ID: {conversation_id}[/bold]")
        
        # Test sending a message
        success, response = test_chatwoot_api(
            conversation_id,
            "🤖 Hello! This is a test message from the API integration test script."
        )
        
        if success:
            console.print("\n✅ Chatwoot API test successful!")
        else:
            console.print("\n❌ Chatwoot API test failed!")
    else:
        console.print("\n❌ No conversations available for testing!")
