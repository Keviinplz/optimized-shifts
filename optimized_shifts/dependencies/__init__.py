from optimized_shifts.state import state


async def get_db():
    db = state.get("database")
    if not db:
        raise ValueError("No database in global state")

    yield db
