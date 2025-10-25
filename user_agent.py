user_agent = Agent(
    name="UserAgent",
    seed="user seed", 
    port=8001,
    endpoint=["http://127.0.0.1:8001/submit"]
)

TARGET = agent1qv5gwujwhmdrjlh5nfh430s4mx4zn4mk3fdgv0cpxfa9zjsy3dm2yd2sw3p # chat agent address

@user_agent.on_interval(period=3.0)
async def send_intro(ctx: Context):
    await ctx.send(TARGET, Message(message="Hello, I feel a bit sad today."))

@user_agent.on_message(model=Message)
async def receive_reply(ctx: Context, sender: str, msg: Message):
    print(f"ChatAgent replied: {msg.message}")
