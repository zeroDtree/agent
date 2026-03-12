import asyncio
import time


async def async_hello_world():
    now = time.time()
    await asyncio.sleep(1)
    print(time.time() - now)
    print("Hello, world!")
    await asyncio.sleep(1)
    print(time.time() - now)


async def main():
    task1 = asyncio.create_task(async_hello_world())
    task2 = asyncio.create_task(async_hello_world())
    task3 = asyncio.create_task(async_hello_world())
    await task1
    await task2
    await task3


now = time.time()
# run 3 async_hello_world() coroutine concurrently
asyncio.run(main())

print(f"Total time for running 3 coroutine: {time.time() - now}")
