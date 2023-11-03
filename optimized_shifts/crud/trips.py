from optimized_shifts.schemas.trip import TripCreate, TripInDB
from optimized_shifts.state import Database

Point = tuple[float, float]


class TripsRepository:
    @staticmethod
    async def get_count_weekly_average_by_bbox_and_region(
        bbox: tuple[Point, Point], region_id: int, db: Database
    ) -> float | None:
        p, q = bbox

        px, py = p
        qx, qy = q

        async with db.acquire() as conn:
            mean_row = await conn.fetchrow(
                """
                SELECT AVG(count) AS result
                FROM (
                    SELECT COUNT(*)
                    FROM (
                        SELECT * 
                        FROM trips 
                        WHERE origin[0] >= $1 AND origin[0] <= $3 AND -- px, qx
                            destination[0] >= $1 AND destination[0] <= $3 AND -- px, qx
                            origin[1] >= $2 AND origin[1] <= $4 AND -- py, qy
                            destination[1] >= $2 AND destination[1] <= $4 AND -- py, qy
                            region_id = $5
                        -- Tabla filtrada por bbox y region
                    ) AS filtered 
                    GROUP BY DATE_TRUNC('week', timestamp) 
                    -- conteo semanal de viajes
                ) AS weekly_count 
            """,
                *(
                    px,
                    py,
                    qx,
                    qy,
                    region_id,
                ),
            )

        return mean_row.get("result") if mean_row else None

    @staticmethod
    async def create(trip: TripCreate, db: Database) -> TripInDB | None:
        stmt = """
            INSERT INTO trips (region_id, origin, destination, timestamp, source)
            VALUES ($1, $2, $3, $4, $5)
            )        
        """

        async with db.acquire() as conn:
            row = await conn.fetchrow(stmt, *trip.model_dump().values())

        return TripInDB(**row) if row else None

    @staticmethod
    async def create_multiple(
        trips: list[TripCreate], db: Database
    ) -> list[TripInDB] | None:
        stmt = """
            INSERT INTO trips (region_id, origin, destination, timestamp, source) (
                SELECT r.region_id, r.origin, r.destination, r.timestamp, r.source
                FROM unnest($1::trips[]) as r
            )
            RETURNING trip_id, region_id, origin, destination, timestamp, source
            """

        async with db.acquire() as conn:
            rows = await conn.fetch(
                stmt, [(None, *trip.model_dump().values()) for trip in trips]
            )

        return [TripInDB(**row) for row in rows]
