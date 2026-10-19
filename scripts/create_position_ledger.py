"""Create a new standalone public position ledger (never overwrite)."""
import argparse
from database.position_accounting import create_position_ledger
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='public_position_ledger.sqlite3')
    args=parser.parse_args()
    create_position_ledger(args.out)
    print('Created:',args.out)
