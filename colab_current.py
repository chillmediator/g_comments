import asyncio
import requests
import time
import json
from asyncio import create_task

async def run_process(cmd, capture_output=True):
    print('>>> starting', *cmd)
    if capture_output:
        p = await asyncio.subprocess.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def pipe(lines):
            async for line in lines:
                print(line.strip().decode('utf-8'))

        await asyncio.gather(
            pipe(p.stdout),
            pipe(p.stderr),
        )
    else:
        # For long-running processes, don't capture output
        p = await asyncio.subprocess.create_subprocess_exec(*cmd)
    return p

async def wait_for_server(max_attempts=5):
    """Wait for Ollama server to be ready"""
    for i in range(max_attempts):
        try:
            response = requests.get('http://localhost:11434')
            if response.status_code == 200:
                print("Server is ready!")
                return True
        except:
            pass
        print(f"Waiting for server... attempt {i+1}/{max_attempts}")
        await asyncio.sleep(2)
    return False

async def pull_model(model_name="dolphin3", max_attempts=3):
    """Pull the specified model with retry logic"""
    for attempt in range(max_attempts):
        try:
            response = requests.post(
                'http://localhost:11434/api/pull',
                json={"name": model_name},
                timeout=300
            )
            if response.status_code == 200:
                print(f"Successfully pulled {model_name} model")
                return True
            else:
                print(f"Failed to pull model (attempt {attempt + 1}): {response.text}")
        except Exception as e:
            print(f"Error pulling model (attempt {attempt + 1}): {str(e)}")
        await asyncio.sleep(5)
    return False

async def verify_model():
    """Verify model is working with a test prompt"""
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "dolphin3",
                "prompt": "Say hello!",
                "stream": False
            },
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            print("Model test successful!")
            print("Response:", result.get('response', ''))
            return True
        else:
            print(f"Model test failed: {response.text}")
            return False
    except Exception as e:
        print(f"Error testing model: {str(e)}")
        return False

async def get_ngrok_url(max_attempts=5):
    """Get the public ngrok URL"""
    for i in range(max_attempts):
        try:
            response = requests.get('http://localhost:4040/api/tunnels')
            tunnels = response.json()['tunnels']
            public_url = next(tunnel['public_url'] for tunnel in tunnels if 'ngrok' in tunnel['public_url'])
            print(f"\nYour public API endpoint is: {public_url}")
            return public_url
        except:
            await asyncio.sleep(2)
    print("Failed to get ngrok URL")
    return None

async def main():
    # Configure ngrok
    NGROK_TOKEN = "2de2r6zY6WYPiHQQtzbbag7Edyh_3oaAwPGgmmPhSbLPYeQb6"

    print("Setting up services...")

    # Configure ngrok
    await run_process(['ngrok', 'config', 'add-authtoken', NGROK_TOKEN])

    # Start Ollama and ngrok as background tasks
    ollama_process = await run_process(['ollama', 'serve'], capture_output=False)
    ngrok_process = await run_process(
        ['ngrok', 'http', '--log', 'stderr', '11434', '--host-header', 'localhost:11434'],
        capture_output=False
    )
    # Wait for server to be ready
    if await wait_for_server():
        # Pull and verify model
        if await pull_model():
            if await verify_model():
                # Get and display ngrok URL
                public_url = await get_ngrok_url()
                if public_url:
                    print("\nSetup complete! Your dolphin3 model is ready to use.")
                    print(f"Use this URL in your applications: {public_url}")

                    # Keep the processes running
                    try:
                        await asyncio.gather(
                            ollama_process.wait(),
                            ngrok_process.wait()
                        )
                    except KeyboardInterrupt:
                        print("\nShutting down services...")
                        ollama_process.terminate()
                        ngrok_process.terminate()
            else:
                print("Failed to verify model")
        else:
            print("Failed to pull model")
    else:
        print("Server failed to start")

# Run the main async function
await main()