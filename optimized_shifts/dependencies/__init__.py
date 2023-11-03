from optimized_shifts.state import state


async def get_db():
    db = state.get("database")
    if not db:
        raise ValueError("No database in global state")

    yield db

async def get_ws_manager():
    manager = state.get("manager")
    if not manager:
        raise ValueError("No websocket manager in global state")

    yield manager