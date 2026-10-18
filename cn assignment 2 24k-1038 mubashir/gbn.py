#24k-1038 mubashir sikandar
from channel import make_pkt, is_corrupt, TX_TIME


class GBN:
    def __init__(self, sim, chan, total, N, k, timeout, stats):
        self.sim, self.chan, self.total = sim, chan, total
        self.N, self.M, self.timeout, self.stats = N, 2 ** k, timeout, stats
        self.data = [f"packet-{i}" for i in range(total)]
        # sender
        self.base = 0
        self.nextseqnum = 0
        self.timer = None
        self.link_free = 0.0
        # receiver
        self.expectedseqnum = 0
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
            if self.base == self.nextseqnum:
                self.start_timer()
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
                     f"base={self.base} nextseqnum={self.nextseqnum}")
        self.chan.send(make_pkt(n % self.M, self.data[n]), self.recv_data, "DATA")

    def start_timer(self):
        self.sim.cancel(self.timer)
        self.timer = self.sim.schedule(self.timeout, self.on_timeout)

    def on_timeout(self):
        if self.done():
            return
        self.stats["timeouts"] += 1
        self.sim.log(f"SENDER   TIMEOUT base={self.base}, resend {self.base}..{self.nextseqnum - 1}")
        self.start_timer()
        for n in range(self.base, self.nextseqnum):
            self.transmit(n, True)

    def recv_ack(self, pkt):
        if is_corrupt(pkt):
            self.sim.log("SENDER   got corrupt ACK, ignored")
            return
        a = pkt["seq"]
        for n in range(self.base, self.nextseqnum):
            if n % self.M == a:
                self.base = n + 1          # cumulative ACK
                self.sim.log(f"SENDER   ACK {a} (cumulative) -> base={self.base}")
                self.sim.cancel(self.timer)
                self.timer = None
                if self.base != self.nextseqnum:
                    self.start_timer()
                self.fill_window()
                return
        self.sim.log(f"SENDER   duplicate ACK {a}, ignored")

    # ---------------- receiver ----------------
    def send_ack(self, seq):
        self.stats["acks_sent"] += 1
        self.sim.log(f"RECEIVER send ACK {seq}")
        self.chan.send(make_pkt(seq, ""), self.recv_ack, "ACK")

    def recv_data(self, pkt):
        if is_corrupt(pkt):
            self.sim.log(f"RECEIVER corrupt packet seq={pkt['seq']}, discarded")
        elif pkt["seq"] == self.expectedseqnum:
            self.delivered.append(pkt["data"])
            self.sim.log(f"RECEIVER got seq={pkt['seq']} in order, delivered "
                         f"({len(self.delivered)})")
            self.expectedseqnum = (self.expectedseqnum + 1) % self.M
            self.send_ack(pkt["seq"])
            return
        else:
            self.sim.log(f"RECEIVER got seq={pkt['seq']} out of order "
                         f"(expectedseqnum={self.expectedseqnum}), discarded")
        # re-send ack of last in-order packet
        if self.delivered:
            self.send_ack((self.expectedseqnum - 1) % self.M)
