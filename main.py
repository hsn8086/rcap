import asyncio
from src.fucker import get_ticket

if __name__ == '__main__':
    print(asyncio.run(get_ticket(headless=True)))