# Integrate chat LLM and build chat agent 
# Allow agents to exchange text 

from uagents import Agent, Context, Model

class Message(Model):
    message: str

chat_agent = Agent(
    name="chat_agent",
    seed="child-friendly seed phrase",
    port=8000,
    endpoint=["http://localhost:8000/submit"]

)
print("Chat Agent address:", chat_agent.address)

# add handler for incoming messages 
# when agent receives a message, we call the LLM API to generate a child-friendly reply 

from openai import OpenAI
client = OpenAI(api_key=os.getenv("ASI_ONE_API_KEY"), base_url="https://api.asi1.ai/v1") #using ASI:One's API

@chat_agent.on_message(model=Message)
async def on_message(ctx: Context, sender: str, msg: Message):
    # Call ASI:One or OpenAI with a supportive system prompt
    system = "You are a friendly assistant talking to a 10-year-old..."
    response = client.chat.completions.create(
        model="asi1-mini", 
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": msg.message}
        ]
    )
    answer = response.choices[0].message.content
    ctx.logger.info(f"Reply to {sender}: {answer}")
    await ctx.send(sender, Message(message=answer))