"""
فرمت CSV (هدر اجباری):
user_id,username,first_name,last_name,phone,note
123456789,ali,Ali,Rezaei,+989121234567,دوست
"""
import asyncio
import csv

from database import init_db, upsert_user


async def import_csv(path: str):
    await init_db()
    ok = 0
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                uid = int(row["user_id"])
            except (KeyError, ValueError):
                continue
            fields = {k: v for k, v in row.items()
                      if k != "user_id" and v}
            await upsert_user(uid, **fields)
            ok += 1
    print(f"✅ {ok} رکورد وارد شد.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("استفاده: python importer.py contacts.csv")
    else:
        asyncio.run(import_csv(sys.argv[1]))
