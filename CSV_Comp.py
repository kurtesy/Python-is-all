import csv
import sys
fil=raw_input('Enter File Name:')
f = open(fil, 'rt')
try:
    reader = csv.reader(f)
    for row in reader:
        print row
finally:
    f.close()
