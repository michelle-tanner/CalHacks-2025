#This script simulates a "child" or user talking to our ChatAgent
# Sends simple messages every few seconds and prints out replies 

import asyncio 
from uagents import Agent, Context, Model

#message schema 
class Message(Model):
    message: str

#user "child" agent
user_agent = Agent(
    name="UserAgent",
    seed="user seed", #identification 
    port=8001, #unique for every agent 
    endpoint=["http://127.0.0.1:8001/submit"]
)

TARGET = "agent1qv5gwujwhmdrjlh5nfh430s4mx4zn4mk3fdgv0cpxfa9zjsy3dm2yd2sw3p"

test_messages = [
        "Hi there!",
        "Hello, I feel a bit sad today.",
        "Can you help me with my homework?",
        "Sometimes I get really sad for no reason.",
        "What's your favorite color?",
        "Do you like animals?"
    ]
msg_counter = 0

#simulate messages every 5 seconds
@user_agent.on_interval(period=5.0)
async def send_intro(ctx: Context):
    global msg_counter
    msg = test_messages[msg_counter % len(test_messages)]
    msg_counter += 1
    ctx.logger.info(f"Sending message to ChatAgent: {msg}")
    

    # msg = test_messages[ctx.periodic_counter % len(test_messages)]
    # ctx.logger.info(f"Sending message to ChatAgent: {msg}")
    # await ctx.send(TARGET, Message(message=msg))

#print replies from our ChatAgent
@user_agent.on_message(model=Message)
async def handle_reply(ctx: Context, sender: str, msg: Message):
    print(f"ChatAgent replied: {msg.message}")

# async def receive_reply(ctx: Context, sender: str, msg: Message):
    # print(f"ChatAgent replied: {msg.message}")

#run userAgent
if __name__ == "__main__":
    user_agent.run()