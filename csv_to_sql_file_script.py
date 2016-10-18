import csv
with open('Proc.csv','r') as file:
    content=csv.reader(file)
    table=list()
    k=0
    for row in content:
        if(k>1):
            s=row[3]
            s1=s+'.sql'
            fo=open(s1,'w')
            fo.write(row[4])
            fo.close()
        k+=1
