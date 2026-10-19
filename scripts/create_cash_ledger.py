"""Create a separate, empty public transaction ledger."""
import argparse
from database.transaction_ledger import create_public_ledger
if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',required=True)
    create_public_ledger(p.parse_args().out)
    print('Created empty public ledger')
