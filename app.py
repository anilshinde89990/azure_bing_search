import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get connection string from environment
conn_str = os.environ["PROJECT_CONNECTION_STRING"]
agent_id = os.environ["AGENT_ID"]

# Optional: Get custom system prompt from environment
update_system_prompt = os.environ.get("UPDATE_SYSTEM_PROMPT", "false").lower() == "true"
custom_system_prompt = os.environ.get("SYSTEM_PROMPT", "")

try:
    # Initialize project client
    project_client = AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=conn_str
    )
    # Get the existing agent
    agent = project_client.agents.get_agent(agent_id)

    # Create a new thread for conversation
    thread = project_client.agents.create_thread()

    # System prompt handling (silent)
    if update_system_prompt:
        if custom_system_prompt:
            system_prompt = custom_system_prompt
        else:
            system_prompt = """You are a helpful AI assistant with access to Bing search capabilities. 
    
Your key characteristics:
- Always search for current, accurate information using Bing when users ask about recent events, weather, news, or facts
- Provide detailed, well-structured responses with proper citations
- Be conversational but professional
- When discussing research or trends, always look up the most recent information
- Format your responses clearly with bullet points or numbered lists when appropriate
- Always provide source URLs when available from your searches
    
Remember to cite your sources and provide context for your information."""

        try:
            updated_agent = project_client.agents.update_agent(
                agent_id=agent.id,
                instructions=system_prompt
            )
        except Exception as update_error:
            pass  # Continue silently

    # Create a message
    user_query = "prepare report on recent trends in health technology"
    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=f"{user_query} in 500 words"
    )
    # Run the agent
    run = project_client.agents.create_and_process_run(
        thread_id=thread.id,
        agent_id=agent.id
    )

    # Get all messages from the thread
    messages = project_client.agents.list_messages(thread_id=thread.id)
    
    # Extract and display only user query and agent response
    agent_response = ""
    
    # Get all messages and find the assistant's response
    for text_message in messages.text_messages:
        message_dict = text_message.as_dict()
        role = message_dict.get('role', '')
        
        if role == 'assistant':  # This is the agent's response
            # Try different ways to extract the content
            if hasattr(text_message, 'content'):
                content = text_message.content
                
                if isinstance(content, str):
                    agent_response = content
                elif isinstance(content, list) and len(content) > 0:
                    # Handle content blocks
                    first_block = content[0]
                    if isinstance(first_block, dict):
                        # Handle dict format like {'type': 'text', 'text': {'value': '...'}}
                        if 'text' in first_block and isinstance(first_block['text'], dict):
                            agent_response = first_block['text'].get('value', str(first_block))
                        else:
                            agent_response = str(first_block)
                    elif hasattr(first_block, 'text'):
                        agent_response = first_block.text.value if hasattr(first_block.text, 'value') else str(first_block.text)
                    else:
                        agent_response = str(first_block)
                else:
                    agent_response = str(content)
            else:
                agent_response = str(text_message)
            break
    
    # If still empty, try alternative method
    if not agent_response:
        for msg in messages.data if hasattr(messages, 'data') else []:
            if msg.get('role') == 'assistant':
                content_list = msg.get('content', [])
                if content_list and len(content_list) > 0:
                    content_item = content_list[0]
                    if content_item.get('type') == 'text':
                        agent_response = content_item.get('text', {}).get('value', '')
                        break
    
    # Display only user query and agent response
    print(f"\nUser Query: {user_query}")
    print(f"\nAgent Response: {agent_response}")
    
except Exception as e:
    print(f"Error: {e}")
