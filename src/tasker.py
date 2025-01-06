import asyncio
from collections import deque

from pydantic import BaseModel
from .fucker import get_ticket
from loguru import logger
import time


class Ticket(BaseModel):
    data: str
    time: int


class Status(BaseModel):
    processing: int
    tickets: int
    last_success_time: int
    success_count: int


class Tasker:
    def __init__(self):
        self.num_of_process = 0
        self.tickets: deque[Ticket] = deque()
        # self.process_thread = threading.Thread(target=self._process_thread)
        # self.process_thread.start()
        self.running = False
        self.succeess_count = 0

    async def process(self):
        if self.running:
            return
        self.running = True
        try:
            while self.num_of_process:
                try:
                    raw_ticket = await asyncio.wait_for(get_ticket(), timeout=120)
                    ticket = Ticket(data=raw_ticket, time=int(time.time()))
                    self.tickets.append(ticket)
                    self.num_of_process -= 1
                    self.succeess_count += 1
                except asyncio.TimeoutError:
                    logger.info("Get ticket timeout. Retrying...")
                except Exception as e:
                    print(e)
        finally:
            self.running = False

    # def _process_thread(self):
    #     while True:
    #         if self.num_of_process:
    #             try:
    #                 ticket = Ticket(
    #                     data=asyncio.run(get_ticket()), time=int(time.time())
    #                 )
    #                 self.tickets.append(ticket)
    #                 with self.lock:
    #                     self.num_of_process -= 1
    #             except Exception as e:
    #                 print(e)
    #         else:
    #             time.sleep(1)

    def submit(self, num: int):
        self.num_of_process += num

    def get_ticket(self):
        while self.tickets:
            t = self.tickets.popleft()
            if time.time() - t.time > 480:
                continue
            yield t
        raise StopIteration

    def status(self) -> Status:
        while self.tickets:
            if time.time() - self.tickets[0].time > 480:
                self.tickets.popleft()
            else:
                break
        # return self.num_of_process, len(self.tickets)
        if self.tickets:
            last_success_time = self.tickets[-1].time
        else:
            last_success_time = 0

        return Status(
            processing=self.num_of_process,
            tickets=len(self.tickets),
            last_success_time=last_success_time,
            success_count=self.succeess_count,
        )


tasker = Tasker()
