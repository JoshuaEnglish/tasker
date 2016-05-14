import argparse

papa = argparse.ArgumentParser('papa', description='Papa Program')

coreshyte = papa.add_argument_group("core", 'the shyte')
corecommies = coreshyte.add_subparsers(title="core commies")