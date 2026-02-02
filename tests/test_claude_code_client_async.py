import pytest
import asyncio
from pathlib import Path
from src.services.claude_code_client import ClaudeCodeClient
import shutil
import sys
import os

# Ensure src is in path
sys.path.append(os.getcwd())

@pytest.mark.asyncio
async def test_claude_code_client_async_io():
    """Verify that ClaudeCodeClient works correctly with async file operations."""
    # Setup
    work_dir = Path("test_async_tasks")
    if work_dir.exists():
        shutil.rmtree(work_dir)

    try:
        client = ClaudeCodeClient(work_dir=work_dir)

        system_prompt = "Test System"
        messages = [{"role": "user", "content": "Test User"}]

        task_id = "task_001" # First task
        response_file = work_dir / f"{task_id}_response.md"
        task_file = work_dir / f"{task_id}_prompt.md"

        async def write_response_later():
            # Wait for task file to exist and have content
            # Check every 0.1s
            for _ in range(50):
                if task_file.exists() and task_file.stat().st_size > 0:
                    break
                await asyncio.sleep(0.1)

            assert task_file.exists(), "Task file was not created"
            assert task_file.stat().st_size > 0, "Task file is empty"

            # Verify task file content
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Retry reading if content is still empty (fs sync issues?)
                if not content:
                    await asyncio.sleep(0.1)
                    f.seek(0)
                    content = f.read()

                assert system_prompt in content
                assert "Test User" in content

            # Write response
            await asyncio.sleep(0.2) # Simulate delay
            with open(response_file, 'w', encoding='utf-8') as f:
                f.write("Test Response")

        # Run user simulation concurrently
        responder = asyncio.create_task(write_response_later())

        # Run client with timeout safety
        response, usage = await asyncio.wait_for(
            client.create_message(system_prompt, messages),
            timeout=10
        )

        # Verify response
        assert response == "Test Response"
        assert usage.input_tokens > 0
        assert usage.output_tokens > 0

        await responder

    finally:
        # Cleanup
        if work_dir.exists():
            shutil.rmtree(work_dir)
