import asyncio
import requests
import time
import os
from rich.console import Console

console = Console()

async def run_process(cmd, capture_output=True):
    """Run a subprocess command"""
    console.print(f'[blue]>>> starting[/blue] {" ".join(cmd)}')
    if capture_output:
        p = await asyncio.subprocess.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        async def pipe(lines):
            async for line in lines:
                console.print(line.strip().decode('utf-8'))
        
        await asyncio.gather(
            pipe(p.stdout),
            pipe(p.stderr),
        )
    else:
        p = await asyncio.subprocess.create_subprocess_exec(*cmd)
    return p

async def wait_for_server(max_attempts=5):
    """Wait for Ollama server to be ready"""
    for i in range(max_attempts):
        try:
            response = requests.get('http://localhost:11434')
            if response.status_code == 200:
                console.print("[green]Server is ready![/green]")
                return True
        except:
            pass
        console.print(f"[yellow]Waiting for server... attempt {i+1}/{max_attempts}[/yellow]")
        await asyncio.sleep(2)
    return False

async def pull_model(model_name="mistral", max_attempts=3):
    """Pull the specified model with retry logic"""
    for attempt in range(max_attempts):
        try:
            response = requests.post(
                'http://localhost:11434/api/pull',
                json={"name": model_name},
                timeout=300
            )
            if response.status_code == 200:
                console.print(f"[green]Successfully pulled {model_name} model[/green]")
                return True
            else:
                console.print(f"[red]Failed to pull model (attempt {attempt + 1}): {response.text}[/red]")
        except Exception as e:
            console.print(f"[red]Error pulling model (attempt {attempt + 1}): {str(e)}[/red]")
        await asyncio.sleep(5)
    return False

async def verify_model(model_name="mistral"):
    """Verify the model is working with a simple test"""
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": model_name,
                "prompt": "Say 'Hello, I am ready to help!'",
                "stream": False
            }
        )
        if response.status_code == 200:
            console.print("[green]Model verification successful![/green]")
            return True
        else:
            console.print(f"[red]Model verification failed: {response.text}[/red]")
    except Exception as e:
        console.print(f"[red]Error verifying model: {str(e)}[/red]")
    return False

async def main():
    """Main setup function"""
    # Install Ollama
    console.print("\n[bold blue]Step 1: Installing Ollama...[/bold blue]")
    import requests
    response = requests.get('https://ollama.ai/install.sh')
    with open('install.sh', 'w') as f:
        f.write(response.text)
    await run_process(['bash', 'install.sh'])
    
    # Wait for server
    console.print("\n[bold blue]Step 2: Waiting for Ollama server...[/bold blue]")
    if await wait_for_server():
        # Pull model
        console.print("\n[bold blue]Step 3: Pulling Mistral model...[/bold blue]")
        if await pull_model():
            # Verify model
            console.print("\n[bold blue]Step 4: Verifying model...[/bold blue]")
            if await verify_model():
                console.print("\n[bold green]Setup complete! You can now run generate_comments.py[/bold green]")
                return
    
    console.print("\n[bold red]Setup failed. Please check the errors above.[/bold red]")

if __name__ == "__main__":
    asyncio.run(main())
