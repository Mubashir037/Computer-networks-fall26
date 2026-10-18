#24k-1038 mubashir sikandar
# CS3001 Assignment 2 - GBN and SR

Python 3 only. matplotlib is needed just for the graph (`pip install matplotlib`).

## Files
- channel.py - checksum, event simulator, unreliable channel (loss, corruption, delay)
- gbn.py - Go-Back-N sender and receiver
- sr.py - Selective Repeat sender and receiver
- simulate.py - command line program, runs one protocol
- run_experiments.py - runs scenarios A, B, C for both protocols, writes results.csv and comparison.png

## Parameters (simulate.py)
--protocol gbn|sr, --packets, --window N, --k (seq bits, numbers wrap mod 2^k),
--loss, --corrupt, --delay (probabilities, apply to data and ACKs),
--timeout (ms, keep it above the max RTT, default 1000), --seed (last 4 digits of roll no), --quiet

GBN needs N <= 2^k - 1, SR needs N <= 2^(k-1).

## Sample command
    python simulate.py --protocol sr --packets 20 --window 4 --k 3 --loss 0.1 --seed 1038

## Experiments
    python run_experiments.py
    then results are obtained they are in the folder 
