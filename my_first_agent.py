from uagents import Agent, Context

# instantiate agent
agent = Agent(
    name="alice",
    seed="secret_seed_phrase",
    port=8000,
    endpoint=["http://localhost:8000/submit"]
)

# startup handler
@agent.on_event("startup")
async def startup_function(ctx: Context):
    ctx.logger.info(f"Hello, I'm agent {agent.name} and my address is {agent.address}.")

if __name__ == "__main__":
    agent.run()