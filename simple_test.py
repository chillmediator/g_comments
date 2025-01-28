import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    # Use the new endpoint
    mistral_endpoint = "https://f48a-34-125-10-193.ngrok-free.app"
    print(f"\nTesting connection to: {mistral_endpoint}")
    
    try:
        # Test basic connectivity
        print("\nTesting basic connectivity...")
        response = requests.get(mistral_endpoint)
        print(f"Basic connectivity test: Status {response.status_code}")
        
        # Check available models
        print("\nChecking available models...")
        response = requests.get(f"{mistral_endpoint}/api/tags")
        if response.status_code == 200:
            models = response.json()
            print("Available models:", models)
            
            # If mistral is not in the models list, try to pull it
            if not any(model.get('name') == 'mistral' for model in models.get('models', [])):
                print("\nMistral model not found. Attempting to pull...")
                pull_response = requests.post(
                    f"{mistral_endpoint}/api/pull",
                    json={"name": "mistral"},
                    headers={'Content-Type': 'application/json'},
                    timeout=300  # Longer timeout for model pull
                )
                if pull_response.status_code == 200:
                    print("Successfully pulled Mistral model")
                else:
                    print(f"Failed to pull model: {pull_response.text}")
        
        # Test Mistral API
        print("\nTesting Mistral API...")
        headers = {'Content-Type': 'application/json'}
        payload = {
            'model': 'mistral',
            'prompt': "Hello!",
            'stream': False
        }
        
        print("Sending request...")
        response = requests.post(
            f"{mistral_endpoint}/api/generate",
            json=payload,
            headers=headers,
            timeout=60
        )
        
        print(f"API test status: {response.status_code}")
        if response.status_code == 200:
            print("Success! Response:", response.json())
        else:
            print("Error response:", response.text)
        
    except requests.exceptions.RequestException as e:
        print(f"\nError: {type(e).__name__}")
        print(f"Details: {str(e)}")

if __name__ == "__main__":
    test_connection()
