#24k-1038 mubashir sikandar
import heapq

import random


RATE = 2_000_000          # 2 Mbps
PKT_BITS = 8000           # 1000 bytes
TX_TIME = PKT_BITS / RATE * 1000   # 4 ms to push one packet on the link
ONE_WAY = 250.0           # RTT = 500 ms


def checksum(seq, data):
    total = seq
    for i, b in enumerate(data.encode()):
        total += (i + 1) * b
    return total % 65536


def make_pkt(seq, data):
    return {"seq": seq, "data": data, "csum": checksum(seq, data)}


def is_corrupt(pkt):
    return pkt["csum"] != checksum(pkt["seq"], pkt["data"])


class Sim:
    """tiny event simulator, time is in ms"""

    def __init__(self, verbose=True):
        self.now = 0.0
        self.q = []
        self.count = 0
        self.verbose = verbose

    def schedule(self, delay, fn):
        ev = {"fn": fn, "dead": False}
        self.count += 1
        heapq.heappush(self.q, (self.now + delay, self.count, ev))
        return ev

    def cancel(self, ev):
        if ev is not None:
            ev["dead"] = True

    def run(self, done):
        while self.q and not done():
            t, _, ev = heapq.heappop(self.q)
            if ev["dead"]:
                continue
            self.now = t
            ev["fn"]()

    def log(self, msg):
        if self.verbose:
            print(f"[{self.now:9.1f} ms] {msg}")


class Channel:
    """unreliable channel: loss, corruption and delay for data and acks"""

    def __init__(self, sim, loss, corrupt, delay, stats):
        self.sim = sim
        self.loss = loss
        self.corrupt = corrupt
        self.delay = delay
        self.stats = stats

    def send(self, pkt, deliver, kind):
        label = f"{kind} seq={pkt['seq']}"
        if random.random() < self.loss:
            self.stats["lost_" + kind.lower()] += 1
            self.sim.log(f"CHANNEL  {label} LOST")
            return
        p = dict(pkt)
        if random.random() < self.corrupt:
            p["data"] = p["data"] + "X"      
            self.stats["corrupt_" + kind.lower()] += 1
            self.sim.log(f"CHANNEL  {label} CORRUPTED")
        d = ONE_WAY
        if random.random() < self.delay:
            extra = random.uniform(50, 200)
            d += extra
            self.sim.log(f"CHANNEL  {label} DELAYED +{extra:.0f} ms")
        self.sim.schedule(d, lambda: deliver(p))
