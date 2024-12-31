import asyncio
from collections import deque
from pydantic import BaseModel
from .fucker import get_ticket
import threading
import time


class Ticket(BaseModel):
    data: str
    time: int


class Tasker:
    def __init__(self):
        self.lock = threading.Lock()
        self.num_of_process = 0
        self.tickets: deque[Ticket] = deque()
        self.process_thread = threading.Thread(target=self._process_thread)

    def _process_thread(self):
        while True:
            if self.num_of_process:
                try:
                    ticket = Ticket(
                        data=asyncio.run(get_ticket()), time=int(time.time())
                    )
                    self.tickets.append(ticket)
                    with self.lock:
                        self.num_of_process -= 1
                except Exception as e:
                    print(e)
            else:
                time.sleep(1)

    def submit(self, num: int):
        with self.lock:
            self.num_of_process += num

    def get_ticket(self):
        while self.tickets:
            t = self.tickets.popleft()
            if time.time() - t.time > 480:
                continue
            yield t
        raise StopIteration

    def status(self):
        while self.tickets:
            if time.time() - self.tickets[0].time > 480:
                self.tickets.popleft()
        return self.num_of_process, len(self.tickets)


tasker = Tasker()