import os
from time import sleep
def addToClipBoard(text):
    command = 'echo ' + text.strip() + '| clip'
    os.system(command)
a=list()
print "Enter list of values-- Use * to end the list"
while(1):
    x=raw_input()
    if(x=='*'):
        break
    else:
        a.append(x)
sep=raw_input("Enter Seperator Type\n")
data=sep.join(a)
print data
addToClipBoard(data)
print "Output copied to clipboard"
sleep(1.5)
print "Thank You!!"

    
        
