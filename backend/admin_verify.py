import asyncio
import sys
from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from app.services.admin_service import seed_admin_account, authenticate_admin

class Req:
    pass

async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = client[settings.DATABASE_NAME]

    await seed_admin_account(db)
    admins = await db['admins'].find({}).to_list(length=20)
    print('admin_count=', len(admins))
    for admin in admins:
        print({
            '_id': str(admin.get('_id')),
            'email': admin.get('email'),
            'full_name': admin.get('full_name'),
            'role': admin.get('role'),
            'account_status': admin.get('account_status'),
        })

    req = Req()
    req.email = 'afan@admin.in'
    req.password = 'Admin@123'
    try:
        admin = await authenticate_admin(req, db)
        print('login_success=', admin.get('email'))
    except Exception as exc:
        print('login_success=FAILED', type(exc).__name__, exc)

    old_req = Req()
    old_req.email = 'admin@edusync.com'
    old_req.password = 'Admin@123'
    try:
        await authenticate_admin(old_req, db)
        print('old_login_still_works=YES')
    except Exception as exc:
        print('old_login_still_works=NO', type(exc).__name__, exc)

    client.close()

asyncio.run(main())
