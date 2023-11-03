from optimized_shifts.schemas.region import RegionInDB
from optimized_shifts.state import Database


class RegionRepository:
    @staticmethod
    async def create(name: str, db: Database) -> RegionInDB | None:
        """Create a region into database, returns RegionInDB if success, or None instead"""
        stmt = "INSERT INTO regions (region_name) VALUES ($1)"
        async with db.acquire() as conn:
            row = await conn.fetchrow(stmt, name)

        return RegionInDB(**row) if row else None

    @staticmethod
    async def create_multiple(names: list[str], db: Database) -> list[RegionInDB]:
        """Insert multiple regions into database, returns RegionInDB list if success, or None instead"""
        stmt = """
            INSERT INTO regions (region_name) (
                SELECT r.region_name 
                FROM unnest($1::regions[]) as r
            ) 
            RETURNING region_id, region_name
        """
        async with db.acquire() as conn:
            rows = await conn.fetch(stmt, [(None, name) for name in names])

        return list(
            map(
                lambda row: RegionInDB(
                    **row,
                ),
                rows,
            )
        )

    @staticmethod
    async def get_by_id(region_id: str, db: Database) -> RegionInDB | None:
        stmt = """SELECT region_id, region_name FROM regions WHERE region_id=$1"""
        async with db.acquire() as conn:
            row = await conn.fetchrow(stmt, region_id)

        if not row:
            return None

        return RegionInDB(**row)

    @staticmethod
    async def get_by_name(region_name: str, db: Database) -> RegionInDB | None:
        stmt = """SELECT region_id, region_name FROM regions WHERE region_name=$1"""
        async with db.acquire() as conn:
            row = await conn.fetchrow(stmt, region_name)

        if not row:
            return None

        return RegionInDB(**row)

    @staticmethod
    async def get_by_name_multiple(names: set[str], db: Database) -> list[RegionInDB]:
        prepared = ", ".join(f"${i+1}" for i in range(len(names)))
        stmt = f"""SELECT region_id, region_name FROM regions WHERE region_name in ({prepared})"""

        async with db.acquire() as conn:
            rows = await conn.fetch(stmt, *names)

        return list(map(lambda row: RegionInDB(**row), rows))
