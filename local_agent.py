from uagents import Agent, Context, Model
 
class Message(Model):
    message: str
 
SEED_PHRASE = "put_your_seed_phrase_here"
 
# Now your agent is ready to join the Agentverse!
agent = Agent(
    name="alice",
    port=8000,
    seed=SEED_PHRASE,
    endpoint=["http://localhost:8000/submit"]
)
 
# Copy the address shown below
print(f"Your agent's address is: {agent.address}")
 
if __name__ == "__main__":
    agent.run()