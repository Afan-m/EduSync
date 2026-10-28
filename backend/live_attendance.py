"""Live face recognition attendance runner."""

import asyncio
import argparse

from app.core.database import connect_to_mongo, close_mongo_connection, db_manager
from app.services.live_face_attendance import run_live_attendance


async def main(session_id: str) -> None:
    await connect_to_mongo()
    db = db_manager.database
    if db is None:
        raise SystemExit("Database connection failed.")

    result = await run_live_attendance(session_id, db, max_frames=300, max_seconds=45)
    print(result)
    await close_mongo_connection()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run EduSync live face attendance.")
    parser.add_argument("session_id", help="Active attendance session ID")
    args = parser.parse_args()
    asyncio.run(main(args.session_id))
