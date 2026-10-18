#24k-1038 mubashir sikandar
import argparse
import random

from channel import Sim, Channel, PKT_BITS
from gbn import GBN
from sr import SR


def run(protocol, packets=200, N=4, k=3, loss=0.0, corrupt=0.0, delay=0.0,
        timeout=1000.0, seed=1234, verbose=False):
    M = 2 ** k
    if protocol == "gbn" and N > M - 1:
        raise ValueError(f"GBN needs N <= 2^k - 1 = {M - 1}")
    if protocol == "sr" and N > M // 2:
        raise ValueError(f"SR needs N <= 2^(k-1) = {M // 2}")

    random.seed(seed)
    stats = {"transmitted": 0, "retransmissions": 0, "timeouts": 0, "acks_sent": 0,
             "lost_data": 0, "lost_ack": 0, "corrupt_data": 0, "corrupt_ack": 0}
    sim = Sim(verbose)
    chan = Channel(sim, loss, corrupt, delay, stats)
    cls = GBN if protocol == "gbn" else SR
    proto = cls(sim, chan, packets, N, k, timeout, stats)
    proto.start()
    sim.run(proto.done)

    ok = proto.delivered == proto.data
    stats["protocol"] = protocol
    stats["delivered"] = len(proto.delivered)
    stats["correct_order"] = ok
    stats["time_ms"] = sim.now
    stats["throughput_kbps"] = len(proto.delivered) * PKT_BITS / sim.now  # bits/ms = kbps
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", choices=["gbn", "sr"], default="gbn")
    ap.add_argument("--packets", type=int, default=20)
    ap.add_argument("--window", type=int, default=4)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--corrupt", type=float, default=0.0)
    ap.add_argument("--delay", type=float, default=0.0)
    ap.add_argument("--timeout", type=float, default=1000.0, help="ms")
    ap.add_argument("--seed", type=int, default=1234, help="last 4 digits of roll no")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    s = run(a.protocol, a.packets, a.window, a.k, a.loss, a.corrupt, a.delay,
            a.timeout, a.seed, verbose=not a.quiet)
    print("\n--- summary ---")
    for key, v in s.items():
        print(f"{key}: {v:.2f}" if isinstance(v, float) else f"{key}: {v}")
