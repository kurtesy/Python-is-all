import csv
import sys
f=open('ETRM_trim.csv','rb')
try:
    count=0
    reader=csv.reader(f)
    l=list(reader)
    table=list()
    rw_cnt = sum(1 for row in l )
    for row in range(0,rw_cnt):
        if (l[row] == ['Foreign Keys '] ):
            k=1
            while(1):
                if(len(str(l[row-k]))<=30 and str(l[row-k]).count('_')>=1 and str(l[row-k]).count('_ID ')==0 ):
                    table.append(l[row-k])
                    break
                else:
                    k+=1
        #print l[row]
    for i in table:
        print i
finally:
    f.close()
