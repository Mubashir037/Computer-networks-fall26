#24k-1038 mubashir sikandar
from channel import make_pkt, is_corrupt, TX_TIME


class SR:
    def __init__(self, sim, chan, total, N, k, timeout, stats):
        self.sim, self.chan, self.total = sim, chan, total
        self.N, self.M, self.timeout, self.stats = N, 2 ** k, timeout, stats
        self.data = [f"packet-{i}" for i in range(total)]
        # sender
        self.base = 0
        self.nextseqnum = 0
        self.acked = set()
        self.timers = {}
        self.link_free = 0.0
        # receiver
        self.rcv_base = 0
        self.buffer = {}
        self.delivered = []

    def done(self):
        return self.base >= self.total

    def start(self):
        self.fill_window()

    # ---------------- sender ----------------
    def fill_window(self):
        while self.nextseqnum < self.base + self.N and self.nextseqnum < self.total:
            n = self.nextseqnum
            self.transmit(n, False)
            self.start_timer(n)
            self.nextseqnum += 1

    def transmit(self, n, retx):
        t = max(self.sim.now, self.link_free)
        self.link_free = t + TX_TIME
        self.sim.schedule(t - self.sim.now, lambda: self.put_on_link(n, retx))

    def put_on_link(self, n, retx):
        self.stats["transmitted"] += 1
        if retx:
            self.stats["retransmissions"] += 1
        tag = "RETRANSMIT" if retx else "SEND"
        self.sim.log(f"SENDER   {tag} pkt {n} (seq={n % self.M}) "
                     f"window=[{self.base}-{self.base + self.N - 1}]")
        self.chan.send(make_pkt(n % self.M, self.data[n]), self.recv_data, "DATA")

    def start_timer(self, n):
        self.sim.cancel(self.timers.get(n))
        self.timers[n] = self.sim.schedule(self.timeout, lambda: self.on_timeout(n))

    def on_timeout(self, n):
        if n < self.base or n in self.acked:
            return
        self.stats["timeouts"] += 1
        self.sim.log(f"SENDER   TIMEOUT for pkt {n}, resend only this one")
        self.transmit(n, True)
        self.start_timer(n)

    def recv_ack(self, pkt):
        if is_corrupt(pkt):
            self.sim.log("SENDER   got corrupt ACK, ignored")
            return
        a = pkt["seq"]
        for n in range(self.base, self.nextseqnum):
            if n % self.M == a:
                if n in self.acked:
                    self.sim.log(f"SENDER   duplicate ACK {a}, ignored")
                    return
                self.acked.add(n)
                self.sim.cancel(self.timers.pop(n, None))
                while self.base in self.acked:
                    self.base += 1
                self.sim.log(f"SENDER   ACK {a} (individual) pkt {n} acked -> base={self.base}")
                self.fill_window()
                return
        self.sim.log(f"SENDER   old ACK {a}, ignored")

    # ---------------- receiver ----------------
    def send_ack(self, seq):
        self.stats["acks_sent"] += 1
        self.sim.log(f"RECEIVER send ACK {seq}")
        self.chan.send(make_pkt(seq, ""), self.recv_ack, "ACK")

    def recv_data(self, pkt):
        if is_corrupt(pkt):
            self.sim.log(f"RECEIVER corrupt packet seq={pkt['seq']}, discarded")
            return
        s = pkt["seq"]
        off = (s - self.rcv_base) % self.M
        if off < self.N:                      # inside receiver window
            n = self.rcv_base + off
            self.send_ack(s)
            if n not in self.buffer:
                self.buffer[n] = pkt["data"]
                if off > 0:
                    self.sim.log(f"RECEIVER seq={s} out of order, buffered "
                                 f"(rcv_base={self.rcv_base})")
            while self.rcv_base in self.buffer:
                self.delivered.append(self.buffer.pop(self.rcv_base))
                self.sim.log(f"RECEIVER delivered pkt {self.rcv_base} in order "
                             f"({len(self.delivered)})")
                self.rcv_base += 1
        elif off >= self.M - self.N:          # already delivered earlier, ack again
            self.sim.log(f"RECEIVER old packet seq={s}, re-ACK")
            self.send_ack(s)
        else:
            self.sim.log(f"RECEIVER seq={s} outside window, ignored")
